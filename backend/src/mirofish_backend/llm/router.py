from dataclasses import dataclass
from typing import Any, Literal

from mirofish_backend.config import Settings, get_settings
from mirofish_backend.llm.anthropic_request import (
    resolve_wire_anthropic_thinking_effort,
    sonnet_55_effective_max_tokens,
)
from mirofish_backend.llm import claude_client
from mirofish_backend.llm.llm_request_log import resolve_llm_request_logger
from mirofish_backend.llm.openai_compatible_client import chat_completion_openai_compatible
from mirofish_backend.llm.routing_policies import (
    resolve_effective_provider as _resolve_effective_provider_for_policy,
    routing_policy_from_mode,
)

LLMProvider = Literal["lmstudio", "anthropic"]


@dataclass(frozen=True)
class LLMCompletion:
    """Chat completion text plus optional token usage (Iteration 29)."""

    text: str
    input_tokens: int | None = None
    output_tokens: int | None = None


def resolve_effective_provider(
    *,
    routing_mode: str = "",
    routing_policy: str | None = None,
    round_number: int,
    turn_index: int,
) -> LLMProvider:
    """
    Map routing mode or explicit policy to the provider for this turn.

    Prefer ``routing_policy`` when set; otherwise derive from legacy ``routing_mode``
    (``lmstudio`` | ``anthropic`` | ``hybrid``).
    """
    policy = routing_policy if routing_policy is not None else routing_policy_from_mode(routing_mode)
    return _resolve_effective_provider_for_policy(
        routing_policy=policy,
        round_number=round_number,
        turn_index=turn_index,
    )


def effective_model_id(
    *,
    provider: LLMProvider,
    lmstudio_model: str,
    anthropic_model: str,
) -> str:
    """Model string used for the given provider (thesis / export traceability)."""
    if provider == "anthropic":
        m = (anthropic_model or "").strip()
        return m if m else "anthropic"
    m = (lmstudio_model or "").strip()
    return m if m else "lmstudio"


async def llm_complete(
    *,
    provider: LLMProvider,
    messages: list[dict[str, Any]],
    temperature: float,
    max_tokens: int,
    lmstudio_base_url: str,
    lmstudio_model: str,
    anthropic_api_key: str,
    anthropic_model: str,
    openai_compatible_api_key: str = "",
    anthropic_thinking: dict[str, Any] | None = None,
    anthropic_effort: str | None = None,
    anthropic_random_seed: int | None = None,
    llm_request_logger: Any | None = None,
    llm_request_context: dict[str, Any] | None = None,
    settings: Settings | None = None,
    llm_call_site: str = "llm_complete",
) -> LLMCompletion:
    """
    Dispatch chat completion by provider. Expects OpenAI-style messages with
    roles `system` and `user` (single pair).

    Anthropic Sonnet 5.5: thinking and effort are resolved here (or in
    ``claude_client``) so ad-hoc call sites cannot omit them.
    """
    settings = settings or get_settings()
    request_logger = resolve_llm_request_logger(run_logger=llm_request_logger, settings=settings)

    system_text = ""
    user_text = ""
    for m in messages:
        role = m.get("role")
        content = m.get("content")
        if not isinstance(content, str):
            content = str(content)
        if role == "system":
            system_text = content
        elif role == "user":
            user_text = content

    ctx = dict(llm_request_context or {})
    ctx.setdefault("call_site", llm_call_site)

    if provider == "anthropic":
        if not anthropic_api_key.strip():
            raise ValueError("anthropic_api_key is empty; set ANTHROPIC_API_KEY or choose llm_provider=lmstudio")
        wire_thinking, wire_effort, wire_seed = resolve_wire_anthropic_thinking_effort(
            model_id=anthropic_model,
            settings=settings,
            anthropic_thinking=anthropic_thinking,
            anthropic_effort=anthropic_effort,
            random_seed=anthropic_random_seed,
        )
        effective_max = sonnet_55_effective_max_tokens(anthropic_model, max_tokens, llm_call_site)
        t, inp, out = await claude_client.chat_completion_anthropic(
            api_key=anthropic_api_key,
            model=anthropic_model,
            system_prompt=system_text,
            user_prompt=user_text,
            temperature=temperature,
            max_tokens=effective_max,
            thinking=wire_thinking,
            effort=wire_effort,
            random_seed=wire_seed,
            llm_request_logger=request_logger,
            llm_request_context=ctx,
            settings=settings,
        )
        return LLMCompletion(text=t, input_tokens=inp, output_tokens=out)

    request_logger.append(
        provider=provider,
        model_id=lmstudio_model,
        thinking=None,
        effort=None,
        max_tokens=max_tokens,
        temperature=temperature,
        seed=None,
        extra=ctx,
    )

    t, inp, out = await chat_completion_openai_compatible(
        base_url=lmstudio_base_url,
        model=lmstudio_model,
        messages=messages,
        temperature=temperature,
        max_tokens=max_tokens,
        api_key=openai_compatible_api_key or None,
    )
    return LLMCompletion(text=t, input_tokens=inp, output_tokens=out)

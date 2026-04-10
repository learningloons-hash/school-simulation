from dataclasses import dataclass
from typing import Any, Literal

from mirofish_backend.llm.claude_client import chat_completion_anthropic
from mirofish_backend.llm.lmstudio_client import chat_completion_openai_compatible

LLMProvider = Literal["lmstudio", "anthropic"]


@dataclass(frozen=True)
class LLMCompletion:
    """Chat completion text plus optional token usage (Iteration 29)."""

    text: str
    input_tokens: int | None = None
    output_tokens: int | None = None


def resolve_effective_provider(
    *,
    routing_mode: str,
    round_number: int,
    turn_index: int,
) -> LLMProvider:
    """
    Map routing mode to the provider for this turn.

    hybrid: LM Studio (local) for bulk turns; Anthropic (frontier) on the **first turn of each round**
    (broadcast / policy anchor). Deterministic and replay-friendly.
    """
    _ = round_number  # reserved for future policies (e.g. frontier on policy-event rounds)
    m = (routing_mode or "lmstudio").strip().lower()
    if m == "hybrid":
        if turn_index == 1:
            return "anthropic"
        return "lmstudio"
    if m == "anthropic":
        return "anthropic"
    return "lmstudio"


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
) -> LLMCompletion:
    """
    Dispatch chat completion by provider. Expects OpenAI-style messages with
    roles `system` and `user` (single pair).
    """
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

    if provider == "anthropic":
        if not anthropic_api_key.strip():
            raise ValueError("anthropic_api_key is empty; set ANTHROPIC_API_KEY or choose llm_provider=lmstudio")
        t, inp, out = await chat_completion_anthropic(
            api_key=anthropic_api_key,
            model=anthropic_model,
            system_prompt=system_text,
            user_prompt=user_text,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        return LLMCompletion(text=t, input_tokens=inp, output_tokens=out)

    t, inp, out = await chat_completion_openai_compatible(
        base_url=lmstudio_base_url,
        model=lmstudio_model,
        messages=messages,
        temperature=temperature,
        max_tokens=max_tokens,
    )
    return LLMCompletion(text=t, input_tokens=inp, output_tokens=out)

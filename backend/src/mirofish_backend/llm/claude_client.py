import logging
from typing import Any

import httpx

from mirofish_backend.config import Settings, get_settings
from mirofish_backend.llm.anthropic_request import (
    anthropic_request_params_supported,
    resolve_wire_anthropic_thinking_effort,
)

logger = logging.getLogger("mirofish_backend.llm.claude_client")

ANTHROPIC_MESSAGES_URL = "https://api.anthropic.com/v1/messages"


def _loggable_request_record(
    *,
    model: str,
    thinking: dict[str, Any] | None,
    effort: str | None,
    max_tokens: int,
    temperature: float | None,
    seed: int | None,
) -> dict[str, Any]:
    return {
        "model_id": model,
        "thinking": thinking,
        "effort": effort,
        "max_tokens": max_tokens,
        "temperature": temperature,
        "seed": seed,
    }


async def chat_completion_anthropic(
    *,
    api_key: str,
    model: str,
    system_prompt: str,
    user_prompt: str,
    temperature: float | None,
    max_tokens: int,
    thinking: dict[str, Any] | None = None,
    effort: str | None = None,
    random_seed: int | None = None,
    timeout_s: float = 120.0,
    llm_request_logger: Any | None = None,
    llm_request_context: dict[str, Any] | None = None,
    settings: Settings | None = None,
) -> tuple[str, int | None, int | None]:
    """
    Minimal Anthropic Messages API client (system + single user turn).

    ``temperature`` is ignored (omitted from the request): current Claude models reject it.
    Sonnet 5.5 accepts ``thinking`` and ``output_config.effort`` (see migration guide).
    Thinking blocks in responses are skipped; only ``type == "text"`` blocks are concatenated.
    """
    cfg_settings = settings or get_settings()
    if anthropic_request_params_supported(model):
        resolved_thinking, resolved_effort, resolved_seed = resolve_wire_anthropic_thinking_effort(
            model_id=model,
            settings=cfg_settings,
            anthropic_thinking=thinking,
            anthropic_effort=effort,
            random_seed=random_seed,
        )
        wire_thinking = resolved_thinking
        wire_effort = resolved_effort
        log_seed = resolved_seed
    else:
        wire_thinking = None
        wire_effort = None
        log_seed = random_seed

    headers = {
        "x-api-key": api_key,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json",
    }
    payload: dict[str, Any] = {
        "model": model,
        "max_tokens": max_tokens,
        "system": system_prompt,
        "messages": [{"role": "user", "content": user_prompt}],
    }
    if wire_thinking is not None:
        payload["thinking"] = wire_thinking
    if wire_effort is not None:
        payload["output_config"] = {"effort": wire_effort}

    log_record = _loggable_request_record(
        model=model,
        thinking=wire_thinking,
        effort=wire_effort,
        max_tokens=max_tokens,
        temperature=temperature,
        seed=log_seed,
    )
    if llm_request_logger is not None:
        llm_request_logger.append(
            provider="anthropic",
            **log_record,
            extra=llm_request_context,
        )

    async with httpx.AsyncClient(timeout=timeout_s) as client:
        resp = await client.post(ANTHROPIC_MESSAGES_URL, headers=headers, json=payload)
        if resp.status_code >= 400:
            body = (resp.text or "").strip()[:500]
            raise RuntimeError(f"Anthropic API {resp.status_code}: {body or '(empty body)'}")
        data = resp.json()
    parts = data.get("content") or []
    texts: list[str] = []
    for p in parts:
        if isinstance(p, dict) and p.get("type") == "text" and isinstance(p.get("text"), str):
            texts.append(p["text"])
    out = "\n".join(texts).strip()
    if not out:
        logger.warning("Anthropic returned empty text content: %s", data)

    usage_raw = data.get("usage")
    inp_t: int | None = None
    out_t: int | None = None
    if isinstance(usage_raw, dict):
        try:
            if usage_raw.get("input_tokens") is not None:
                inp_t = int(usage_raw["input_tokens"])
            if usage_raw.get("output_tokens") is not None:
                out_t = int(usage_raw["output_tokens"])
        except (TypeError, ValueError):
            inp_t, out_t = None, None

    return out, inp_t, out_t

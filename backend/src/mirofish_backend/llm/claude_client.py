import logging
from typing import Any

import httpx

logger = logging.getLogger("mirofish_backend.llm.claude_client")

ANTHROPIC_MESSAGES_URL = "https://api.anthropic.com/v1/messages"


async def chat_completion_anthropic(
    *,
    api_key: str,
    model: str,
    system_prompt: str,
    user_prompt: str,
    temperature: float,
    max_tokens: int,
    timeout_s: float = 120.0,
) -> tuple[str, int | None, int | None]:
    """
    Minimal Anthropic Messages API client (system + single user turn).
    """
    headers = {
        "x-api-key": api_key,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json",
    }
    payload: dict[str, Any] = {
        "model": model,
        "max_tokens": max_tokens,
        "temperature": temperature,
        "system": system_prompt,
        "messages": [{"role": "user", "content": user_prompt}],
    }
    async with httpx.AsyncClient(timeout=timeout_s) as client:
        resp = await client.post(ANTHROPIC_MESSAGES_URL, headers=headers, json=payload)
        resp.raise_for_status()
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

import json
import logging
from typing import Any

import httpx

logger = logging.getLogger("mirofish_backend.llm.openai_compatible_client")


def _format_openai_compatible_error_body(status_code: int, text: str) -> str:
    text = (text or "").strip()
    if not text:
        return f"(empty response body, status {status_code})"
    try:
        data = json.loads(text)
        err = data.get("error")
        if isinstance(err, dict) and err.get("message"):
            return str(err["message"])
        if isinstance(err, str):
            return err
    except Exception:
        pass
    return text[:4000]


def _auth_headers(api_key: str | None) -> dict[str, str]:
    key = (api_key or "").strip()
    if not key:
        return {}
    return {"Authorization": f"Bearer {key}"}


async def chat_completion_openai_compatible(
    *,
    base_url: str,
    model: str,
    messages: list[dict[str, Any]],
    temperature: float,
    max_tokens: int = 512,
    timeout_s: float = 120.0,
    api_key: str | None = None,
) -> tuple[str, int | None, int | None]:
    """
    Minimal OpenAI-compatible chat.completions client.

    Works with any server that exposes ``POST {base_url}/chat/completions``
    (LM Studio, vLLM, OpenRouter, etc.). ``base_url`` is typically like
    ``http://127.0.0.1:1234/v1``.
    """
    url = f"{base_url.rstrip('/')}/chat/completions"

    payload: dict[str, Any] = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
        "stream": False,
    }

    headers = _auth_headers(api_key)
    async with httpx.AsyncClient(timeout=timeout_s) as client:
        resp = await client.post(url, json=payload, headers=headers or None)
        if resp.status_code != 200:
            detail = _format_openai_compatible_error_body(resp.status_code, resp.text)
            logger.error(
                "OpenAI-compatible chat/completions failed: status=%s model=%r detail=%s",
                resp.status_code,
                model,
                detail[:500],
            )
            raise RuntimeError(f"OpenAI-compatible HTTP {resp.status_code}: {detail}")

        data = resp.json()
        msg = data["choices"][0]["message"]

        content = msg.get("content")
        if isinstance(content, str) and content.strip():
            text_out = content
        else:
            reasoning = msg.get("reasoning_content")
            if isinstance(reasoning, str) and reasoning.strip():
                text_out = reasoning
            else:
                text_out = str(content if content is not None else reasoning)

        usage_raw = data.get("usage")
        inp_t: int | None = None
        out_t: int | None = None
        if isinstance(usage_raw, dict):
            try:
                pi = usage_raw.get("prompt_tokens")
                if pi is None:
                    pi = usage_raw.get("input_tokens")
                po = usage_raw.get("completion_tokens")
                if po is None:
                    po = usage_raw.get("output_tokens")
                if pi is not None:
                    inp_t = int(pi)
                if po is not None:
                    out_t = int(po)
            except (TypeError, ValueError):
                inp_t, out_t = None, None

        return text_out, inp_t, out_t

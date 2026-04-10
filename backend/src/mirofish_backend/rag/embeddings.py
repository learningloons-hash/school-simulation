from __future__ import annotations

import json
import logging
from typing import Any

import httpx

from mirofish_backend.llm.lmstudio_client import _format_lm_studio_error_body

logger = logging.getLogger("mirofish_backend.rag.embeddings")


async def embed_texts_openai_compatible(
    *,
    base_url: str,
    model: str,
    texts: list[str],
    timeout_s: float = 120.0,
) -> list[list[float]]:
    """
    OpenAI-compatible POST /embeddings (LM Studio local server).
    """
    url = f"{base_url.rstrip('/')}/embeddings"
    payload: dict[str, Any] = {"model": model, "input": texts}
    async with httpx.AsyncClient(timeout=timeout_s) as client:
        resp = await client.post(url, json=payload)
        if resp.status_code != 200:
            detail = _format_lm_studio_error_body(resp.status_code, resp.text)
            logger.error("LM Studio embeddings failed: status=%s detail=%s", resp.status_code, detail[:500])
            raise RuntimeError(f"LM Studio embeddings HTTP {resp.status_code}: {detail}")
        data = resp.json()
    items = data.get("data")
    if not isinstance(items, list):
        raise RuntimeError(f"embeddings response missing data list: {json.dumps(data)[:500]}")
    # Sort by index when present
    indexed: list[tuple[int, list[float]]] = []
    for i, item in enumerate(items):
        if not isinstance(item, dict):
            continue
        emb = item.get("embedding")
        if not isinstance(emb, list):
            continue
        floats = [float(x) for x in emb]
        idx = int(item.get("index", i))
        indexed.append((idx, floats))
    indexed.sort(key=lambda x: x[0])
    vectors = [v for _, v in indexed]
    if len(vectors) != len(texts):
        raise RuntimeError(f"embeddings count mismatch: got {len(vectors)} expected {len(texts)}")
    return vectors

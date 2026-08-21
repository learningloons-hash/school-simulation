"""In-process per-simulation turn embeddings for weighted memory retrieval (iter-50)."""

from __future__ import annotations

import hashlib
import logging
from collections.abc import Awaitable, Callable
from typing import Any

from mirofish_backend.rag.embeddings import embed_texts_openai_compatible
from mirofish_backend.rag.similarity import cosine_similarity

logger = logging.getLogger("mirofish_backend.rag.memory_index")

EmbedBatchFn = Callable[..., Awaitable[list[list[float]]]]

# (simulation_id, turn_id) -> embedding vector
_TURN_VECTORS: dict[tuple[str, str], list[float]] = {}
# simulation_id -> situation fingerprint -> vector (one embed per distinct situation per sim)
_SITUATION_VECTORS: dict[tuple[str, str], list[float]] = {}


def clear_memory_index_cache() -> None:
    """Test helper: drop in-memory turn/situation vectors."""
    _TURN_VECTORS.clear()
    _SITUATION_VECTORS.clear()


def _situation_key(situation_text: str) -> str:
    return hashlib.sha256(situation_text.strip().encode()).hexdigest()[:16]


def relevance_from_vectors(
    turn_vector: list[float] | None,
    situation_vector: list[float] | None,
) -> float:
    if not turn_vector or not situation_vector:
        return 0.0
    # Cosine similarity is [-1, 1]; clamp to [0, 1] for retrieval component.
    return max(0.0, min(1.0, (cosine_similarity(turn_vector, situation_vector) + 1.0) / 2.0))


def get_turn_vector(simulation_id: str, turn_id: str) -> list[float] | None:
    return _TURN_VECTORS.get((simulation_id, turn_id))


async def embed_turn(
    *,
    simulation_id: str,
    turn_id: str,
    raw_response: str,
    lmstudio_base_url: str,
    embedding_model: str,
    embed_batch: EmbedBatchFn | None = None,
) -> list[float] | None:
    """Embed a turn's ``raw_response`` and cache for the run lifetime."""
    text = (raw_response or "").strip()
    if not text:
        return None
    key = (simulation_id, turn_id)
    if key in _TURN_VECTORS:
        return _TURN_VECTORS[key]
    embed_fn = embed_batch or embed_texts_openai_compatible
    try:
        vecs = await embed_fn(base_url=lmstudio_base_url, model=embedding_model, texts=[text])
    except Exception as exc:
        logger.warning("memory index embed_turn failed sim=%s turn=%s: %s", simulation_id[:12], turn_id[:8], exc)
        return None
    if vecs:
        _TURN_VECTORS[key] = vecs[0]
        return vecs[0]
    return None


async def embed_situation(
    *,
    simulation_id: str,
    situation_text: str,
    lmstudio_base_url: str,
    embedding_model: str,
    embed_batch: EmbedBatchFn | None = None,
) -> list[float] | None:
    """Embed the pending-turn situation string (cached per sim + situation hash)."""
    text = (situation_text or "").strip()
    if not text:
        return None
    fp = _situation_key(text)
    key = (simulation_id, fp)
    if key in _SITUATION_VECTORS:
        return _SITUATION_VECTORS[key]
    embed_fn = embed_batch or embed_texts_openai_compatible
    try:
        vecs = await embed_fn(base_url=lmstudio_base_url, model=embedding_model, texts=[text])
    except Exception as exc:
        logger.warning("memory index embed_situation failed sim=%s: %s", simulation_id[:12], exc)
        return None
    if vecs:
        _SITUATION_VECTORS[key] = vecs[0]
        return vecs[0]
    return None


def memory_index_stats() -> dict[str, Any]:
    sims = {k[0] for k in _TURN_VECTORS}
    return {"turn_vectors": len(_TURN_VECTORS), "simulation_count": len(sims)}

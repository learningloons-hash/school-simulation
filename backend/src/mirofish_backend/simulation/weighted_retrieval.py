"""Weighted memory retrieval config helpers (senna-iter-50)."""

from __future__ import annotations

from typing import Any

from mirofish_backend.config import Settings
from mirofish_backend.simulation.memory_retrieval import RetrievalWeights


def resolve_weighted_retrieval_enabled(
    *,
    request_flag: bool | None,
    settings: Settings,
) -> bool:
    if request_flag is not None:
        return bool(request_flag)
    return bool(getattr(settings, "weighted_retrieval_enabled", False))


def resolve_retrieval_weights(
    *,
    settings: Settings,
    request_recency: float | None = None,
    request_importance: float | None = None,
    request_relevance: float | None = None,
) -> RetrievalWeights:
    return RetrievalWeights(
        recency=float(
            request_recency
            if request_recency is not None
            else getattr(settings, "retrieval_weight_recency", 0.5)
        ),
        importance=float(
            request_importance
            if request_importance is not None
            else getattr(settings, "retrieval_weight_importance", 0.25)
        ),
        relevance=float(
            request_relevance
            if request_relevance is not None
            else getattr(settings, "retrieval_weight_relevance", 0.25)
        ),
    )


def weighted_retrieval_config_snapshot_fields(
    *,
    enabled: bool,
    weights: RetrievalWeights,
) -> dict[str, Any]:
    w = weights.normalised()
    return {
        "weighted_retrieval_enabled": enabled,
        "retrieval_weight_recency": round(w.recency, 6),
        "retrieval_weight_importance": round(w.importance, 6),
        "retrieval_weight_relevance": round(w.relevance, 6),
    }

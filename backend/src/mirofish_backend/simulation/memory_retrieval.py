"""Weighted memory retrieval scoring (senna-iter-50)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from mirofish_backend.rag.memory_index import get_turn_vector, relevance_from_vectors

# Candidate pool cap for self-history (matches orchestrator extended-K discipline).
MEMORY_RETRIEVAL_SELF_CAP = 24


@dataclass(frozen=True)
class RetrievalWeights:
    recency: float = 0.5
    importance: float = 0.25
    relevance: float = 0.25

    def normalised(self) -> RetrievalWeights:
        total = self.recency + self.importance + self.relevance
        if total <= 0:
            return RetrievalWeights(recency=1.0, importance=0.0, relevance=0.0)
        return RetrievalWeights(
            recency=self.recency / total,
            importance=self.importance / total,
            relevance=self.relevance / total,
        )


@dataclass(frozen=True)
class RankedTurn:
    turn: dict[str, Any]
    retrieval_score: float
    recency: float
    importance: float
    relevance: float

    def signals_dict(self) -> dict[str, float]:
        return {
            "retrieval_score": round(self.retrieval_score, 6),
            "retrieval_recency": round(self.recency, 6),
            "retrieval_importance": round(self.importance, 6),
            "retrieval_relevance": round(self.relevance, 6),
        }


def build_situation_query(
    *,
    policy_event: str,
    intent_tag: str | None,
    interaction_type: str,
    target_scope: str,
) -> str:
    parts = [
        str(policy_event or "").strip(),
        str(intent_tag or "").strip(),
        str(interaction_type or "").strip(),
        str(target_scope or "").strip(),
    ]
    return " | ".join(p for p in parts if p)


def recency_components(candidates: list[dict[str, Any]]) -> dict[str, float]:
    """Monotonic recency within pool: oldest=0, newest=1 (candidates oldest→newest)."""
    n = len(candidates)
    if n == 0:
        return {}
    if n == 1:
        tid = str(candidates[0].get("id") or "")
        return {tid: 1.0} if tid else {}
    out: dict[str, float] = {}
    for i, turn in enumerate(candidates):
        tid = str(turn.get("id") or "")
        if tid:
            out[tid] = i / (n - 1)
    return out


def importance_component(importance_score: int | None) -> float:
    if importance_score is None:
        return 0.5
    return max(0.0, min(1.0, (int(importance_score) - 1) / 9.0))


def rank_turns(
    candidates: list[dict[str, Any]],
    *,
    weights: RetrievalWeights,
    simulation_id: str,
    situation_vector: list[float] | None,
    top_k: int,
) -> list[RankedTurn]:
    """Rank candidate turns and return the top ``top_k`` by weighted score."""
    if not candidates or top_k <= 0:
        return []
    w = weights.normalised()
    rec_map = recency_components(candidates)
    ranked: list[RankedTurn] = []
    for turn in candidates:
        tid = str(turn.get("id") or "")
        if not tid:
            continue
        rec = rec_map.get(tid, 0.0)
        imp = importance_component(turn.get("importance_score"))
        turn_vec = get_turn_vector(simulation_id, tid)
        rel = relevance_from_vectors(turn_vec, situation_vector)
        score = w.recency * rec + w.importance * imp + w.relevance * rel
        ranked.append(
            RankedTurn(
                turn=turn,
                retrieval_score=score,
                recency=rec,
                importance=imp,
                relevance=rel,
            )
        )
    ranked.sort(
        key=lambda r: (
            -r.retrieval_score,
            -int(r.turn.get("round_number") or 0),
            -int(r.turn.get("turn_index") or 0),
        )
    )
    return ranked[:top_k]


def self_candidate_cap(*, working_memory_last_k: int) -> int:
    return min(
        MEMORY_RETRIEVAL_SELF_CAP,
        max(working_memory_last_k * 3, working_memory_last_k + 8),
    )

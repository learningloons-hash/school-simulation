"""Per-turn memory/context inclusion instrumentation (senna-iter-45)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

from mirofish_backend.llm.context_clip import prepare_peer_response_for_prompt_with_meta

ExclusionReason = Literal["network_filtered", "recency_cut", "char_budget_truncated"] | None

CONTEXT_FETCH_CAP = 10000


@dataclass(frozen=True)
class InclusionRecord:
    round_number: int
    observer_agent_id: str
    candidate_turn_id: str
    included: bool
    exclusion_reason: ExclusionReason
    target_scope: str
    char_truncated: bool


def build_memory_context_inclusion_records(
    *,
    observer_agent_id: str,
    round_number: int,
    extended_candidates: list[dict[str, Any]],
    recency_window: list[dict[str, Any]],
    visible_turns: list[dict[str, Any]],
    peer_limit: int,
) -> list[InclusionRecord]:
    """
    Build one inclusion row per candidate turn for this observer prompt assembly.

    Layers (order): recency window → network visibility → char-budget truncation label.
    """
    recency_ids = {str(t.get("id") or "") for t in recency_window if t.get("id")}
    visible_ids = {str(t.get("id") or "") for t in visible_turns if t.get("id")}

    records: list[InclusionRecord] = []
    for turn in extended_candidates:
        turn_id = str(turn.get("id") or "")
        if not turn_id:
            continue
        target_scope = str(turn.get("target_scope") or "agent")

        if turn_id not in recency_ids:
            records.append(
                InclusionRecord(
                    round_number=round_number,
                    observer_agent_id=observer_agent_id,
                    candidate_turn_id=turn_id,
                    included=False,
                    exclusion_reason="recency_cut",
                    target_scope=target_scope,
                    char_truncated=False,
                )
            )
            continue

        if turn_id not in visible_ids:
            records.append(
                InclusionRecord(
                    round_number=round_number,
                    observer_agent_id=observer_agent_id,
                    candidate_turn_id=turn_id,
                    included=False,
                    exclusion_reason="network_filtered",
                    target_scope=target_scope,
                    char_truncated=False,
                )
            )
            continue

        clip = prepare_peer_response_for_prompt_with_meta(
            str(turn.get("raw_response") or ""),
            max_chars=peer_limit,
        )
        records.append(
            InclusionRecord(
                round_number=round_number,
                observer_agent_id=observer_agent_id,
                candidate_turn_id=turn_id,
                included=True,
                exclusion_reason="char_budget_truncated" if clip.truncated else None,
                target_scope=target_scope,
                char_truncated=clip.truncated,
            )
        )
    return records


def summarize_memory_context_log(rows: list[dict[str, Any]]) -> dict[str, Any]:
    breakdown: dict[str, int] = {
        "included_clean": 0,
        "char_budget_truncated": 0,
        "network_filtered": 0,
        "recency_cut": 0,
    }
    for row in rows:
        if not row.get("included"):
            reason = str(row.get("exclusion_reason") or "")
            if reason in breakdown:
                breakdown[reason] += 1
            continue
        if row.get("char_truncated") or row.get("exclusion_reason") == "char_budget_truncated":
            breakdown["char_budget_truncated"] += 1
        else:
            breakdown["included_clean"] += 1
    return {
        "record_count": len(rows),
        "exclusion_breakdown": breakdown,
    }


def merge_group_addressed_summary(
    memory_summary: dict[str, Any],
    group_addressed: dict[str, Any],
) -> dict[str, Any]:
    return {
        **memory_summary,
        **group_addressed,
    }

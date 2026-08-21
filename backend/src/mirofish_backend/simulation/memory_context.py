"""Per-turn memory/context inclusion instrumentation (senna-iter-45)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

from mirofish_backend.llm.context_clip import prepare_peer_response_for_prompt_with_meta

ExclusionReason = Literal[
    "recency_cut",
    "visibility_policy",
    "char_budget_truncated",
    "same_round_peer",
] | None


@dataclass(frozen=True)
class InclusionRecord:
    round_number: int
    observer_agent_id: str
    candidate_turn_id: str
    included: bool
    exclusion_reason: ExclusionReason
    target_scope: str
    char_truncated: bool
    retrieval_signals: dict[str, float] | None = None


def build_prompt_aligned_inclusion_records(
    *,
    observer_agent_id: str,
    round_number: int,
    recency_candidates: list[dict[str, Any]],
    visible_turn_ids: set[str],
    self_prompt_turn_ids: set[str],
    peer_prompt_turn_ids: set[str],
    peer_limit: int,
    retrieval_signals_by_turn_id: dict[str, dict[str, float]] | None = None,
) -> list[InclusionRecord]:
    """
    Derive inclusion rows from turns actually placed in the assembled prompt.

    Self history uses ``prior_agent_memory`` (``self_prompt_turn_ids``); peer history
    uses ``recent_interactions`` (``peer_prompt_turn_ids``). Visibility exclusions
    use ``visibility_policy`` rather than a generic network label.
    """
    records: list[InclusionRecord] = []
    signals_map = retrieval_signals_by_turn_id or {}
    for turn in recency_candidates:
        turn_id = str(turn.get("id") or "")
        if not turn_id:
            continue
        target_scope = str(turn.get("target_scope") or "agent")
        speaker_id = str(turn.get("agent_id") or "")
        turn_round = int(turn.get("round_number") or 0)

        if speaker_id == observer_agent_id:
            if turn_id not in self_prompt_turn_ids:
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
                    retrieval_signals=signals_map.get(turn_id),
                )
            )
            continue

        if turn_id not in visible_turn_ids:
            records.append(
                InclusionRecord(
                    round_number=round_number,
                    observer_agent_id=observer_agent_id,
                    candidate_turn_id=turn_id,
                    included=False,
                    exclusion_reason="visibility_policy",
                    target_scope=target_scope,
                    char_truncated=False,
                )
            )
            continue

        if turn_round == round_number and turn_id not in peer_prompt_turn_ids:
            records.append(
                InclusionRecord(
                    round_number=round_number,
                    observer_agent_id=observer_agent_id,
                    candidate_turn_id=turn_id,
                    included=False,
                    exclusion_reason="same_round_peer",
                    target_scope=target_scope,
                    char_truncated=False,
                )
            )
            continue

        if turn_id not in peer_prompt_turn_ids:
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
                retrieval_signals=signals_map.get(turn_id),
            )
        )
    return records


def build_memory_context_inclusion_records(
    *,
    observer_agent_id: str,
    round_number: int,
    extended_candidates: list[dict[str, Any]],
    recency_window: list[dict[str, Any]],
    visible_turns: list[dict[str, Any]],
    peer_limit: int,
    self_prompt_turn_ids: set[str] | None = None,
    peer_prompt_turn_ids: set[str] | None = None,
    retrieval_signals_by_turn_id: dict[str, dict[str, float]] | None = None,
) -> list[InclusionRecord]:
    """
    Build inclusion rows. When prompt-aligned id sets are supplied, records reflect
    the final prompt; otherwise falls back to legacy visibility/recency layering.
    """
    if self_prompt_turn_ids is not None and peer_prompt_turn_ids is not None:
        visible_ids = {str(t.get("id") or "") for t in visible_turns if t.get("id")}
        return build_prompt_aligned_inclusion_records(
            observer_agent_id=observer_agent_id,
            round_number=round_number,
            recency_candidates=extended_candidates,
            visible_turn_ids=visible_ids,
            self_prompt_turn_ids=self_prompt_turn_ids,
            peer_prompt_turn_ids=peer_prompt_turn_ids,
            peer_limit=peer_limit,
            retrieval_signals_by_turn_id=retrieval_signals_by_turn_id,
        )

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
                    exclusion_reason="visibility_policy",
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
        "visibility_policy": 0,
        "network_filtered": 0,
        "recency_cut": 0,
        "same_round_peer": 0,
    }
    for row in rows:
        if not row.get("included"):
            reason = str(row.get("exclusion_reason") or "")
            if reason == "network_filtered":
                breakdown["visibility_policy"] += 1
            elif reason in breakdown:
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

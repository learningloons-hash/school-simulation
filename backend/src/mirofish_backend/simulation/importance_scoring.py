"""Memory importance scoring orchestration (senna-iter-49)."""

from __future__ import annotations

import logging
from typing import Any, Literal

from mirofish_backend.config import Settings
from mirofish_backend.llm.importance_parse import (
    ImportanceSource,
    count_importance_sources,
    resolve_batch_importance_scores,
    resolve_importance_score,
)
from mirofish_backend.llm.importance_prompts import (
    IMPORTANCE_PROMPT_VERSION,
    build_batch_importance_prompt,
    build_single_turn_importance_prompt,
)
from mirofish_backend.llm.router import effective_model_id, llm_complete
from mirofish_backend.llm.routing_policies import resolve_effective_provider

logger = logging.getLogger(__name__)

ImportanceScoringMode = Literal["per_turn", "per_round_batch"]


def resolve_importance_scoring_enabled(
    *,
    request_flag: bool | None,
    settings: Settings,
) -> bool:
    if request_flag is not None:
        return bool(request_flag)
    return bool(settings.importance_scoring_enabled)


def resolve_importance_scoring_mode(
    *,
    request_mode: str | None,
    settings: Settings,
) -> ImportanceScoringMode:
    raw = (request_mode or settings.importance_scoring_mode or "per_turn").strip().lower()
    if raw not in ("per_turn", "per_round_batch"):
        return "per_turn"
    return raw  # type: ignore[return-value]


def resolve_importance_prompt_version(
    *,
    request_version: str | None,
    settings: Settings,
) -> str:
    return str(request_version or settings.importance_prompt_version or IMPORTANCE_PROMPT_VERSION)


def importance_config_snapshot_fields(
    *,
    enabled: bool,
    prompt_version: str,
    scoring_mode: ImportanceScoringMode,
) -> dict[str, Any]:
    return {
        "importance_scoring_enabled": enabled,
        "importance_prompt_version": prompt_version,
        "importance_scoring_mode": scoring_mode,
    }


async def score_turn_importance(
    *,
    raw_response: str,
    round_number: int,
    turn_index: int,
    agent_name: str,
    agent_role: str,
    prompt_version: str,
    llm_temperature: float,
    llm_max_tokens: int,
    lmstudio_base_url: str,
    lmstudio_model: str,
    anthropic_api_key: str,
    anthropic_model: str,
    openai_compatible_api_key: str,
    routing_policy: str,
    routing_profile_local_id: str,
    routing_profile_frontier_id: str,
) -> tuple[int, ImportanceSource, int, int]:
    """Dedicated LLM call for one turn. Returns (score, source, in_tokens, out_tokens)."""
    system, user = build_single_turn_importance_prompt(
        prompt_version=prompt_version,
        round_number=round_number,
        turn_index=turn_index,
        agent_name=agent_name,
        agent_role=agent_role,
        raw_response=raw_response,
    )
    effective = resolve_effective_provider(
        routing_policy=routing_policy,
        round_number=round_number,
        turn_index=turn_index,
    )
    in_acc = 0
    out_acc = 0
    try:
        completion = await llm_complete(
            provider=effective,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            temperature=llm_temperature,
            max_tokens=min(llm_max_tokens, 256),
            lmstudio_base_url=lmstudio_base_url,
            lmstudio_model=lmstudio_model,
            anthropic_api_key=anthropic_api_key,
            anthropic_model=anthropic_model,
            openai_compatible_api_key=openai_compatible_api_key,
        )
        raw = completion.text
        if completion.input_tokens is not None:
            in_acc += completion.input_tokens
        if completion.output_tokens is not None:
            out_acc += completion.output_tokens
    except Exception as exc:
        logger.warning("importance scoring LLM failed round=%s turn=%s: %s", round_number, turn_index, exc)
        raw = ""
    score, source = resolve_importance_score(raw)
    return score, source, in_acc, out_acc


async def score_round_importance_batch(
    *,
    round_number: int,
    turns: list[dict[str, Any]],
    prompt_version: str,
    llm_temperature: float,
    llm_max_tokens: int,
    lmstudio_base_url: str,
    lmstudio_model: str,
    anthropic_api_key: str,
    anthropic_model: str,
    openai_compatible_api_key: str,
    routing_policy: str,
    routing_profile_local_id: str,
    routing_profile_frontier_id: str,
) -> tuple[dict[str, tuple[int, ImportanceSource]], int, int]:
    """One LLM call scoring all turns in a round. Returns (scores_by_turn_id, in, out)."""
    if not turns:
        return {}, 0, 0
    system, user = build_batch_importance_prompt(
        prompt_version=prompt_version,
        round_number=round_number,
        turns=turns,
    )
    effective = resolve_effective_provider(
        routing_policy=routing_policy,
        round_number=round_number,
        turn_index=998,
    )
    in_acc = 0
    out_acc = 0
    expected_ids = [str(t["turn_id"]) for t in turns]
    try:
        completion = await llm_complete(
            provider=effective,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            temperature=llm_temperature,
            max_tokens=min(llm_max_tokens, 1024),
            lmstudio_base_url=lmstudio_base_url,
            lmstudio_model=lmstudio_model,
            anthropic_api_key=anthropic_api_key,
            anthropic_model=anthropic_model,
            openai_compatible_api_key=openai_compatible_api_key,
        )
        raw = completion.text
        if completion.input_tokens is not None:
            in_acc += completion.input_tokens
        if completion.output_tokens is not None:
            out_acc += completion.output_tokens
    except Exception as exc:
        logger.warning("batch importance scoring failed round=%s: %s", round_number, exc)
        raw = ""
    parsed = resolve_batch_importance_scores(raw, expected_turn_ids=expected_ids)
    return parsed, in_acc, out_acc


def merge_importance_audit(
    audit: dict[str, int],
    *,
    score: int,
    source: ImportanceSource,
) -> None:
    audit[source] = audit.get(source, 0) + 1


def finalize_importance_audit(audit: dict[str, int]) -> dict[str, Any]:
    return {"importance_scoring_audit": dict(audit)}


__all__ = [
    "ImportanceScoringMode",
    "count_importance_sources",
    "finalize_importance_audit",
    "importance_config_snapshot_fields",
    "merge_importance_audit",
    "resolve_importance_prompt_version",
    "resolve_importance_scoring_enabled",
    "resolve_importance_scoring_mode",
    "score_round_importance_batch",
    "score_turn_importance",
]

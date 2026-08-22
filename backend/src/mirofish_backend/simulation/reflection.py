"""Agent reflection orchestration (senna-iter-51)."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

from mirofish_backend.config import Settings
from mirofish_backend.llm.importance_parse import FALLBACK_SCORE
from mirofish_backend.llm.reflection_parse import ReflectionSource, resolve_reflection
from mirofish_backend.llm.reflection_prompts import REFLECTION_PROMPT_VERSION, build_reflection_prompt
from mirofish_backend.llm.router import llm_complete
from mirofish_backend.llm.routing_policies import resolve_effective_provider

logger = logging.getLogger(__name__)

REFLECTION_MEMORY_TURN_INDEX = 1000


@dataclass
class PendingObservation:
    turn_id: str
    importance_score: int
    raw_response: str
    round_number: int
    turn_index: int


@dataclass
class ReflectionAccumulator:
    pending: list[PendingObservation] = field(default_factory=list)

    def accumulated_importance(self) -> int:
        return sum(p.importance_score for p in self.pending)

    def clear(self) -> None:
        self.pending.clear()


def resolve_reflection_enabled(
    *,
    request_flag: bool | None,
    settings: Settings,
) -> bool:
    if request_flag is not None:
        return bool(request_flag)
    return bool(getattr(settings, "reflection_enabled", False))


def resolve_reflection_trigger_threshold(
    *,
    request_threshold: int | None,
    settings: Settings,
) -> int:
    if request_threshold is not None:
        return max(1, int(request_threshold))
    return max(1, int(getattr(settings, "reflection_trigger_threshold", 150)))


def resolve_reflection_prompt_version(
    *,
    request_version: str | None,
    settings: Settings,
) -> str:
    return str(request_version or getattr(settings, "reflection_prompt_version", REFLECTION_PROMPT_VERSION))


def reflection_config_snapshot_fields(
    *,
    enabled: bool,
    trigger_threshold: int,
    prompt_version: str,
) -> dict[str, Any]:
    return {
        "reflection_enabled": enabled,
        "reflection_trigger_threshold": int(trigger_threshold),
        "reflection_prompt_version": prompt_version,
    }


def merge_reflection_audit(audit: dict[str, int], *, source: ReflectionSource) -> None:
    audit[source] = audit.get(source, 0) + 1


def format_self_memory_line(row: dict[str, Any]) -> str:
    text = str(row.get("raw_response") or "").strip()
    if row.get("memory_kind") == "reflection":
        return f"[reflection] {text}"
    return text


def reflection_row_to_memory_candidate(reflection: dict[str, Any]) -> dict[str, Any]:
    source_ids = reflection.get("source_turn_ids") or []
    n_sources = max(1, len(source_ids))
    acc = int(reflection.get("accumulated_importance") or 0)
    imp = min(10, max(1, acc // n_sources))
    return {
        "id": str(reflection["id"]),
        "round_number": int(reflection["round_number"]),
        "turn_index": REFLECTION_MEMORY_TURN_INDEX,
        "agent_id": str(reflection["agent_id"]),
        "agent_name": reflection.get("agent_name"),
        "interaction_type": "reflection",
        "target_scope": "agent",
        "target_agent_name": "self",
        "raw_response": str(reflection.get("reflection_text") or ""),
        "importance_score": imp,
        "memory_kind": "reflection",
    }


def merge_self_memory_candidates(
    turn_rows: list[dict[str, Any]],
    reflection_rows: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    merged = list(turn_rows) + [reflection_row_to_memory_candidate(r) for r in reflection_rows]
    merged.sort(
        key=lambda r: (
            int(r.get("round_number") or 0),
            int(r.get("turn_index") or 0),
            str(r.get("id") or ""),
        )
    )
    return merged


def take_last_k_memory_rows(rows: list[dict[str, Any]], k: int) -> list[dict[str, Any]]:
    if k <= 0 or not rows:
        return []
    return rows[-k:]


async def synthesize_reflection(
    *,
    agent_name: str,
    agent_role: str,
    round_number: int,
    observations: list[PendingObservation],
    prompt_version: str,
    llm_temperature: float,
    llm_max_tokens: int,
    lmstudio_base_url: str,
    lmstudio_model: str,
    anthropic_api_key: str,
    anthropic_model: str,
    openai_compatible_api_key: str,
    routing_policy: str,
) -> tuple[str, list[str], ReflectionSource, int, int]:
    obs_payload = [
        {
            "turn_id": o.turn_id,
            "round_number": o.round_number,
            "turn_index": o.turn_index,
            "importance_score": o.importance_score,
            "raw_response": o.raw_response,
        }
        for o in observations
    ]
    system, user = build_reflection_prompt(
        prompt_version=prompt_version,
        agent_name=agent_name,
        agent_role=agent_role,
        round_number=round_number,
        observations=obs_payload,
    )
    effective = resolve_effective_provider(
        routing_policy=routing_policy,
        round_number=round_number,
        turn_index=999,
    )
    in_acc = 0
    out_acc = 0
    fallback_ids = [o.turn_id for o in observations]
    try:
        completion = await llm_complete(
            provider=effective,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            temperature=llm_temperature,
            max_tokens=min(llm_max_tokens, 512),
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
        logger.warning("reflection LLM failed round=%s agent=%s: %s", round_number, agent_name, exc)
        raw = ""
    text, sources, source = resolve_reflection(raw, fallback_source_turn_ids=fallback_ids)
    return text, sources, source, in_acc, out_acc


def observation_importance_for_reflection(importance_score: int | None) -> int:
    if importance_score is None:
        return FALLBACK_SCORE
    return int(importance_score)

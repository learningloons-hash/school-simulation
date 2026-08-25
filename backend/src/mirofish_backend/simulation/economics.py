"""Run economics: token-derived USD estimates for thesis RQ2 (Iteration 29).

Default list prices are snapshots only — override generic Anthropic fallback via
``ANTHROPIC_INPUT_PRICE_PER_MTOK`` / ``ANTHROPIC_OUTPUT_PRICE_PER_MTOK`` when needed.
Per-model keys (Haiku, Opus, etc.) use ``PROVIDER_PRICE_MAP`` entries (iter-56).
"""

from __future__ import annotations

import os
from typing import Any

from mirofish_backend.config import Settings
from mirofish_backend.llm.model_profiles import get_builtin_profile, resolve_anthropic_pricing_key
from mirofish_backend.llm.routing_policies import HEURISTIC_PROFILE_SENTINEL

# Date associated with default ``PROVIDER_PRICE_MAP`` values (cite in thesis appendices).
PRICE_MAP_DATE = "2026-08-25"

PROVIDER_PRICE_MAP: dict[str, dict[str, float]] = {
    # Sonnet-tier fallback for unknown Anthropic model ids.
    "anthropic": {"input_per_mtok": 3.00, "output_per_mtok": 15.00},
    "anthropic_haiku_3_5": {"input_per_mtok": 0.80, "output_per_mtok": 4.00},
    "anthropic_haiku_4_5": {"input_per_mtok": 1.00, "output_per_mtok": 5.00},
    "anthropic_sonnet": {"input_per_mtok": 3.00, "output_per_mtok": 15.00},
    "anthropic_opus_4": {"input_per_mtok": 15.00, "output_per_mtok": 75.00},
    "anthropic_opus_5": {"input_per_mtok": 5.00, "output_per_mtok": 25.00},
    "lmstudio": {"input_per_mtok": 0.00, "output_per_mtok": 0.00},
    "openai": {"input_per_mtok": 0.15, "output_per_mtok": 0.60},
    "openrouter": {"input_per_mtok": 0.15, "output_per_mtok": 0.60},
    # Per-turn billing resolves ``pricing_key`` from ``effective_profile_id`` (Arc 8 GM follow-up).
    # Kept so callers
    # can pass ``provider_key="hybrid"`` to ``estimate_cost_usd`` for an upper-bound envelope (all
    # tokens at frontier rates) without duplicating numbers; run-level payloads use per-turn sums instead.
    "hybrid": {"input_per_mtok": 3.00, "output_per_mtok": 15.00},
}


def _per_mtok_rates(provider_key: str) -> tuple[float, float]:
    """Resolve input/output USD per million tokens for a logical provider bucket."""
    env_in = os.environ.get("ANTHROPIC_INPUT_PRICE_PER_MTOK")
    env_out = os.environ.get("ANTHROPIC_OUTPUT_PRICE_PER_MTOK")
    defaults = PROVIDER_PRICE_MAP.get(provider_key) or PROVIDER_PRICE_MAP["anthropic"]
    pk = (provider_key or "").strip().lower()
    if pk == "anthropic" and env_in is not None and env_in.strip():
        din = float(env_in)
    else:
        din = float(defaults["input_per_mtok"])
    if pk == "anthropic" and env_out is not None and env_out.strip():
        dout = float(env_out)
    else:
        dout = float(defaults["output_per_mtok"])
    return din, dout


def estimate_cost_usd(*, input_tokens: int, output_tokens: int, provider_key: str) -> float:
    """
    Estimated USD from token counts using list-price defaults (or env overrides for Anthropic).

    ``provider_key``: ``lmstudio`` → always 0; other keys resolve via ``PROVIDER_PRICE_MAP`` (with
    unknown keys falling back to ``anthropic`` rates in ``_per_mtok_rates``). ``hybrid`` uses the
    map entry for envelope-style estimates; per-run totals in the API use per-turn billing instead.
    """
    pk = (provider_key or "lmstudio").strip().lower()
    if pk == "lmstudio":
        return 0.0
    din, dout = _per_mtok_rates(pk)
    return round((input_tokens / 1_000_000.0) * din + (output_tokens / 1_000_000.0) * dout, 6)


def _builtin_profile_pricing_key(profile_id: str) -> str | None:
    """Built-in profile ``pricing_key`` for post-run billing (no API keys)."""
    profile = get_builtin_profile(profile_id, Settings())
    if profile is None:
        return None
    if profile.provider_type == "anthropic":
        return resolve_anthropic_pricing_key(profile.model_id)
    return profile.pricing_key


def resolve_billing_provider_key(
    *,
    effective_profile_id: str | None,
    effective_provider: str | None,
    effective_model: str | None = None,
) -> str:
    """
    Map a transcript row to a ``PROVIDER_PRICE_MAP`` key for ``estimate_cost_usd``.

    Prefer ``effective_profile_id`` → built-in ``pricing_key``. Tier-3 ``heuristic`` → $0.
    Anthropic rows prefer ``effective_model`` when set. Missing profile id → legacy provider fallback.
    """
    pid = (effective_profile_id or "").strip()
    if pid:
        if pid == HEURISTIC_PROFILE_SENTINEL:
            return "lmstudio"
        pk = _builtin_profile_pricing_key(pid)
        if pk is not None:
            profile = get_builtin_profile(pid, Settings())
            if profile is not None and profile.provider_type == "anthropic":
                model_id = (effective_model or profile.model_id or "").strip()
                if model_id:
                    return resolve_anthropic_pricing_key(model_id)
            return pk

    prov = (effective_provider or "").strip().lower()
    if prov == "anthropic":
        model_id = (effective_model or "").strip()
        if model_id:
            return resolve_anthropic_pricing_key(model_id)
        return "anthropic"
    return "lmstudio"


def _turn_cost_usd(
    effective_provider: str | None,
    effective_profile_id: str | None,
    inp: int | None,
    out: int | None,
    effective_model: str | None = None,
) -> float:
    """Bill one transcript row from profile ``pricing_key`` or legacy provider fallback."""
    if inp is None or out is None:
        return 0.0
    pk = resolve_billing_provider_key(
        effective_profile_id=effective_profile_id,
        effective_provider=effective_provider,
        effective_model=effective_model,
    )
    return estimate_cost_usd(input_tokens=inp, output_tokens=out, provider_key=pk)


def tier_breakdown_from_transcript(transcript: list[dict[str, Any]]) -> dict[str, int]:
    tb = {"tier_1_turns": 0, "tier_2_turns": 0, "tier_3_turns": 0}
    for row in transcript:
        try:
            t = int(row.get("fidelity_tier") or 1)
        except (TypeError, ValueError):
            t = 1
        if t == 1:
            tb["tier_1_turns"] += 1
        elif t == 2:
            tb["tier_2_turns"] += 1
        else:
            tb["tier_3_turns"] += 1
    return tb


def estimated_run_cost_usd_from_transcript(transcript: list[dict[str, Any]]) -> float:
    """Sum per-turn estimates using ``effective_profile_id`` (fallback: ``effective_provider``)."""
    total = 0.0
    for row in transcript:
        total += _turn_cost_usd(
            row.get("effective_provider"),
            row.get("effective_profile_id"),
            row.get("input_tokens") if row.get("input_tokens") is not None else None,
            row.get("output_tokens") if row.get("output_tokens") is not None else None,
            effective_model=row.get("effective_model"),
        )
    return round(total, 6)


def likert_billing_rows_from_responses(likert_responses: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """One USD billing row per agent-round Likert LLM call (dedupe per-indicator rows)."""
    seen: set[tuple[int, str]] = set()
    rows: list[dict[str, Any]] = []
    for lr in likert_responses:
        rnd = int(lr.get("round_number") or 0)
        agent_id = str(lr.get("agent_id") or "")
        key = (rnd, agent_id)
        if key in seen:
            continue
        seen.add(key)
        inp = lr.get("input_tokens")
        out = lr.get("output_tokens")
        if inp is None and out is None:
            continue
        rows.append(
            {
                "effective_provider": lr.get("effective_provider"),
                "effective_model": lr.get("effective_model"),
                "effective_profile_id": lr.get("effective_profile_id"),
                "input_tokens": inp,
                "output_tokens": out,
            }
        )
    return rows


def build_run_economics_payload(
    transcript: list[dict[str, Any]],
    *,
    total_input_tokens: int | None,
    total_output_tokens: int | None,
    llm_provider: str,
    likert_responses: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """
    Shape returned on ``GET /simulations/{id}``, export ``run.economics``, and experiment run rows.
    """
    billing_rows = list(transcript)
    billing_rows.extend(likert_billing_rows_from_responses(likert_responses or []))
    tier = tier_breakdown_from_transcript(transcript)
    likert_turns = len(likert_billing_rows_from_responses(likert_responses or []))
    if likert_turns:
        tier = dict(tier)
        tier["likert_self_report_turns"] = likert_turns
    cost = estimated_run_cost_usd_from_transcript(billing_rows)
    return {
        "total_input_tokens": total_input_tokens,
        "total_output_tokens": total_output_tokens,
        "estimated_cost_usd": cost,
        "llm_provider": (llm_provider or "lmstudio").strip().lower(),
        "tier_breakdown": tier,
    }

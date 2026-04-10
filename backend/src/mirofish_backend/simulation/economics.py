"""Run economics: token-derived USD estimates for thesis RQ2 (Iteration 29).

Default list prices are snapshots only — override with env vars when provider pricing changes.
"""

from __future__ import annotations

import os
from typing import Any

# Date associated with default ``PROVIDER_PRICE_MAP`` values (cite in thesis appendices).
PRICE_MAP_DATE = "2026-04-07"

PROVIDER_PRICE_MAP: dict[str, dict[str, float]] = {
    "anthropic": {"input_per_mtok": 3.00, "output_per_mtok": 15.00},
    "lmstudio": {"input_per_mtok": 0.00, "output_per_mtok": 0.00},
    # Not used by per-turn billing (`_turn_cost_usd` keys off `effective_provider`). Kept so callers
    # can pass ``provider_key="hybrid"`` to ``estimate_cost_usd`` for an upper-bound envelope (all
    # tokens at frontier rates) without duplicating numbers; run-level payloads use per-turn sums instead.
    "hybrid": {"input_per_mtok": 3.00, "output_per_mtok": 15.00},
}


def _per_mtok_rates(provider_key: str) -> tuple[float, float]:
    """Resolve input/output USD per million tokens for a logical provider bucket."""
    env_in = os.environ.get("ANTHROPIC_INPUT_PRICE_PER_MTOK")
    env_out = os.environ.get("ANTHROPIC_OUTPUT_PRICE_PER_MTOK")
    defaults = PROVIDER_PRICE_MAP.get(provider_key) or PROVIDER_PRICE_MAP["anthropic"]
    din = float(env_in) if env_in is not None and env_in.strip() else float(defaults["input_per_mtok"])
    dout = float(env_out) if env_out is not None and env_out.strip() else float(defaults["output_per_mtok"])
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


def _turn_cost_usd(effective_provider: str | None, inp: int | None, out: int | None) -> float:
    """Bill one transcript row: only Anthropic turns with known usage contribute."""
    if inp is None or out is None:
        return 0.0
    prov = (effective_provider or "").strip().lower()
    if prov in ("anthropic",):
        return estimate_cost_usd(input_tokens=inp, output_tokens=out, provider_key="anthropic")
    # lmstudio, heuristic, none, etc. → $0
    return 0.0


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
    """Sum per-turn estimates using ``effective_provider`` (hybrid runs: Anthropic rows only)."""
    total = 0.0
    for row in transcript:
        total += _turn_cost_usd(
            row.get("effective_provider"),
            row.get("input_tokens") if row.get("input_tokens") is not None else None,
            row.get("output_tokens") if row.get("output_tokens") is not None else None,
        )
    return round(total, 6)


def build_run_economics_payload(
    transcript: list[dict[str, Any]],
    *,
    total_input_tokens: int | None,
    total_output_tokens: int | None,
    llm_provider: str,
) -> dict[str, Any]:
    """
    Shape returned on ``GET /simulations/{id}``, export ``run.economics``, and experiment run rows.
    """
    tier = tier_breakdown_from_transcript(transcript)
    cost = estimated_run_cost_usd_from_transcript(transcript)
    return {
        "total_input_tokens": total_input_tokens,
        "total_output_tokens": total_output_tokens,
        "estimated_cost_usd": cost,
        "llm_provider": (llm_provider or "lmstudio").strip().lower(),
        "tier_breakdown": tier,
    }

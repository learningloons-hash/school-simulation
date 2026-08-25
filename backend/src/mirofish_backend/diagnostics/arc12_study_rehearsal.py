"""Arc 12 study-scale rehearsal harness (senna-iter-55)."""

from __future__ import annotations

import statistics
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from mirofish_backend.simulation.network import NetworkParseResult, parse_network_csv

DEFAULT_STUDY_SEEDS: tuple[int, ...] = (42, 43, 44)
DEFAULT_RQ1_ROUND_COUNTS: tuple[int, ...] = (15, 20)
DEFAULT_SCENARIO_ID = "ciepss_school_b"
DEFAULT_AGENT_LIMIT = 8
DEFAULT_NETWORK_CSV_REL = "docs/research/fixtures/ciepss_school_b_network.csv"

# GM-F ruling pending (iter-54 → iter-55 gate); iter-53 frozen defaults until ruled otherwise.
INTERIM_MECHANISM_FLAGS: dict[str, bool] = {
    "importance_scoring_enabled": False,
    "weighted_retrieval_enabled": False,
    "reflection_enabled": False,
}


@dataclass(frozen=True)
class StudyRehearsalProfile:
    scenario_id: str = DEFAULT_SCENARIO_ID
    agent_limit: int = DEFAULT_AGENT_LIMIT
    visibility_policy: str = "network_bounded"
    sampling_strategy: str = "full_census"


@dataclass
class StudyRehearsalRunRecord:
    label: str
    rounds: int
    seed: int
    simulation_id: str
    status: str
    mechanics: dict[str, Any] = field(default_factory=dict)


def build_expected_run_agent_ids(*, persona_ids: list[str]) -> list[str]:
    """Run agent ids in slot order: ``{persona_id}_{slot:03d}``."""
    return [f"{pid}_{i:03d}" for i, pid in enumerate(persona_ids)]


def load_documented_network_csv(
    *,
    study_repo_path: Path,
    rel_path: str,
    expected_agent_ids: frozenset[str],
) -> tuple[str, NetworkParseResult]:
    """
    Load CIEPSS documented network CSV from the study repo checkout.

    Validates parsed edges against ``expected_agent_ids`` for this run. Rows
    referencing unknown endpoints are skipped by :func:`parse_network_csv` with
    warnings; if no valid edges remain, raises ``ValueError``.
    """
    csv_path = (study_repo_path / rel_path).resolve()
    if not csv_path.is_file():
        raise FileNotFoundError(f"documented network CSV not found: {csv_path}")
    text = csv_path.read_text(encoding="utf-8")
    result = parse_network_csv(text, known_agent_ids=expected_agent_ids)
    if not result.edges:
        raise ValueError(
            f"network CSV {csv_path} produced no valid edges for expected agents "
            f"{sorted(expected_agent_ids)!r}; warnings={list(result.warnings)}",
        )
    referenced = {s for s, _t, _w in result.edges} | {t for _s, t, _w in result.edges}
    unknown_in_file = referenced - expected_agent_ids
    if unknown_in_file:
        raise ValueError(
            f"network CSV references agent ids not in this run: {sorted(unknown_in_file)!r}",
        )
    return text, result


def count_llm_errors(transcript: list[dict[str, Any]]) -> int:
    return sum(
        1 for t in transcript if str(t.get("raw_response") or "").startswith("[LLM error]")
    )


def count_context_length_failures(transcript: list[dict[str, Any]]) -> int:
    count = 0
    for t in transcript:
        raw = str(t.get("raw_response") or "").lower()
        if any(
            phrase in raw
            for phrase in (
                "context length",
                "context_length",
                "maximum context",
                "too many tokens",
                "prompt is too long",
            )
        ):
            count += 1
    return count


def token_totals_by_round(transcript: list[dict[str, Any]]) -> dict[int, dict[str, int]]:
    by_round: dict[int, dict[str, int]] = {}
    for t in transcript:
        rn = int(t.get("round_number") or 0)
        if rn <= 0:
            continue
        bucket = by_round.setdefault(rn, {"input_tokens": 0, "output_tokens": 0, "turns": 0})
        bucket["input_tokens"] += int(t.get("input_tokens") or 0)
        bucket["output_tokens"] += int(t.get("output_tokens") or 0)
        bucket["turns"] += 1
    return dict(sorted(by_round.items()))


def state_update_source_counts(transcript: list[dict[str, Any]]) -> dict[str, int]:
    counts: Counter[str] = Counter()
    for t in transcript:
        src = t.get("state_update_source")
        if src:
            counts[str(src)] += 1
    return dict(sorted(counts.items()))


def final_round_support_stdev(bundle: dict[str, Any]) -> float | None:
    snapshots = bundle.get("agent_state_snapshots") or []
    run = bundle.get("run") or {}
    total_rounds = int(run.get("total_rounds") or 0)
    if total_rounds <= 0:
        return None
    levels = [
        float(row.get("support_level") or 0.0)
        for row in snapshots
        if int(row.get("round_number") or 0) == total_rounds
    ]
    if len(levels) < 2:
        return None
    return round(statistics.pstdev(levels), 6)


def extract_mechanics_metrics(*, bundle: dict[str, Any], wall_clock_seconds: float) -> dict[str, Any]:
    """Mechanics-only aggregates for study rehearsal (no substantive scoring)."""
    run = bundle.get("run") or {}
    cfg = run.get("config_snapshot") or {}
    econ = run.get("economics") or {}
    transcript = bundle.get("transcript") or []
    memory = bundle.get("memory_context_summary") or {}

    return {
        "wall_clock_seconds": round(wall_clock_seconds, 3),
        "total_input_tokens": run.get("total_input_tokens"),
        "total_output_tokens": run.get("total_output_tokens"),
        "estimated_cost_usd": econ.get("estimated_cost_usd"),
        "llm_error_count": count_llm_errors(transcript),
        "context_length_failure_count": count_context_length_failures(transcript),
        "group_addressed_proportion": memory.get("group_addressed_proportion"),
        "memory_exclusion_breakdown": dict(memory.get("exclusion_breakdown") or {}),
        "state_update_source_counts": state_update_source_counts(transcript),
        "token_totals_by_round": token_totals_by_round(transcript),
        "final_round_support_stdev": final_round_support_stdev(bundle),
        "network_csv_applied": cfg.get("network_csv_applied"),
        "network_edge_count": cfg.get("network_edge_count"),
        "visibility_effective": cfg.get("interaction_policy", {}).get("visibility_effective")
        if isinstance(cfg.get("interaction_policy"), dict)
        else cfg.get("visibility_effective"),
    }


def build_rq1_run_plan(*, round_counts: list[int], seeds: list[int]) -> list[tuple[str, int, int]]:
    """Return (label, rounds, seed) tuples for RQ1 matrix."""
    plan: list[tuple[str, int, int]] = []
    for rounds in round_counts:
        for seed in seeds:
            plan.append((f"RQ1-{rounds}", rounds, seed))
    return plan


def build_results_payload(
    *,
    profile: StudyRehearsalProfile,
    records: list[StudyRehearsalRunRecord],
    command: str,
    interim_flags: dict[str, bool],
    rq2_skipped: bool,
    rq2_note: str | None,
    network_csv_rel_path: str,
) -> dict[str, Any]:
    return {
        "harness": "senna-iter-55",
        "profile": {
            "scenario_id": profile.scenario_id,
            "agent_limit": profile.agent_limit,
            "visibility_policy": profile.visibility_policy,
            "sampling_strategy": profile.sampling_strategy,
            "network_csv_rel_path": network_csv_rel_path,
            "network_csv_note": "documented CIEPSS links from study repo (not synthetic chain)",
        },
        "interim_mechanism_flags": interim_flags,
        "interim_flags_note": "GM-F formal ruling pending; iter-53 frozen defaults until ruled otherwise.",
        "rq2": {"skipped": rq2_skipped, "note": rq2_note},
        "command": command,
        "runs": [
            {
                "label": r.label,
                "rounds": r.rounds,
                "seed": r.seed,
                "simulation_id": r.simulation_id,
                "status": r.status,
                "mechanics": r.mechanics,
            }
            for r in records
        ],
    }


def generate_rehearsal_markdown(payload: dict[str, Any]) -> str:
    profile = payload.get("profile") or {}
    flags = payload.get("interim_mechanism_flags") or {}
    lines = [
        "# Arc 12 study rehearsal results",
        "",
        f"**Harness:** {payload.get('harness', 'senna-iter-55')}",
        f"**Command:** `{payload.get('command', '')}`",
        "",
        "## Profile",
        "",
        f"- Scenario: `{profile.get('scenario_id')}`",
        f"- Agents: {profile.get('agent_limit')}",
        f"- Visibility: `{profile.get('visibility_policy')}` (+ documented network CSV)",
        f"- Network CSV: `{profile.get('network_csv_rel_path')}`",
        f"- Note: {profile.get('network_csv_note', '')}",
        "",
        "## Interim mechanism flags (GM-F ruling pending)",
        "",
        f"- `importance_scoring_enabled`: {flags.get('importance_scoring_enabled')}",
        f"- `weighted_retrieval_enabled`: {flags.get('weighted_retrieval_enabled')}",
        f"- `reflection_enabled`: {flags.get('reflection_enabled')}",
        "",
        f"*{payload.get('interim_flags_note', '')}*",
        "",
    ]
    rq2 = payload.get("rq2") or {}
    if rq2.get("skipped"):
        lines.extend(["## RQ2", "", f"**Deferred:** {rq2.get('note', 'skipped via --skip-rq2')}", ""])
    runs = payload.get("runs") or []
    if runs:
        lines.extend(
            [
                "## Run mechanics summary",
                "",
                "| Label | Seed | Rounds | Status | Input tokens | Cost USD | Wall s | LLM errors | Ctx failures | Support stdev |",
                "|-------|------|--------|--------|--------------|----------|--------|------------|--------------|---------------|",
            ]
        )
        for r in runs:
            m = r.get("mechanics") or {}
            lines.append(
                "| {label} | {seed} | {rounds} | {status} | {inp} | {cost} | {wall} | {llm} | {ctx} | {sd} |".format(
                    label=r.get("label"),
                    seed=r.get("seed"),
                    rounds=r.get("rounds"),
                    status=r.get("status"),
                    inp=m.get("total_input_tokens"),
                    cost=m.get("estimated_cost_usd"),
                    wall=m.get("wall_clock_seconds"),
                    llm=m.get("llm_error_count"),
                    ctx=m.get("context_length_failure_count"),
                    sd=m.get("final_round_support_stdev"),
                )
            )
        lines.append("")
        lines.append(
            "*Mechanics only — substantive outputs not read, cited, or scored (Arc 12 standing constraint).*"
        )
    return "\n".join(lines) + "\n"

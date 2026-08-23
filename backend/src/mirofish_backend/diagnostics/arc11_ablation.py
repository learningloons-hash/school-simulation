"""Arc 11 memory-mechanism ablation harness (senna-iter-52)."""

from __future__ import annotations

import json
import statistics
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal

from mirofish_backend.diagnostics.arc10_baseline import (
    interview_category_averages,
    membench_recall_reflective_averages,
)
from mirofish_backend.scenarios.registry import get_scenario

AblationCondition = Literal[
    "baseline",
    "+importance",
    "+importance+retrieval",
    "+importance+retrieval+reflection",
]

ABLATION_CONDITIONS: tuple[AblationCondition, ...] = (
    "baseline",
    "+importance",
    "+importance+retrieval",
    "+importance+retrieval+reflection",
)

DEFAULT_ABLATION_SEEDS: tuple[int, ...] = (42, 43, 44)


@dataclass(frozen=True)
class AblationRunProfile:
    scenario_id: str = "fsbb_comparator"
    agent_limit: int = 3
    total_rounds: int = 5
    visibility_policy: str = "network_bounded"
    sampling_strategy: str = "full_census"


@dataclass
class AblationRunRecord:
    condition: str
    seed: int
    simulation_id: str
    wall_clock_seconds: float
    diagnostics: dict[str, Any]
    cost: dict[str, Any]
    dispersion: dict[str, Any]
    metrics: dict[str, Any]
    deltas_vs_baseline: dict[str, Any] = field(default_factory=dict)


def condition_memory_flags(condition: str) -> dict[str, bool]:
    """Map ablation condition name to simulation memory flags (cumulative ladder)."""
    name = (condition or "baseline").strip()
    if name not in ABLATION_CONDITIONS:
        raise ValueError(f"unknown ablation condition {condition!r}; expected one of {ABLATION_CONDITIONS}")
    flags: dict[str, bool] = {
        "importance_scoring_enabled": False,
        "weighted_retrieval_enabled": False,
        "reflection_enabled": False,
    }
    if name == "baseline":
        return flags
    flags["importance_scoring_enabled"] = True
    if name == "+importance":
        return flags
    flags["weighted_retrieval_enabled"] = True
    if name == "+importance+retrieval":
        return flags
    flags["reflection_enabled"] = True
    return flags


def build_network_csv_for_scenario(*, scenario_id: str, agent_limit: int) -> str:
    """Build a valid network CSV for ``network_bounded`` visibility (no broadcast fallback)."""
    cfg = get_scenario(scenario_id)
    personas = cfg.personas[:agent_limit]
    if len(personas) < 2:
        raise ValueError(f"agent_limit must be >= 2 for network CSV; got {agent_limit}")
    agent_ids = [f"{p.persona_id}_{i:03d}" for i, p in enumerate(personas)]
    lines = ["source_agent_id,target_agent_id,influence_weight"]
    for i in range(len(agent_ids) - 1):
        lines.append(f"{agent_ids[i]},{agent_ids[i + 1]},0.5")
    if len(agent_ids) >= 3:
        lines.append(f"{agent_ids[0]},{agent_ids[2]},0.3")
    return "\n".join(lines) + "\n"


def extract_normalized_metrics(diagnostics_summary: dict[str, Any]) -> dict[str, Any]:
    """Flatten Arc 10 diagnostics into comparable scalars for delta reporting."""
    membench = diagnostics_summary.get("membench") or {}
    interview = diagnostics_summary.get("architectural_interview") or {}
    memory = diagnostics_summary.get("memory_context") or {}
    mb_factual, mb_reflective = membench_recall_reflective_averages(membench)
    cat_means = interview_category_averages(interview.get("scores") or [])
    exclusion = dict(memory.get("exclusion_breakdown") or {})
    return {
        "membench_factual_mean": mb_factual,
        "membench_reflective_mean": mb_reflective,
        "interview_category_means": cat_means,
        "memory_group_addressed_proportion": memory.get("group_addressed_proportion"),
        "memory_exclusion_breakdown": exclusion,
        "memory_included_clean": int(exclusion.get("included_clean") or 0),
        "memory_recency_cut": int(exclusion.get("recency_cut") or 0),
    }


def compute_dispersion_metrics(
    *,
    export_bundle: dict[str, Any],
    diagnostics_summary: dict[str, Any],
) -> dict[str, Any]:
    """Between-agent dispersion: final-round support stdev + interview category stdev."""
    snapshots = export_bundle.get("agent_state_snapshots") or []
    run = export_bundle.get("run") or {}
    total_rounds = int(run.get("total_rounds") or 0)
    final_support: list[float] = []
    if total_rounds > 0:
        for row in snapshots:
            if int(row.get("round_number") or 0) == total_rounds:
                final_support.append(float(row.get("support_level") or 0.0))
    support_stdev = (
        round(statistics.pstdev(final_support), 6) if len(final_support) >= 2 else None
    )

    scores = (diagnostics_summary.get("architectural_interview") or {}).get("scores") or []
    by_agent: dict[str, dict[str, list[int]]] = {}
    for row in scores:
        if row.get("parse_source") == "unparseable" or row.get("score") is None:
            continue
        aid = str(row.get("agent_id") or "")
        cat = str(row.get("category") or "")
        if not aid or not cat:
            continue
        by_agent.setdefault(aid, {}).setdefault(cat, []).append(int(row["score"]))

    agent_category_means: dict[str, dict[str, float]] = {}
    for aid, cats in by_agent.items():
        agent_category_means[aid] = {
            cat: round(sum(vals) / len(vals), 6) for cat, vals in cats.items() if vals
        }

    interview_category_stdev: dict[str, float | None] = {}
    all_cats = {cat for cats in agent_category_means.values() for cat in cats}
    for cat in sorted(all_cats):
        vals = [agent_category_means[aid][cat] for aid in agent_category_means if cat in agent_category_means[aid]]
        interview_category_stdev[cat] = (
            round(statistics.pstdev(vals), 6) if len(vals) >= 2 else None
        )

    return {
        "final_round_support_stdev": support_stdev,
        "final_round_support_levels": final_support,
        "interview_category_stdev_across_agents": interview_category_stdev,
        "interview_agent_category_means": agent_category_means,
    }


def extract_cost_metrics(export_bundle: dict[str, Any], *, wall_clock_seconds: float) -> dict[str, Any]:
    run = export_bundle.get("run") or {}
    cfg = run.get("config_snapshot") or {}
    econ = run.get("economics") or {}
    return {
        "wall_clock_seconds": round(wall_clock_seconds, 3),
        "total_input_tokens": run.get("total_input_tokens"),
        "total_output_tokens": run.get("total_output_tokens"),
        "estimated_cost_usd": econ.get("estimated_cost_usd"),
        "importance_scoring_token_totals": cfg.get("importance_scoring_token_totals"),
        "reflection_token_totals": cfg.get("reflection_token_totals"),
        "weighted_retrieval_embed_api_calls": cfg.get("weighted_retrieval_embed_api_calls"),
    }


def compute_deltas_vs_baseline(
    metrics: dict[str, Any],
    baseline_metrics: dict[str, Any],
) -> dict[str, Any]:
    """Diagnostic deltas vs measured Arc 10 real-run baseline summary."""

    def _delta(a: float | None, b: float | None) -> float | None:
        if a is None or b is None:
            return None
        return round(float(a) - float(b), 6)

    base_cats = baseline_metrics.get("interview_category_means") or {}
    run_cats = metrics.get("interview_category_means") or {}
    cat_deltas = {
        cat: _delta(run_cats.get(cat), base_cats.get(cat))
        for cat in sorted(set(base_cats) | set(run_cats))
    }

    base_exc = baseline_metrics.get("memory_exclusion_breakdown") or {}
    run_exc = metrics.get("memory_exclusion_breakdown") or {}
    exc_deltas = {
        k: int(run_exc.get(k) or 0) - int(base_exc.get(k) or 0)
        for k in sorted(set(base_exc) | set(run_exc))
    }

    return {
        "membench_factual_mean": _delta(
            metrics.get("membench_factual_mean"),
            baseline_metrics.get("membench_factual_mean"),
        ),
        "membench_reflective_mean": _delta(
            metrics.get("membench_reflective_mean"),
            baseline_metrics.get("membench_reflective_mean"),
        ),
        "interview_category_means": cat_deltas,
        "memory_group_addressed_proportion": _delta(
            metrics.get("memory_group_addressed_proportion"),
            baseline_metrics.get("memory_group_addressed_proportion"),
        ),
        "memory_exclusion_breakdown": exc_deltas,
    }


def load_measured_baseline_summary(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if "metrics" not in data:
        raise ValueError(f"baseline fixture missing 'metrics': {path}")
    return data


def aggregate_condition_results(records: list[AblationRunRecord]) -> dict[str, Any]:
    """Aggregate runs by condition (mean ± spread across seeds)."""
    by_condition: dict[str, list[AblationRunRecord]] = {}
    for rec in records:
        by_condition.setdefault(rec.condition, []).append(rec)

    def _agg_float(values: list[float | None]) -> dict[str, Any]:
        clean = [float(v) for v in values if v is not None]
        if not clean:
            return {"mean": None, "min": None, "max": None, "stdev": None, "n": 0}
        return {
            "mean": round(statistics.mean(clean), 6),
            "min": round(min(clean), 6),
            "max": round(max(clean), 6),
            "stdev": round(statistics.pstdev(clean), 6) if len(clean) >= 2 else 0.0,
            "n": len(clean),
        }

    out: dict[str, Any] = {}
    for condition, rows in sorted(by_condition.items()):
        costs_in = [r.cost.get("total_input_tokens") for r in rows]
        costs_out = [r.cost.get("total_output_tokens") for r in rows]
        costs_usd = [r.cost.get("estimated_cost_usd") for r in rows]
        wall = [r.cost.get("wall_clock_seconds") for r in rows]
        support_stdev = [r.dispersion.get("final_round_support_stdev") for r in rows]
        mb_fact_delta = [r.deltas_vs_baseline.get("membench_factual_mean") for r in rows]
        mb_refl_delta = [r.deltas_vs_baseline.get("membench_reflective_mean") for r in rows]
        refl_iv_delta = [
            (r.deltas_vs_baseline.get("interview_category_means") or {}).get("reflection")
            for r in rows
        ]
        out[condition] = {
            "run_count": len(rows),
            "seeds": sorted({r.seed for r in rows}),
            "cost": {
                "total_input_tokens": _agg_float(costs_in),
                "total_output_tokens": _agg_float(costs_out),
                "estimated_cost_usd": _agg_float(costs_usd),
                "wall_clock_seconds": _agg_float(wall),
            },
            "dispersion": {
                "final_round_support_stdev": _agg_float(support_stdev),
            },
            "diagnostic_deltas_vs_measured_baseline": {
                "membench_factual_mean": _agg_float(mb_fact_delta),
                "membench_reflective_mean": _agg_float(mb_refl_delta),
                "interview_reflection_mean": _agg_float(refl_iv_delta),
            },
            "runs": [
                {
                    "seed": r.seed,
                    "simulation_id": r.simulation_id,
                    "wall_clock_seconds": r.cost.get("wall_clock_seconds"),
                    "metrics": r.metrics,
                    "deltas_vs_baseline": r.deltas_vs_baseline,
                    "dispersion": r.dispersion,
                    "cost": r.cost,
                }
                for r in sorted(rows, key=lambda x: x.seed)
            ],
        }
    return out


def build_ablation_results_payload(
    *,
    profile: AblationRunProfile,
    seeds: list[int],
    conditions: list[str],
    records: list[AblationRunRecord],
    baseline_ref: dict[str, Any],
    command: str,
) -> dict[str, Any]:
    return {
        "arc": "11",
        "harness": "senna-iter-52",
        "command": command,
        "run_profile": {
            "scenario_id": profile.scenario_id,
            "agent_limit": profile.agent_limit,
            "total_rounds": profile.total_rounds,
            "visibility_policy": profile.visibility_policy,
            "sampling_strategy": profile.sampling_strategy,
        },
        "seeds": seeds,
        "conditions": conditions,
        "baseline_reference": {
            "source": baseline_ref.get("source"),
            "simulation_id": baseline_ref.get("simulation_id"),
            "metrics": baseline_ref.get("metrics"),
        },
        "runs": [
            {
                "condition": r.condition,
                "seed": r.seed,
                "simulation_id": r.simulation_id,
                "wall_clock_seconds": r.cost.get("wall_clock_seconds"),
                "metrics": r.metrics,
                "deltas_vs_baseline": r.deltas_vs_baseline,
                "dispersion": r.dispersion,
                "cost": r.cost,
            }
            for r in records
        ],
        "aggregated_by_condition": aggregate_condition_results(records),
    }


def generate_ablation_markdown(payload: dict[str, Any]) -> str:
    profile = payload.get("run_profile") or {}
    baseline = payload.get("baseline_reference") or {}
    agg = payload.get("aggregated_by_condition") or {}
    lines = [
        "# Arc 11 memory ablation results",
        "",
        f"**Harness:** senna-iter-52",
        f"**Command:** `{payload.get('command', '')}`",
        "",
        "## Run profile",
        "",
        f"- Scenario: `{profile.get('scenario_id')}`",
        f"- Agents: {profile.get('agent_limit')}",
        f"- Rounds: {profile.get('total_rounds')}",
        f"- Visibility: `{profile.get('visibility_policy')}` (+ network CSV)",
        f"- Seeds: {payload.get('seeds')}",
        "",
        "## Baseline reference",
        "",
        f"- Source: `{baseline.get('source')}`",
        f"- Simulation ID: `{baseline.get('simulation_id')}`",
        "",
        "## Per-condition summary (aggregate across seeds)",
        "",
        "| Condition | Δ factual | Δ reflective | Δ reflection (interview) | Input tokens (mean) | Cost USD (mean) | Wall s (mean) | Support stdev (mean) |",
        "|-----------|-----------|--------------|------------------------|---------------------|-----------------|---------------|----------------------|",
    ]
    for condition in payload.get("conditions") or sorted(agg.keys()):
        block = agg.get(condition) or {}
        dd = block.get("diagnostic_deltas_vs_measured_baseline") or {}
        cost = block.get("cost") or {}
        disp = block.get("dispersion") or {}

        def _fmt(agg_dict: dict[str, Any] | None) -> str:
            if not agg_dict or agg_dict.get("mean") is None:
                return "—"
            m = agg_dict["mean"]
            spread = agg_dict.get("stdev")
            if spread is not None and spread != 0:
                return f"{m} ± {spread}"
            return str(m)

        lines.append(
            "| "
            + " | ".join(
                [
                    condition,
                    _fmt(dd.get("membench_factual_mean")),
                    _fmt(dd.get("membench_reflective_mean")),
                    _fmt(dd.get("interview_reflection_mean")),
                    _fmt(cost.get("total_input_tokens")),
                    _fmt(cost.get("estimated_cost_usd")),
                    _fmt(cost.get("wall_clock_seconds")),
                    _fmt(disp.get("final_round_support_stdev")),
                ]
            )
            + " |"
        )
    lines.extend(
        [
            "",
            "Deltas are vs [`ARC10_MEASURED_BASELINE_REAL_RUN.md`](./ARC10_MEASURED_BASELINE_REAL_RUN.md) diagnostic summary.",
            "",
            "*MemBench is run-level accuracy; between-agent dispersion uses final-round support stdev and per-category interview stdev across agents.*",
            "",
        ]
    )
    return "\n".join(lines)


async def run_ablation_simulation(
    *,
    sqlite_path: str,
    condition: str,
    seed: int,
    profile: AblationRunProfile | None = None,
    config_snapshot: dict[str, Any] | None = None,
) -> str:
    """
    Run one ablation cell via ``run_simulation_task`` (integration-test path).

    Returns ``simulation_id`` after the run completes.
    """
    from mirofish_backend.db.repo import create_simulation_run
    from mirofish_backend.scenarios.registry import get_scenario as load_scenario
    from mirofish_backend.simulation import orchestrator
    from mirofish_backend.simulation.network import parse_network_csv, undirected_neighbor_map
    from mirofish_backend.roster.csv_roster import personas_for_run as build_personas_for_agent_limit

    prof = profile or AblationRunProfile()
    flags = condition_memory_flags(condition)
    scenario = load_scenario(prof.scenario_id)
    personas = build_personas_for_agent_limit(scenario, prof.agent_limit, None)
    agent_ids = [f"{p.persona_id}_{i:03d}" for i, p in enumerate(personas)]
    known = frozenset(agent_ids)
    network_csv = build_network_csv_for_scenario(
        scenario_id=prof.scenario_id,
        agent_limit=prof.agent_limit,
    )
    net_parse = parse_network_csv(network_csv, known_agent_ids=known)
    neighbors_map = undirected_neighbor_map(known, net_parse.edges)

    snap = dict(config_snapshot or {})
    snap.update(
        {
            "ablation_condition": condition,
            "ablation_seed": seed,
            **flags,
        }
    )
    sim_id = await create_simulation_run(
        sqlite_path,
        name=f"arc11-{condition}-s{seed}",
        scenario_id=prof.scenario_id,
        status="pending",
        total_rounds=prof.total_rounds,
        random_seed=seed,
        prompt_version="v0",
        model_used="lmstudio:local",
        config_snapshot=snap,
    )

    rag_effective = bool(scenario.rag_enabled)
    await orchestrator.run_simulation_task(
        sqlite_path=sqlite_path,
        simulation_id=sim_id,
        scenario_id=prof.scenario_id,
        total_rounds=prof.total_rounds,
        agent_limit=prof.agent_limit,
        random_seed=seed,
        prompt_version="v0",
        model_used="lmstudio:local",
        lmstudio_model="local-test",
        lmstudio_base_url="http://127.0.0.1:9",
        llm_temperature=0.0,
        llm_max_tokens=256,
        working_memory_last_k=2,
        llm_provider="lmstudio",
        anthropic_api_key="",
        anthropic_model="unused",
        peer_context_max_chars=800,
        rag_effective=rag_effective,
        embedding_model="test-embed",
        rag_top_k=2,
        rag_chunk_size=200,
        rag_chunk_overlap=40,
        rag_max_inject_chars=800,
        personas_for_run=personas,
        scenario_config=scenario,
        simulation_mode="full_round_robin",
        visibility_policy=prof.visibility_policy,
        visibility_effective="network_bounded",
        network_neighbors=neighbors_map,
        fidelity_tiers=[1] * prof.agent_limit,
        llm_concurrency_cap=1,
        importance_scoring_enabled=flags["importance_scoring_enabled"],
        weighted_retrieval_enabled=flags["weighted_retrieval_enabled"],
        reflection_enabled=flags["reflection_enabled"],
        reflection_trigger_threshold=150,
    )
    return sim_id


async def execute_ablation_cell(
    *,
    sqlite_path: str,
    condition: str,
    seed: int,
    profile: AblationRunProfile,
    fixtures_dir: Path,
    baseline_metrics: dict[str, Any],
    run_arc10_diagnostics,
    execute_interview: bool = True,
    wall_clock_seconds: float | None = None,
) -> AblationRunRecord:
    """Run simulation + Arc 10 diagnostics and return structured ablation record."""
    import time

    from mirofish_backend.db.repo import get_simulation_export_bundle

    t0 = time.perf_counter()
    sim_id = await run_ablation_simulation(
        sqlite_path=sqlite_path,
        condition=condition,
        seed=seed,
        profile=profile,
    )
    elapsed = wall_clock_seconds if wall_clock_seconds is not None else time.perf_counter() - t0

    diag = await run_arc10_diagnostics(
        sqlite_path=sqlite_path,
        simulation_id=sim_id,
        fixtures_dir=fixtures_dir,
        membench_seed=seed,
        membench_answer_mode="memory_match",
        execute_interview=execute_interview,
        interview_profile_id="local_lmstudio_default",
        judge_profile_id="local_lmstudio_default",
        force_interview=False,
        interview_temperature=0.0,
        interview_max_tokens=256,
    )
    bundle = await get_simulation_export_bundle(sqlite_path, simulation_id=sim_id)
    if bundle is None:
        raise RuntimeError(f"export bundle missing for {sim_id}")
    metrics = extract_normalized_metrics(diag)
    dispersion = compute_dispersion_metrics(export_bundle=bundle, diagnostics_summary=diag)
    cost = extract_cost_metrics(bundle, wall_clock_seconds=elapsed)
    deltas = compute_deltas_vs_baseline(metrics, baseline_metrics)
    return AblationRunRecord(
        condition=condition,
        seed=seed,
        simulation_id=sim_id,
        wall_clock_seconds=elapsed,
        diagnostics=diag,
        cost=cost,
        dispersion=dispersion,
        metrics=metrics,
        deltas_vs_baseline=deltas,
    )

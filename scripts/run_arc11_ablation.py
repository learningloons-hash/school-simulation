#!/usr/bin/env python3
"""Arc 11 memory-mechanism ablation sweep (senna-iter-52)."""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
import time
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_REPO_ROOT / "backend" / "src"))
sys.path.insert(0, str(_REPO_ROOT / "scripts"))

from run_arc10_diagnostics import run_arc10_diagnostics

from mirofish_backend.api.simulations import (
    SimulationRunRequest,
    queue_simulation_run,
    wait_for_simulation_terminal,
)
from mirofish_backend.config import get_settings
from mirofish_backend.db.repo import get_simulation_export_bundle
from mirofish_backend.db.schema import init_db as schema_init
from mirofish_backend.diagnostics.arc11_ablation import (
    ABLATION_CONDITIONS,
    DEFAULT_ABLATION_SEEDS,
    AblationRunProfile,
    AblationRunRecord,
    build_ablation_results_payload,
    build_network_csv_for_scenario,
    compute_deltas_vs_baseline,
    compute_dispersion_metrics,
    condition_memory_flags,
    extract_cost_metrics,
    extract_normalized_metrics,
    generate_ablation_markdown,
    load_measured_baseline_summary,
)
from mirofish_backend.llm.model_profiles import LOCAL_LMSTUDIO_DEFAULT_ID

_DEFAULT_FIXTURES = _REPO_ROOT / "backend/tests/fixtures/membench"
_DEFAULT_BASELINE = _REPO_ROOT / "backend/tests/fixtures/arc11/measured_baseline_summary.json"
_DEFAULT_JSON_OUT = _REPO_ROOT / "docs/diagnostics/arc11_ablation_results.json"
_DEFAULT_MD_OUT = _REPO_ROOT / "docs/diagnostics/ARC11_ABLATION_RESULTS.md"


def build_simulation_request(
    *,
    condition: str,
    seed: int,
    profile: AblationRunProfile,
    network_csv: str,
) -> SimulationRunRequest:
    flags = condition_memory_flags(condition)
    return SimulationRunRequest(
        scenario_id=profile.scenario_id,
        agent_limit=profile.agent_limit,
        total_rounds=profile.total_rounds,
        random_seed=seed,
        visibility_policy=profile.visibility_policy,
        sampling_strategy=profile.sampling_strategy,
        network_csv=network_csv,
        importance_scoring_enabled=flags["importance_scoring_enabled"] or None,
        weighted_retrieval_enabled=flags["weighted_retrieval_enabled"] or None,
        reflection_enabled=flags["reflection_enabled"] or None,
        reflection_trigger_threshold=(
            profile.reflection_trigger_threshold if flags["reflection_enabled"] else None
        ),
    )


async def run_ablation_via_api(
    *,
    settings,
    condition: str,
    seed: int,
    profile: AblationRunProfile,
    network_csv: str,
    fixtures_dir: Path,
    baseline_metrics: dict,
    execute_interview: bool,
) -> AblationRunRecord:
    req = build_simulation_request(
        condition=condition,
        seed=seed,
        profile=profile,
        network_csv=network_csv,
    )
    t0 = time.perf_counter()
    resp = await queue_simulation_run(
        settings,
        req,
        run_display_name=f"arc11-{condition}-s{seed}",
    )
    await wait_for_simulation_terminal(
        sqlite_path=settings.sqlite_path,
        simulation_id=resp.id,
        poll_interval=0.5,
        timeout_seconds=3600.0,
    )
    elapsed = time.perf_counter() - t0
    diag = await run_arc10_diagnostics(
        sqlite_path=settings.sqlite_path,
        simulation_id=resp.id,
        fixtures_dir=fixtures_dir,
        membench_seed=seed,
        membench_answer_mode="memory_match",
        execute_interview=execute_interview,
        interview_profile_id=LOCAL_LMSTUDIO_DEFAULT_ID,
        judge_profile_id=LOCAL_LMSTUDIO_DEFAULT_ID,
        force_interview=False,
        interview_temperature=0.2,
        interview_max_tokens=1024,
    )
    bundle = await get_simulation_export_bundle(settings.sqlite_path, simulation_id=resp.id)
    if bundle is None:
        raise RuntimeError(f"missing export bundle for {resp.id}")
    metrics = extract_normalized_metrics(diag)
    dispersion = compute_dispersion_metrics(export_bundle=bundle, diagnostics_summary=diag)
    cost = extract_cost_metrics(bundle, wall_clock_seconds=elapsed)
    deltas = compute_deltas_vs_baseline(metrics, baseline_metrics)
    return AblationRunRecord(
        condition=condition,
        seed=seed,
        simulation_id=resp.id,
        wall_clock_seconds=elapsed,
        diagnostics=diag,
        cost=cost,
        dispersion=dispersion,
        metrics=metrics,
        deltas_vs_baseline=deltas,
    )


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Arc 11 memory ablation harness (senna-iter-52)")
    p.add_argument(
        "--conditions",
        nargs="+",
        default=list(ABLATION_CONDITIONS),
        help="Subset of ablation conditions",
    )
    p.add_argument(
        "--seeds",
        nargs="+",
        type=int,
        default=list(DEFAULT_ABLATION_SEEDS),
        help="Random seeds (default: 42 43 44)",
    )
    p.add_argument("--sqlite-path", default="", help="SQLite path (default: settings)")
    p.add_argument("--fixtures-dir", type=Path, default=_DEFAULT_FIXTURES)
    p.add_argument("--baseline-json", type=Path, default=_DEFAULT_BASELINE)
    p.add_argument("--json-out", type=Path, default=_DEFAULT_JSON_OUT)
    p.add_argument("--markdown-out", type=Path, default=_DEFAULT_MD_OUT)
    p.add_argument(
        "--skip-interview",
        action="store_true",
        help="Skip live architectural interview (not recommended for ablation)",
    )
    p.add_argument("--rounds", type=int, default=5, help="Total rounds (default 5)")
    p.add_argument(
        "--reflection-threshold",
        type=int,
        default=35,
        help="reflection_trigger_threshold when reflection arm is on (default 35 for 5-round profile)",
    )
    return p


async def _main_async(args: argparse.Namespace) -> dict:
    settings = get_settings()
    sqlite_path = args.sqlite_path or settings.sqlite_path
    await schema_init(sqlite_path)
    profile = AblationRunProfile(
        total_rounds=args.rounds,
        reflection_trigger_threshold=args.reflection_threshold,
    )
    network_csv = build_network_csv_for_scenario(
        scenario_id=profile.scenario_id,
        agent_limit=profile.agent_limit,
    )
    baseline_ref = load_measured_baseline_summary(args.baseline_json.resolve())
    baseline_metrics = baseline_ref["metrics"]
    command = " ".join(sys.argv)

    records: list[AblationRunRecord] = []
    for condition in args.conditions:
        for seed in args.seeds:
            rec = await run_ablation_via_api(
                settings=settings,
                condition=condition,
                seed=seed,
                profile=profile,
                network_csv=network_csv,
                fixtures_dir=args.fixtures_dir.resolve(),
                baseline_metrics=baseline_metrics,
                execute_interview=not args.skip_interview,
            )
            records.append(rec)
            print(
                json.dumps(
                    {
                        "condition": condition,
                        "seed": seed,
                        "simulation_id": rec.simulation_id,
                        "wall_clock_seconds": rec.cost.get("wall_clock_seconds"),
                    }
                ),
                flush=True,
            )

    payload = build_ablation_results_payload(
        profile=profile,
        seeds=list(args.seeds),
        conditions=list(args.conditions),
        records=records,
        baseline_ref=baseline_ref,
        command=command,
    )
    args.json_out.parent.mkdir(parents=True, exist_ok=True)
    args.json_out.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    md = generate_ablation_markdown(payload)
    args.markdown_out.write_text(md, encoding="utf-8")
    payload["artifacts"] = {
        "json": str(args.json_out),
        "markdown": str(args.markdown_out),
    }
    return payload


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        payload = asyncio.run(_main_async(args))
    except (ValueError, RuntimeError) as exc:
        print(json.dumps({"error": str(exc)}), file=sys.stderr)
        return 1
    print(json.dumps({"status": "ok", "run_count": len(payload.get("runs") or [])}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

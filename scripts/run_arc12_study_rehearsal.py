#!/usr/bin/env python3
"""Arc 12 study-scale rehearsal harness (senna-iter-55).

Loads the CIEPSS documented network CSV from the study repo, queues simulations
via the normal API path, and records mechanics-only metrics. Part A: harness +
CI tests only. Live Anthropic RQ1/RQ2 runs are Part B (Mark/CLI).

**Interim config:** GM-F formal ruling pending — uses iter-53 frozen mechanism
defaults (all memory flags off) until ruled otherwise.
"""

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

from run_arc11_ablation import load_dotenv_if_present, print_config_banner  # noqa: E402

from mirofish_backend.api.simulations import (  # noqa: E402
    SimulationRunRequest,
    queue_simulation_run,
    wait_for_simulation_terminal,
)
from mirofish_backend.config import get_settings  # noqa: E402
from mirofish_backend.db.repo import get_simulation_export_bundle, user_scenario_exists  # noqa: E402
from mirofish_backend.db.schema import init_db as schema_init  # noqa: E402
from mirofish_backend.diagnostics.arc12_study_rehearsal import (  # noqa: E402
    DEFAULT_AGENT_LIMIT,
    DEFAULT_NETWORK_CSV_REL,
    DEFAULT_RQ1_ROUND_COUNTS,
    DEFAULT_SCENARIO_ID,
    DEFAULT_STUDY_SEEDS,
    INTERIM_MECHANISM_FLAGS,
    StudyRehearsalProfile,
    StudyRehearsalRunRecord,
    build_results_payload,
    build_rq1_run_plan,
    build_expected_run_agent_ids,
    extract_mechanics_metrics,
    generate_rehearsal_markdown,
    load_documented_network_csv,
)
from mirofish_backend.scenarios.loader import load_scenario_for_run  # noqa: E402

_DEFAULT_JSON_OUT = _REPO_ROOT / "docs/diagnostics/arc12_study_rehearsal_results.json"
_DEFAULT_MD_OUT = _REPO_ROOT / "docs/diagnostics/ARC12_STUDY_REHEARSAL_RESULTS.md"
_DEFAULT_ENV_FILE = _REPO_ROOT / "backend" / ".env"
_RQ2_DEFER_NOTE = (
    "RQ2 (~20 documented actors + synthetic remainder) deferred — no platform scenario "
    "fixture today; pending Lee (2020) case per ARC12 §7. Re-run without --skip-rq2 when "
    "study-repo fixture and scenario exist."
)


def check_transcript_qa(bundle: dict, *, simulation_id: str, label: str, seed: int) -> None:
    from mirofish_backend.diagnostics.arc12_study_rehearsal import (
        count_context_length_failures,
        count_llm_errors,
    )

    transcript = bundle.get("transcript") or []
    llm_err = count_llm_errors(transcript)
    if llm_err:
        raise RuntimeError(
            f"[rehearsal] {llm_err} LLM error turns in {simulation_id} "
            f"(label={label!r}, seed={seed}) — run not usable."
        )
    ctx_err = count_context_length_failures(transcript)
    if ctx_err:
        raise RuntimeError(
            f"[rehearsal] {ctx_err} context-length failures in {simulation_id} "
            f"(label={label!r}, seed={seed}) — run not usable."
        )


def build_simulation_request(
    *,
    profile: StudyRehearsalProfile,
    rounds: int,
    seed: int,
    network_csv: str,
    llm_provider: str | None,
    model_profile_id: str | None,
    rag_enabled: bool | None,
) -> SimulationRunRequest:
    return SimulationRunRequest(
        scenario_id=profile.scenario_id,
        agent_limit=profile.agent_limit,
        total_rounds=rounds,
        random_seed=seed,
        visibility_policy=profile.visibility_policy,
        sampling_strategy=profile.sampling_strategy,
        network_csv=network_csv,
        llm_provider=llm_provider,
        model_profile_id=model_profile_id,
        rag_enabled=rag_enabled,
        importance_scoring_enabled=INTERIM_MECHANISM_FLAGS["importance_scoring_enabled"] or None,
        weighted_retrieval_enabled=INTERIM_MECHANISM_FLAGS["weighted_retrieval_enabled"] or None,
        reflection_enabled=INTERIM_MECHANISM_FLAGS["reflection_enabled"] or None,
    )


async def run_rehearsal_via_api(
    *,
    settings,
    profile: StudyRehearsalProfile,
    label: str,
    rounds: int,
    seed: int,
    network_csv: str,
    llm_provider: str | None = None,
    model_profile_id: str | None = None,
    rag_enabled: bool | None = None,
) -> StudyRehearsalRunRecord:
    req = build_simulation_request(
        profile=profile,
        rounds=rounds,
        seed=seed,
        network_csv=network_csv,
        llm_provider=llm_provider,
        model_profile_id=model_profile_id,
        rag_enabled=rag_enabled,
    )
    t0 = time.perf_counter()
    resp = await queue_simulation_run(
        settings,
        req,
        run_display_name=f"arc12-{label}-s{seed}",
    )
    terminal = await wait_for_simulation_terminal(
        sqlite_path=settings.sqlite_path,
        simulation_id=resp.id,
        poll_interval=0.5,
        timeout_seconds=7200.0,
    )
    elapsed = time.perf_counter() - t0
    status = str(terminal.get("status") or "unknown")
    bundle = await get_simulation_export_bundle(settings.sqlite_path, simulation_id=resp.id)
    if bundle is None:
        raise RuntimeError(f"missing export bundle for {resp.id}")
    check_transcript_qa(bundle, simulation_id=resp.id, label=label, seed=seed)
    mechanics = extract_mechanics_metrics(bundle=bundle, wall_clock_seconds=elapsed)
    return StudyRehearsalRunRecord(
        label=label,
        rounds=rounds,
        seed=seed,
        simulation_id=resp.id,
        status=status,
        mechanics=mechanics,
    )


def print_interim_flags_banner() -> None:
    print("[rehearsal] interim mechanism flags (GM-F ruling pending):", flush=True)
    for k, v in INTERIM_MECHANISM_FLAGS.items():
        print(f"  {k} = {v}", flush=True)
    print("  (iter-53 frozen defaults until GM-F rules otherwise)", flush=True)


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Arc 12 study-scale rehearsal harness (senna-iter-55)")
    p.add_argument("--seeds", type=int, nargs="+", default=list(DEFAULT_STUDY_SEEDS))
    p.add_argument(
        "--rounds",
        type=int,
        nargs="+",
        default=list(DEFAULT_RQ1_ROUND_COUNTS),
        help="Round counts for RQ1 matrix (default: 15 20)",
    )
    p.add_argument("--scenario-id", default=DEFAULT_SCENARIO_ID)
    p.add_argument("--agent-limit", type=int, default=DEFAULT_AGENT_LIMIT)
    p.add_argument("--study-repo-path", default="", help="Path to senna-sstrf-study checkout")
    p.add_argument(
        "--network-csv-rel-path",
        default=DEFAULT_NETWORK_CSV_REL,
        help="Network CSV path relative to study repo",
    )
    p.add_argument("--network-csv-text", default="", help="Inline network CSV (tests/local override)")
    p.add_argument("--sqlite-path", default="", help="SQLite path (default: settings)")
    p.add_argument("--json-out", type=Path, default=_DEFAULT_JSON_OUT)
    p.add_argument("--markdown-out", type=Path, default=_DEFAULT_MD_OUT)
    p.add_argument("--llm-provider", default="anthropic", choices=["lmstudio", "anthropic", "hybrid"])
    p.add_argument("--model-profile-id", default="")
    p.add_argument("--no-rag", action="store_true", help="Force rag_enabled=False on simulation")
    p.add_argument("--skip-rq2", action="store_true", help="Skip RQ2 (default until fixture exists)")
    p.add_argument("--dry-run", action="store_true", help="Validate config and exit without queuing runs")
    p.add_argument("--env-file", type=Path, default=_DEFAULT_ENV_FILE)
    return p


async def _main_async(args: argparse.Namespace) -> dict:
    settings = get_settings()
    sqlite_path = args.sqlite_path or settings.sqlite_path
    await schema_init(sqlite_path)

    profile = StudyRehearsalProfile(
        scenario_id=args.scenario_id,
        agent_limit=args.agent_limit,
    )

    if not await user_scenario_exists(sqlite_path, scenario_id=profile.scenario_id):
        raise RuntimeError(
            f"scenario {profile.scenario_id!r} not in user_scenarios — seed first via "
            "scripts/seed_scenario_from_study_repo.py (see docs/SETUP_STUDY_FIXTURES.md)."
        )

    scenario_cfg, _src = await load_scenario_for_run(sqlite_path, profile.scenario_id)
    persona_ids = [p.persona_id for p in scenario_cfg.personas[: profile.agent_limit]]
    if len(persona_ids) < profile.agent_limit:
        raise RuntimeError(
            f"scenario {profile.scenario_id!r} has {len(scenario_cfg.personas)} personas; "
            f"need {profile.agent_limit} for study rehearsal.",
        )
    expected_ids = frozenset(build_expected_run_agent_ids(persona_ids=persona_ids))

    if args.network_csv_text.strip():
        network_csv = args.network_csv_text.strip()
        if not network_csv.endswith("\n"):
            network_csv += "\n"
        from mirofish_backend.simulation.network import parse_network_csv

        net_parse = parse_network_csv(network_csv, known_agent_ids=expected_ids)
        if not net_parse.edges:
            raise ValueError("inline network_csv produced no valid edges")
    else:
        if not args.study_repo_path:
            raise RuntimeError("--study-repo-path required unless --network-csv-text is provided")
        network_csv, net_parse = load_documented_network_csv(
            study_repo_path=Path(args.study_repo_path),
            rel_path=args.network_csv_rel_path,
            expected_agent_ids=expected_ids,
        )
    print(f"[rehearsal] network CSV: {len(net_parse.edges)} edges for {len(expected_ids)} agents", flush=True)
    if net_parse.warnings:
        for w in net_parse.warnings:
            print(f"[rehearsal] network warning: {w}", flush=True)

    print_interim_flags_banner()
    print_config_banner(settings)

    rq2_skipped = bool(args.skip_rq2)
    rq2_note = _RQ2_DEFER_NOTE if rq2_skipped else None

    plan = build_rq1_run_plan(round_counts=list(args.rounds), seeds=list(args.seeds))
    print(f"[rehearsal] RQ1 plan: {len(plan)} runs — {plan}", flush=True)
    if rq2_skipped:
        print(f"[rehearsal] RQ2 skipped: {rq2_note}", flush=True)

    if args.dry_run:
        return {
            "status": "dry_run",
            "planned_runs": len(plan),
            "rq2_skipped": rq2_skipped,
        }

    records: list[StudyRehearsalRunRecord] = []
    model_profile_id = args.model_profile_id.strip() or None
    rag_enabled = False if args.no_rag else None
    for label, rounds, seed in plan:
        rec = await run_rehearsal_via_api(
            settings=settings,
            profile=profile,
            label=label,
            rounds=rounds,
            seed=seed,
            network_csv=network_csv,
            llm_provider=args.llm_provider,
            model_profile_id=model_profile_id,
            rag_enabled=rag_enabled,
        )
        records.append(rec)
        print(
            json.dumps(
                {
                    "label": label,
                    "seed": seed,
                    "rounds": rounds,
                    "simulation_id": rec.simulation_id,
                    "status": rec.status,
                    "wall_clock_seconds": rec.mechanics.get("wall_clock_seconds"),
                }
            ),
            flush=True,
        )

    payload = build_results_payload(
        profile=profile,
        records=records,
        command=" ".join(sys.argv),
        interim_flags=dict(INTERIM_MECHANISM_FLAGS),
        rq2_skipped=rq2_skipped,
        rq2_note=rq2_note,
        network_csv_rel_path=args.network_csv_rel_path,
    )
    args.json_out.parent.mkdir(parents=True, exist_ok=True)
    args.json_out.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    args.markdown_out.write_text(generate_rehearsal_markdown(payload), encoding="utf-8")
    payload["artifacts"] = {"json": str(args.json_out), "markdown": str(args.markdown_out)}
    return payload


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    load_dotenv_if_present(args.env_file)
    try:
        payload = asyncio.run(_main_async(args))
    except (ValueError, RuntimeError, FileNotFoundError) as exc:
        print(f"\n{exc}\n", file=sys.stderr)
        print(json.dumps({"error": str(exc)}), file=sys.stderr)
        return 1
    print(json.dumps({"status": "ok", "run_count": len(payload.get("runs") or [])}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

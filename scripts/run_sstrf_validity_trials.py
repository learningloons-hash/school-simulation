#!/usr/bin/env python3
"""SSTRF RQ1 validity-trial simulation harness (sstrf-validity-v2 Part A).

Ten frozen-config runs (seeds 500–509) under signed pre-reg
``docs/research/PREREG_SSTRF_RQ1_V2.md``. Part A: harness + CI only — no live
Anthropic spend unless ``--execute`` is passed.

**Pre-flight (live runs):**
- Platform freeze must be signed (``ARC12_PLATFORM_FREEZE.json``).
- Fixture provenance must match freeze binding.
- Scenario ``ciepss_school_b`` must be seeded from the study repo.
- Study-repo checkout @ fixture commit for documented network CSV.

**ANTHROPIC_API_KEY pitfall:** if your shell exports an empty or stale
``ANTHROPIC_API_KEY``, it shadows ``backend/.env`` and live runs fail with 401
even when the key in ``.env`` is valid. Before ``--execute``:

    unset ANTHROPIC_API_KEY
    # or confirm: echo "[$ANTHROPIC_API_KEY]"  — [] means empty export is the culprit

Then rely on ``backend/.env`` (loaded by this script) or export a fresh key.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
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
from mirofish_backend.diagnostics.sstrf_validity_v2 import (  # noqa: E402
    DEFAULT_NETWORK_CSV_REL,
    FROZEN_MECHANISM_FLAGS,
    ValidityTrialProfile,
    ValidityTrialRecord,
    assert_fixture_provenance_matches,
    assert_freeze_signed,
    build_expected_run_agent_ids,
    build_manifest_payload,
    build_planned_trial_records,
    build_validity_run_plan,
    check_transcript_qa,
    default_freeze_path,
    default_manifest_path,
    default_provenance_path,
    default_seeds_path,
    extract_economics_summary,
    load_documented_network_csv,
    load_fixture_provenance,
    load_platform_freeze,
    load_study_seeds,
    profile_snapshot,
    resolve_validity_manifest_write_path,
    write_manifest,
)
from mirofish_backend.llm.model_profiles import ANTHROPIC_DEFAULT_ID  # noqa: E402
from mirofish_backend.scenarios.loader import load_scenario_for_run  # noqa: E402

_DEFAULT_ENV_FILE = _REPO_ROOT / "backend" / ".env"
_PREREG_PATH = "docs/research/PREREG_SSTRF_RQ1_V2.md"


def print_validity_banner(*, profile: ValidityTrialProfile, trial_count: int) -> None:
    print("[validity] SSTRF RQ1 validity trials — frozen study profile", flush=True)
    print(f"  pre-reg: {_PREREG_PATH}", flush=True)
    print(f"  scenario_id = {profile.scenario_id}", flush=True)
    print(f"  agent_limit = {profile.agent_limit}", flush=True)
    print(f"  total_rounds = {profile.total_rounds}", flush=True)
    print(f"  model_profile = {profile.model_profile_id} ({profile.model_id})", flush=True)
    print(f"  visibility_policy = {profile.visibility_policy}", flush=True)
    print(f"  sampling_strategy = {profile.sampling_strategy}", flush=True)
    print(f"  turn_order_policy = {profile.turn_order_policy}", flush=True)
    print(f"  network_csv = study repo {profile.network_csv_rel_path}", flush=True)
    print(f"  planned trials = {trial_count}", flush=True)
    print("[validity] mechanism flags (all off per pre-reg §4):", flush=True)
    for key, value in FROZEN_MECHANISM_FLAGS.items():
        print(f"  {key} = {value}", flush=True)
    print("  convergence_threshold = null (full 20 rounds)", flush=True)
    print("  rag_enabled = false", flush=True)


def print_anthropic_key_pitfall_if_relevant(*, execute: bool, llm_provider: str) -> None:
    if not execute:
        return
    if llm_provider not in ("anthropic", "hybrid"):
        return
    exported = os.environ.get("ANTHROPIC_API_KEY")
    if exported is not None and not exported.strip():
        print(
            "[validity] WARNING: ANTHROPIC_API_KEY is exported but empty — it shadows backend/.env.\n"
            "  Run: unset ANTHROPIC_API_KEY\n"
            "  Then confirm backend/.env has a valid key or export one explicitly.",
            flush=True,
        )


def build_simulation_request(
    *,
    profile: ValidityTrialProfile,
    seed: int,
    network_csv: str,
    llm_provider: str | None,
    model_profile_id: str | None,
) -> SimulationRunRequest:
    return SimulationRunRequest(
        scenario_id=profile.scenario_id,
        agent_limit=profile.agent_limit,
        total_rounds=profile.total_rounds,
        random_seed=seed,
        visibility_policy=profile.visibility_policy,
        sampling_strategy=profile.sampling_strategy,
        turn_order_policy=profile.turn_order_policy,
        network_csv=network_csv,
        llm_provider=llm_provider,
        model_profile_id=model_profile_id,
        rag_enabled=False,
        convergence_threshold=None,
        likert_self_report_enabled=FROZEN_MECHANISM_FLAGS["likert_self_report_enabled"] or None,
        importance_scoring_enabled=FROZEN_MECHANISM_FLAGS["importance_scoring_enabled"] or None,
        weighted_retrieval_enabled=FROZEN_MECHANISM_FLAGS["weighted_retrieval_enabled"] or None,
        reflection_enabled=FROZEN_MECHANISM_FLAGS["reflection_enabled"] or None,
    )


async def run_validity_trial_via_api(
    *,
    settings,
    profile: ValidityTrialProfile,
    trial_label: str,
    seed: int,
    network_csv: str,
    llm_provider: str | None = None,
    model_profile_id: str | None = None,
) -> ValidityTrialRecord:
    req = build_simulation_request(
        profile=profile,
        seed=seed,
        network_csv=network_csv,
        llm_provider=llm_provider,
        model_profile_id=model_profile_id,
    )
    t0 = time.perf_counter()
    resp = await queue_simulation_run(
        settings,
        req,
        run_display_name=f"validity-{trial_label}-s{seed}",
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
    if status == "completed":
        check_transcript_qa(bundle, simulation_id=resp.id, trial_label=trial_label, seed=seed)
    economics = (
        extract_economics_summary(bundle=bundle, wall_clock_seconds=elapsed)
        if status == "completed"
        else None
    )
    return ValidityTrialRecord(
        trial_label=trial_label,
        random_seed=seed,
        simulation_id=resp.id,
        status=status,
        total_rounds=profile.total_rounds,
        economics_summary=economics,
    )


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="SSTRF RQ1 validity-trial simulation harness")
    p.add_argument("--seeds-path", type=Path, default=default_seeds_path(root=_REPO_ROOT))
    p.add_argument("--freeze-path", type=Path, default=default_freeze_path(root=_REPO_ROOT))
    p.add_argument("--provenance-path", type=Path, default=default_provenance_path(root=_REPO_ROOT))
    p.add_argument(
        "--manifest-out",
        type=Path,
        default=None,
        help="Manifest write path. Dry-run skips writing unless this is set to a non-production "
        "scratch path. Execute defaults to docs/diagnostics/sstrf_validity_v2_manifest.json.",
    )
    p.add_argument("--study-repo-path", default="", help="Path to senna-sstrf-study checkout")
    p.add_argument(
        "--network-csv-rel-path",
        default=DEFAULT_NETWORK_CSV_REL,
        help="Network CSV path relative to study repo",
    )
    p.add_argument("--network-csv-text", default="", help="Inline network CSV (tests/local override)")
    p.add_argument("--sqlite-path", default="", help="SQLite path (default: settings)")
    p.add_argument("--llm-provider", default="anthropic", choices=["lmstudio", "anthropic", "hybrid"])
    p.add_argument("--model-profile-id", default=ANTHROPIC_DEFAULT_ID)
    p.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate config and write manifest with planned trials (no API calls)",
    )
    p.add_argument(
        "--execute",
        action="store_true",
        help="Queue all validity trials (live spend when llm-provider=anthropic)",
    )
    p.add_argument("--env-file", type=Path, default=_DEFAULT_ENV_FILE)
    return p


async def _main_async(args: argparse.Namespace) -> dict:
    if args.execute and args.dry_run:
        raise RuntimeError("choose one of --dry-run or --execute, not both")

    mode = "execute" if args.execute else "dry_run"
    seeds_doc = load_study_seeds(path=args.seeds_path)
    freeze = load_platform_freeze(path=args.freeze_path)
    provenance = load_fixture_provenance(path=args.provenance_path)
    assert_fixture_provenance_matches(freeze=freeze, provenance=provenance)

    if args.execute:
        assert_freeze_signed(freeze)

    settings = get_settings()
    sqlite_path = args.sqlite_path or settings.sqlite_path
    await schema_init(sqlite_path)

    profile = ValidityTrialProfile(network_csv_rel_path=args.network_csv_rel_path)
    plan = build_validity_run_plan(seeds_doc=seeds_doc)
    print_validity_banner(profile=profile, trial_count=len(plan))
    print_anthropic_key_pitfall_if_relevant(execute=args.execute, llm_provider=args.llm_provider)
    print_config_banner(settings)

    if not await user_scenario_exists(sqlite_path, scenario_id=profile.scenario_id):
        raise RuntimeError(
            f"scenario {profile.scenario_id!r} not in user_scenarios — seed first via "
            "scripts/seed_scenario_from_study_repo.py (see docs/SETUP_STUDY_FIXTURES.md).",
        )

    scenario_cfg, _src = await load_scenario_for_run(sqlite_path, profile.scenario_id)
    persona_ids = [p.persona_id for p in scenario_cfg.personas[: profile.agent_limit]]
    if len(persona_ids) < profile.agent_limit:
        raise RuntimeError(
            f"scenario {profile.scenario_id!r} has {len(scenario_cfg.personas)} personas; "
            f"need {profile.agent_limit} for validity trials.",
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
    print(
        f"[validity] network CSV: {len(net_parse.edges)} edges for {len(expected_ids)} agents",
        flush=True,
    )
    if net_parse.warnings:
        for warning in net_parse.warnings:
            print(f"[validity] network warning: {warning}", flush=True)

    print(f"[validity] run plan: {plan}", flush=True)

    if mode == "dry_run":
        records = build_planned_trial_records(plan=plan, total_rounds=profile.total_rounds)
    else:
        records = []
        model_profile_id = args.model_profile_id.strip() or None
        for trial_label, seed in plan:
            rec = await run_validity_trial_via_api(
                settings=settings,
                profile=profile,
                trial_label=trial_label,
                seed=seed,
                network_csv=network_csv,
                llm_provider=args.llm_provider,
                model_profile_id=model_profile_id,
            )
            records.append(rec)
            print(
                json.dumps(
                    {
                        "trial_label": trial_label,
                        "random_seed": seed,
                        "simulation_id": rec.simulation_id,
                        "status": rec.status,
                        "economics_summary": rec.economics_summary,
                    },
                ),
                flush=True,
            )

    payload = build_manifest_payload(
        profile=profile,
        records=records,
        command=" ".join(sys.argv),
        mode=mode,
        freeze=freeze,
        pre_reg_path=_PREREG_PATH,
        freeze_path=str(args.freeze_path.relative_to(_REPO_ROOT))
        if args.freeze_path.is_relative_to(_REPO_ROOT)
        else str(args.freeze_path),
    )
    manifest_path = resolve_validity_manifest_write_path(
        mode=mode,
        manifest_out=args.manifest_out,
        root=_REPO_ROOT,
    )
    if manifest_path is not None:
        write_manifest(path=manifest_path, payload=payload)
        payload["artifacts"] = {"manifest": str(manifest_path)}
    else:
        payload["artifacts"] = {}
    payload["profile_snapshot"] = profile_snapshot(profile)
    return payload


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if not args.dry_run and not args.execute:
        args.dry_run = True
    load_dotenv_if_present(args.env_file)
    try:
        payload = asyncio.run(_main_async(args))
    except (ValueError, RuntimeError, FileNotFoundError) as exc:
        print(f"\n{exc}\n", file=sys.stderr)
        print(json.dumps({"error": str(exc)}), file=sys.stderr)
        return 1
    print(
        json.dumps(
            {
                "status": "ok",
                "mode": payload.get("mode"),
                "trial_count": len(payload.get("trials") or []),
                "manifest": payload.get("artifacts", {}).get("manifest"),
            },
        ),
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

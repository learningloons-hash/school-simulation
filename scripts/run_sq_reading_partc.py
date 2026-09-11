#!/usr/bin/env python3
"""Part C — sq_reading_culture 2×2 context × shock study (GM-F 2026-09-10).

12 runs (4 cells × seeds 101–103). Mechanics report + blind analyst package.

**ANTHROPIC_API_KEY pitfall (iter-55):** a stale shell export shadows ``backend/.env``
and live runs 401 even when ``.env`` is valid. This script calls
``load_backend_env_for_live_runs()`` to clear shell shadows before loading ``.env``.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import random
import re
import io
import statistics
import sys
import time
import zipfile
from dataclasses import dataclass, field
from datetime import UTC, datetime
from io import BytesIO
from pathlib import Path
from typing import Any

_REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_REPO_ROOT / "backend" / "src"))
sys.path.insert(0, str(_REPO_ROOT / "scripts"))

from run_arc11_ablation import (  # noqa: E402
    load_backend_env_for_live_runs,
    print_config_banner,
)

from mirofish_backend.api.simulations import (  # noqa: E402
    SimulationRunRequest,
    build_preflight_response,
    queue_simulation_run,
    wait_for_simulation_terminal,
)
from mirofish_backend.config import get_settings  # noqa: E402
from mirofish_backend.db.repo import get_simulation_export_bundle  # noqa: E402
from mirofish_backend.db.schema import init_db as schema_init  # noqa: E402
from mirofish_backend.diagnostics.arc12_study_rehearsal import (  # noqa: E402
    DEFAULT_NETWORK_CSV_REL,
    build_expected_run_agent_ids,
    count_context_length_failures,
    count_llm_errors,
    extract_mechanics_metrics,
    load_documented_network_csv,
    state_update_source_counts,
)
from mirofish_backend.export_bundle import build_export_zip  # noqa: E402
from mirofish_backend.scenarios.loader import load_scenario_for_run  # noqa: E402

AGENT_LIMIT = 8
TOTAL_ROUNDS = 10
SEEDS = (101, 102, 103)
PREFLIGHT_COST_CAP_USD = 0.70
# 2026-09-03 tempsweep measured ~$0.32/run ($3.87/12); preflight envelope is ~3.7× conservative.
TEMPSWEEP_MEASURED_MEAN_USD = 0.3225
SHOCK_ROUND = 5

CELLS: tuple[tuple[str, str, bool], ...] = (
    ("positive_no_shock", "sq_reading_culture", False),
    ("adverse_no_shock", "sq_reading_culture_adverse", False),
    ("positive_shock", "sq_reading_culture_shock", True),
    ("adverse_shock", "sq_reading_culture_adverse_shock", True),
)

SENTINEL_POSITIVE = "in post for several years"
SENTINEL_ADVERSE = "three principals in six years"

CONTEXT_LEAKAGE_TERMS = [
    "three principals",
    "abandoned",
    "high-needs",
    "stretched",
    "wary",
    "limited spare capacity",
    "established",
    "stable",
    "routine",
    "adequate",
    "several years",
    "accustomed",
]
NEUTRAL_SCENARIO_ID = "reading_culture_programme"

_DEFAULT_OUT = _REPO_ROOT / "docs/research/runs/sq_reading_culture/2026-09-10"
_DEFAULT_SQLITE = _REPO_ROOT / "backend/data/sq_reading_partc.sqlite"
_DEFAULT_ENV = _REPO_ROOT / "backend/.env"


@dataclass
class PartCRunRecord:
    cell: str
    scenario_id: str
    seed: int
    simulation_id: str
    status: str
    has_shock: bool
    mechanics: dict[str, Any] = field(default_factory=dict)
    decline_at_shock: int | None = None
    shock_round_all_declined: bool | None = None
    final_support_mean: float | None = None
    final_support_spread: float | None = None


def build_request(*, scenario_id: str, seed: int, network_csv: str) -> SimulationRunRequest:
    return SimulationRunRequest(
        scenario_id=scenario_id,
        agent_limit=AGENT_LIMIT,
        total_rounds=TOTAL_ROUNDS,
        random_seed=seed,
        llm_provider="anthropic",
        model_profile_id="anthropic_default",
        visibility_policy="network_bounded",
        sampling_strategy="full_census",
        network_csv=network_csv,
        rag_enabled=False,
        importance_scoring_enabled=False,
        weighted_retrieval_enabled=False,
        reflection_enabled=False,
        likert_self_report_enabled=False,
        convergence_threshold=None,
    )


def assert_run_gates(bundle: dict[str, Any], *, simulation_id: str, cell: str, seed: int) -> None:
    run = bundle.get("run") or {}
    cfg = run.get("config_snapshot") or {}
    transcript = bundle.get("transcript") or []
    status = str(run.get("status") or "")

    if status != "completed":
        raise RuntimeError(f"{simulation_id} ({cell} s{seed}) status={status!r} — not usable")

    if count_llm_errors(transcript):
        sample = next(
            (
                str(t.get("raw_response") or "")
                for t in transcript
                if str(t.get("raw_response") or "").startswith("[LLM error]")
            ),
            "",
        )
        if "401" in sample or "Unauthorized" in sample:
            raise RuntimeError(
                f"{simulation_id}: Anthropic 401 Unauthorized — check ANTHROPIC_API_KEY in "
                "backend/.env (unset stale shell export: env -u ANTHROPIC_API_KEY)"
            )
        raise RuntimeError(f"{simulation_id}: LLM errors present — {sample[:200]}")
    if count_context_length_failures(transcript):
        raise RuntimeError(f"{simulation_id}: context-length failures present")

    src_counts = state_update_source_counts(transcript)
    non_parsed = {k: v for k, v in src_counts.items() if k != "model_parsed"}
    if non_parsed:
        raise RuntimeError(f"{simulation_id}: state_update_source not all model_parsed: {non_parsed}")

    if not cfg.get("network_csv_applied"):
        raise RuntimeError(f"{simulation_id}: network_csv_applied is false")

    ip = cfg.get("interaction_policy") or {}
    if isinstance(ip, dict):
        if ip.get("network_visibility_fallback"):
            raise RuntimeError(f"{simulation_id}: network_visibility_fallback=true")
        if ip.get("visibility_effective") != "network_bounded":
            raise RuntimeError(
                f"{simulation_id}: visibility_effective={ip.get('visibility_effective')!r}"
            )


def capture_system_prompt(bundle: dict[str, Any]) -> str:
    for turn in bundle.get("transcript") or []:
        raw = str(turn.get("raw_prompt") or "")
        if "[SYSTEM]" in raw:
            return raw
    return ""


def assert_sentinel(system_prompt: str, *, valence: str, scenario_id: str, seed: int) -> None:
    needle = SENTINEL_POSITIVE if valence == "positive" else SENTINEL_ADVERSE
    if needle.lower() not in system_prompt.lower():
        raise RuntimeError(
            f"SENTINEL FAIL ({scenario_id} seed {seed}): "
            f"expected '{needle}' in system prompt (case-insensitive) — "
            "context not injected"
        )


def support_by_agent_round(bundle: dict[str, Any]) -> dict[str, dict[int, float]]:
    out: dict[str, dict[int, float]] = {}
    for row in bundle.get("agent_state_snapshots") or []:
        aid = str(row.get("agent_id") or "")
        rnd = int(row.get("round_number") or 0)
        if not aid or rnd <= 0:
            continue
        out.setdefault(aid, {})[rnd] = float(row.get("support_level") or 0.0)
    return out


def decline_metrics(bundle: dict[str, Any], *, shock_round: int) -> tuple[int, bool]:
    """Agents declining support into shock_round; True if all 8 declined that round."""
    by_agent = support_by_agent_round(bundle)
    if len(by_agent) < AGENT_LIMIT:
        return 0, False
    declined = 0
    for _aid, rounds in by_agent.items():
        prev = rounds.get(shock_round - 1)
        curr = rounds.get(shock_round)
        if prev is not None and curr is not None and curr < prev:
            declined += 1
    all_same_round = declined == AGENT_LIMIT
    return declined, all_same_round


def final_support_stats(bundle: dict[str, Any]) -> tuple[float | None, float | None]:
    run = bundle.get("run") or {}
    total_rounds = int(run.get("total_rounds") or TOTAL_ROUNDS)
    levels = [
        float(r.get("support_level") or 0.0)
        for r in bundle.get("agent_state_snapshots") or []
        if int(r.get("round_number") or 0) == total_rounds
    ]
    if not levels:
        return None, None
    mean = round(statistics.mean(levels), 6)
    spread = round(max(levels) - min(levels), 6) if len(levels) > 1 else 0.0
    return mean, spread


def _redact_config_snapshot_blob(blob: str) -> str:
    import ast

    if not blob or blob.strip() in ("", "None"):
        return blob
    try:
        data = ast.literal_eval(blob)
    except (SyntaxError, ValueError):
        data = None
    if isinstance(data, dict):
        data.pop("llm_temperature", None)
        data.pop("random_seed", None)
        data.pop("scenario_context", None)
        if "scenario_id" in data:
            data["scenario_id"] = NEUTRAL_SCENARIO_ID
        return repr(data)
    out = blob
    for sid in (
        "sq_reading_culture_adverse_shock",
        "sq_reading_culture_adverse",
        "sq_reading_culture_shock",
        "sq_reading_culture",
    ):
        out = out.replace(sid, NEUTRAL_SCENARIO_ID)
    out = re.sub(r"'llm_temperature':\s*[-\d.]+,?\s*", "", out)
    out = re.sub(r'"llm_temperature":\s*[-\d.]+,?\s*', "", out)
    out = re.sub(r"'random_seed':\s*\d+,?\s*", "", out)
    out = re.sub(r'"random_seed":\s*\d+,?\s*', "", out)
    return out


def redact_analyst_text(text: str, *, run_label: str) -> str:
    out = str(text or "")
    for sid in (
        "sq_reading_culture_adverse_shock",
        "sq_reading_culture_adverse",
        "sq_reading_culture_shock",
        "sq_reading_culture",
    ):
        out = out.replace(sid, NEUTRAL_SCENARIO_ID)
    out = re.sub(r"\bpartc-[\w-]+\b", run_label, out, flags=re.I)
    out = re.sub(r"\bseed[_\s:=]+\d+\b", "", out, flags=re.I)
    out = re.sub(r"\btemperature[_\s:=]+[\d.]+\b", "", out, flags=re.I)
    for term in CONTEXT_LEAKAGE_TERMS:
        out = re.sub(re.escape(term), "[redacted]", out, flags=re.I)
    out = re.sub(r"\b[0-9a-f]{32}\b", "[redacted-id]", out, flags=re.I)
    return out


def assert_no_leakage_in_zip(zip_bytes: bytes, *, path: str) -> None:
    """Scan analyst zip contents for context vocabulary and design metadata."""
    design_patterns = (
        r"sq_reading_culture",
        r"\bpartc-",
        r"'random_seed':\s*\d+",
        r'"random_seed":\s*\d+',
        r"'llm_temperature':\s*[-\d.]+",
        r'"llm_temperature":\s*[-\d.]+',
    )
    hits: list[str] = []
    with zipfile.ZipFile(io.BytesIO(zip_bytes), "r") as zf:
        for name in zf.namelist():
            text = zf.read(name).decode("utf-8", errors="ignore")
            lower = text.lower()
            for term in CONTEXT_LEAKAGE_TERMS:
                if term.lower() in lower:
                    hits.append(term)
            for pat in design_patterns:
                if re.search(pat, text, re.I):
                    hits.append(pat)
    if hits:
        raise RuntimeError(f"leakage check failed for {path}: {hits[:8]}")


def package_for_analyst(
    records: list[PartCRunRecord],
    bundles: dict[str, dict[str, Any]],
    out_dir: Path,
) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    labels = [f"RUN-{chr(ord('A') + i)}" for i in range(len(records))]
    shuffled = list(records)
    random.SystemRandom().shuffle(shuffled)
    key: dict[str, Any] = {
        "generated_at": datetime.now(UTC).isoformat(),
        "note": "Runner-held key — do not ship to Analyst",
        "mapping": {},
    }
    analyst_dir = out_dir / "analyst_package"
    analyst_dir.mkdir(parents=True, exist_ok=True)

    for label, rec in zip(labels, shuffled, strict=True):
        bundle = bundles[rec.simulation_id]
        raw_zip = build_export_zip(bundle)
        buf = io.BytesIO()
        with zipfile.ZipFile(io.BytesIO(raw_zip), "r") as zin, zipfile.ZipFile(
            buf, "w", compression=zipfile.ZIP_DEFLATED
        ) as zout:
            for info in zin.infolist():
                text = zin.read(info.filename).decode("utf-8", errors="ignore")
                text = redact_analyst_text(text, run_label=label)
                if info.filename == "simulation_run.csv":
                    import csv

                    reader = csv.DictReader(io.StringIO(text))
                    if reader.fieldnames:
                        rows = list(reader)
                        out_csv = io.StringIO()
                        writer = csv.DictWriter(
                            out_csv, fieldnames=reader.fieldnames, lineterminator="\n"
                        )
                        writer.writeheader()
                        for row in rows:
                            if "scenario_id" in row:
                                row["scenario_id"] = NEUTRAL_SCENARIO_ID
                            if "name" in row:
                                row["name"] = label
                            if "random_seed" in row:
                                row["random_seed"] = ""
                            if "config_snapshot" in row:
                                row["config_snapshot"] = _redact_config_snapshot_blob(
                                    row.get("config_snapshot") or ""
                                )
                            for col in list(row):
                                if row[col]:
                                    row[col] = redact_analyst_text(str(row[col]), run_label=label)
                            writer.writerow(row)
                        text = out_csv.getvalue()
                zout.writestr(info.filename, text.encode("utf-8"))
        zip_bytes = buf.getvalue()
        assert_no_leakage_in_zip(zip_bytes, path=label)
        zip_path = analyst_dir / f"{label}.zip"
        zip_path.write_bytes(zip_bytes)
        key["mapping"][label] = {
            "simulation_id": rec.simulation_id,
            "cell": rec.cell,
            "scenario_id": rec.scenario_id,
            "seed": rec.seed,
        }

    key_path = out_dir / "analyst_label_key.json"
    key_path.write_text(json.dumps(key, indent=2) + "\n", encoding="utf-8")
    check = {
        "scanned_at": datetime.now(UTC).isoformat(),
        "analyst_package_dir": str(analyst_dir),
        "patterns": CONTEXT_LEAKAGE_TERMS,
        "pass": True,
        "hits": [],
    }
    (out_dir / "analyst_redaction_check.json").write_text(
        json.dumps(check, indent=2) + "\n", encoding="utf-8"
    )
    return key_path


def generate_mechanics_markdown(records: list[PartCRunRecord], *, preflight_usd: float) -> str:
    lines = [
        "# Part C mechanics report — sq_reading 2×2",
        "",
        f"**Date:** 2026-09-10 · **Preflight estimate (per run):** ${preflight_usd:.4f}",
        "",
        "## Per cell",
        "",
        "| Cell | Seed | Status | Decline @ shock | All 8 @ shock | Final support μ | Spread | Cost USD | Wall s |",
        "|---|---:|---|---:|---:|---:|---:|---:|---:|",
    ]
    total_cost = 0.0
    for rec in records:
        m = rec.mechanics
        cost = float(m.get("estimated_cost_usd") or 0.0)
        total_cost += cost
        decline = rec.decline_at_shock if rec.decline_at_shock is not None else "—"
        all8 = rec.shock_round_all_declined if rec.shock_round_all_declined is not None else "—"
        lines.append(
            f"| {rec.cell} | {rec.seed} | {rec.status} | {decline} | {all8} | "
            f"{rec.final_support_mean} | {rec.final_support_spread} | "
            f"{m.get('estimated_cost_usd')} | {m.get('wall_clock_seconds')} |"
        )
    lines.extend(
        [
            "",
            f"**Total estimated cost:** ${total_cost:.4f}",
            "",
            "## Gates",
            "",
            "- Preflight ≤ $0.70/run",
            "- Sentinel: context strings in system prompt (positive/adverse first run each)",
            "- state_update_source: model_parsed throughout",
            "- network_csv_applied true, no broadcast fallback",
            "",
            "*Mechanics only — no transcript interpretation.*",
        ]
    )
    return "\n".join(lines) + "\n"


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Part C sq_reading 2×2 harness")
    p.add_argument("--study-repo-path", default=str(_REPO_ROOT.parent / "senna-sstrf-study"))
    p.add_argument("--network-csv-rel-path", default=DEFAULT_NETWORK_CSV_REL)
    p.add_argument("--sqlite-path", default=str(_DEFAULT_SQLITE))
    p.add_argument("--out-dir", type=Path, default=_DEFAULT_OUT)
    p.add_argument("--env-file", type=Path, default=_DEFAULT_ENV)
    p.add_argument("--execute", action="store_true", help="Queue live Anthropic runs")
    p.add_argument("--preflight-only", action="store_true")
    p.add_argument(
        "--waive-preflight-gate",
        action="store_true",
        help="Proceed when preflight > $0.70 if GM EXECUTE approves spend (~$4; tempsweep measured ~$0.32/run)",
    )
    p.add_argument(
        "--resume",
        action="store_true",
        help="Skip (cell, seed) pairs already in out-dir/partc_manifest.json; reload bundles from sqlite",
    )
    p.add_argument(
        "--package-only",
        action="store_true",
        help="Build analyst package + mechanics report from existing partc_manifest.json (no new runs)",
    )
    return p


def _record_from_manifest_row(row: dict[str, Any]) -> PartCRunRecord:
    return PartCRunRecord(
        cell=str(row["cell"]),
        scenario_id=str(row["scenario_id"]),
        seed=int(row["seed"]),
        simulation_id=str(row["simulation_id"]),
        status=str(row["status"]),
        has_shock=bool(row["has_shock"]),
        mechanics=dict(row.get("mechanics") or {}),
        decline_at_shock=row.get("decline_at_shock"),
        shock_round_all_declined=row.get("shock_round_all_declined"),
        final_support_mean=row.get("final_support_mean"),
        final_support_spread=row.get("final_support_spread"),
    )


def _manifest_row(rec: PartCRunRecord) -> dict[str, Any]:
    return {
        "cell": rec.cell,
        "scenario_id": rec.scenario_id,
        "seed": rec.seed,
        "simulation_id": rec.simulation_id,
        "status": rec.status,
        "has_shock": rec.has_shock,
        "decline_at_shock": rec.decline_at_shock,
        "shock_round_all_declined": rec.shock_round_all_declined,
        "final_support_mean": rec.final_support_mean,
        "final_support_spread": rec.final_support_spread,
        "mechanics": rec.mechanics,
    }


def _write_manifest(path: Path, *, records: list[PartCRunRecord], est: float) -> None:
    payload = {
        "harness": "partc-sq-reading-2x2",
        "date": "2026-09-10",
        "seeds": list(SEEDS),
        "preflight_estimated_cost_usd": est,
        "runs": [_manifest_row(r) for r in records],
    }
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


async def assert_anthropic_key_from_backend_env(settings) -> None:
    """One-turn ping so a stale shell key fails before 12-run spend."""
    import httpx

    from mirofish_backend.llm.claude_client import chat_completion_anthropic

    api_key = (settings.anthropic_api_key or "").strip()
    if not api_key:
        raise RuntimeError(
            "ANTHROPIC_API_KEY missing after loading backend/.env — add to backend/.env"
        )
    try:
        await chat_completion_anthropic(
            api_key=api_key,
            model=settings.anthropic_model,
            system_prompt="Reply with OK",
            user_prompt="ping",
            temperature=0.0,
            max_tokens=8,
            timeout_s=30.0,
        )
    except httpx.HTTPStatusError as exc:
        status = exc.response.status_code if exc.response is not None else "?"
        if status == 401:
            raise RuntimeError(
                "Anthropic preflight HTTP 401 — the key now loaded from backend/.env "
                f"({settings.anthropic_model}) is rejected by Anthropic. "
                "Shell shadowing is already cleared; rotate or replace ANTHROPIC_API_KEY "
                "in backend/.env (console.anthropic.com → API keys), then run "
                "scripts/check_anthropic_key.py to verify before Part C spend."
            ) from exc
        raise RuntimeError(f"Anthropic preflight failed HTTP {status}.") from exc


async def _main_async(args: argparse.Namespace) -> dict[str, Any]:
    load_backend_env_for_live_runs(args.env_file)
    settings = get_settings()
    sqlite_path = args.sqlite_path or settings.sqlite_path
    await schema_init(sqlite_path)

    if not args.package_only:
        if abs(settings.llm_temperature - 0.8) > 0.01:
            raise RuntimeError(
                f"LLM_TEMPERATURE must be 0.8 for Part C (got {settings.llm_temperature})"
            )
        if not settings.anthropic_api_key:
            raise RuntimeError("ANTHROPIC_API_KEY not configured in backend/.env")

    print_config_banner(settings)
    study_repo = Path(args.study_repo_path)
    if not study_repo.is_dir():
        raise FileNotFoundError(f"study repo not found: {study_repo}")

    # Load network once from representative scenario
    scenario_cfg, _ = await load_scenario_for_run(sqlite_path, "sq_reading_culture")
    persona_ids = [p.persona_id for p in scenario_cfg.personas[:AGENT_LIMIT]]
    expected_ids = frozenset(build_expected_run_agent_ids(persona_ids=persona_ids))
    network_csv, net_parse = load_documented_network_csv(
        study_repo_path=study_repo,
        rel_path=args.network_csv_rel_path,
        expected_agent_ids=expected_ids,
    )
    print(f"[partc] network CSV: {len(net_parse.edges)} edges", flush=True)

    req = build_request(scenario_id="sq_reading_culture", seed=SEEDS[0], network_csv=network_csv)
    preflight = await build_preflight_response(settings, req)
    pf = preflight.preflight or {}
    est = float(pf.get("estimated_cost_usd") or 0.0)
    print(f"[partc] preflight estimated_cost_usd={est:.4f}", flush=True)
    if est > PREFLIGHT_COST_CAP_USD and not args.package_only:
        msg = (
            f"PREFLIGHT GATE: ${est:.4f}/run exceeds cap ${PREFLIGHT_COST_CAP_USD:.2f} "
            f"(tempsweep measured ~${TEMPSWEEP_MEASURED_MEAN_USD:.4f}/run)"
        )
        if not args.waive_preflight_gate:
            raise RuntimeError(msg)
        print(f"[partc] WARNING: {msg} — waived under GM EXECUTE", flush=True)
    if args.preflight_only or (not args.execute and not args.package_only):
        return {"status": "preflight_ok", "estimated_cost_usd": est, "planned_runs": len(CELLS) * len(SEEDS)}

    if args.package_only:
        manifest_path = args.out_dir / "partc_manifest.json"
        if not manifest_path.is_file():
            raise FileNotFoundError(f"missing {manifest_path}")
        prev = json.loads(manifest_path.read_text(encoding="utf-8"))
        records = [_record_from_manifest_row(row) for row in prev.get("runs") or []]
        if len(records) != len(CELLS) * len(SEEDS):
            raise RuntimeError(f"expected 12 runs in manifest, got {len(records)}")
        bundles: dict[str, dict[str, Any]] = {}
        for rec in records:
            bundle = await get_simulation_export_bundle(
                settings.sqlite_path, simulation_id=rec.simulation_id
            )
            if bundle is None:
                raise RuntimeError(f"missing bundle for {rec.simulation_id}")
            bundles[rec.simulation_id] = bundle
        args.out_dir.mkdir(parents=True, exist_ok=True)
        md_path = args.out_dir / "PARTC_MECHANICS_REPORT.md"
        md_path.write_text(generate_mechanics_markdown(records, preflight_usd=est), encoding="utf-8")
        key_path = package_for_analyst(records, bundles, args.out_dir)
        print(f"[partc] analyst key: {key_path}", flush=True)
        return {"status": "packaged", "run_count": len(records), "manifest": str(manifest_path)}

    await assert_anthropic_key_from_backend_env(settings)
    print("[partc] Anthropic API key OK (backend/.env)", flush=True)

    args.out_dir.mkdir(parents=True, exist_ok=True)
    exports_dir = args.out_dir / "exports"
    exports_dir.mkdir(parents=True, exist_ok=True)

    manifest_path = args.out_dir / "partc_manifest.json"
    records: list[PartCRunRecord] = []
    bundles: dict[str, dict[str, Any]] = {}
    sentinel_done: set[str] = set()
    done_pairs: set[tuple[str, int]] = set()

    if args.resume and manifest_path.is_file():
        prev = json.loads(manifest_path.read_text(encoding="utf-8"))
        for row in prev.get("runs") or []:
            rec = _record_from_manifest_row(row)
            records.append(rec)
            done_pairs.add((rec.cell, rec.seed))
            bundle = await get_simulation_export_bundle(
                settings.sqlite_path, simulation_id=rec.simulation_id
            )
            if bundle is None:
                raise RuntimeError(f"resume: missing bundle for {rec.simulation_id}")
            bundles[rec.simulation_id] = bundle
            valence = "positive" if rec.cell.startswith("positive") else "adverse"
            if rec.seed == SEEDS[0]:
                sentinel_done.add(valence)
        print(f"[partc] resume: {len(done_pairs)} runs already complete", flush=True)

    for cell, scenario_id, has_shock in CELLS:
        valence = "positive" if cell.startswith("positive") else "adverse"
        for seed in SEEDS:
            if (cell, seed) in done_pairs:
                continue
            t0 = time.perf_counter()
            run_req = build_request(scenario_id=scenario_id, seed=seed, network_csv=network_csv)
            resp = await queue_simulation_run(
                settings,
                run_req,
                run_display_name=f"partc-{cell}-s{seed}",
            )
            terminal = await wait_for_simulation_terminal(
                sqlite_path=settings.sqlite_path,
                simulation_id=resp.id,
                timeout_seconds=7200.0,
            )
            elapsed = time.perf_counter() - t0
            bundle = await get_simulation_export_bundle(settings.sqlite_path, simulation_id=resp.id)
            if bundle is None:
                raise RuntimeError(f"missing bundle for {resp.id}")

            assert_run_gates(bundle, simulation_id=resp.id, cell=cell, seed=seed)

            if valence not in sentinel_done and seed == SEEDS[0]:
                assert_sentinel(
                    capture_system_prompt(bundle),
                    valence=valence,
                    scenario_id=scenario_id,
                    seed=seed,
                )
                sentinel_done.add(valence)
                print(f"[partc] SENTINEL PASS ({valence})", flush=True)

            decline_n, all8 = (None, None)
            if has_shock:
                decline_n, all8 = decline_metrics(bundle, shock_round=SHOCK_ROUND)

            fmean, fspread = final_support_stats(bundle)
            mechanics = extract_mechanics_metrics(bundle=bundle, wall_clock_seconds=elapsed)
            rec = PartCRunRecord(
                cell=cell,
                scenario_id=scenario_id,
                seed=seed,
                simulation_id=resp.id,
                status=str(terminal.get("status") or ""),
                has_shock=has_shock,
                mechanics=mechanics,
                decline_at_shock=decline_n,
                shock_round_all_declined=all8,
                final_support_mean=fmean,
                final_support_spread=fspread,
            )
            records.append(rec)
            bundles[resp.id] = bundle

            zip_bytes = build_export_zip(bundle)
            (exports_dir / f"{resp.id}.zip").write_bytes(zip_bytes)

            print(
                json.dumps(
                    {
                        "cell": cell,
                        "seed": seed,
                        "simulation_id": resp.id,
                        "status": rec.status,
                        "decline_at_shock": decline_n,
                        "wall_s": round(elapsed, 1),
                        "cost_usd": mechanics.get("estimated_cost_usd"),
                    }
                ),
                flush=True,
            )
            _write_manifest(manifest_path, records=records, est=est)

    _write_manifest(manifest_path, records=records, est=est)

    md_path = args.out_dir / "PARTC_MECHANICS_REPORT.md"
    md_path.write_text(generate_mechanics_markdown(records, preflight_usd=est), encoding="utf-8")

    key_path = package_for_analyst(records, bundles, args.out_dir)
    print(f"[partc] analyst key: {key_path}", flush=True)
    print(f"[partc] manifest: {manifest_path}", flush=True)

    return {"status": "completed", "run_count": len(records), "manifest": str(manifest_path)}


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        payload = asyncio.run(_main_async(args))
    except (ValueError, RuntimeError, FileNotFoundError, TimeoutError) as exc:
        print(f"\n[partc] FAILED: {exc}\n", file=sys.stderr)
        return 1
    print(json.dumps(payload))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Persona-rich utility run — sq_reading_culture 2 cells × 3 seeds (GM-F 2026-09-11).

6 live runs (positive_rich + adverse_rich), packaged blind with 6 Part C no-shock comparators.

**ANTHROPIC_API_KEY pitfall (iter-55):** uses ``load_backend_env_for_live_runs()`` from Part C harness.
"""

from __future__ import annotations

import argparse
import asyncio
import csv
import io
import json
import random
import re
import statistics
import sys
import time
import zipfile
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

_REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_REPO_ROOT / "backend" / "src"))
sys.path.insert(0, str(_REPO_ROOT / "scripts"))

from run_arc11_ablation import (  # noqa: E402
    load_backend_env_for_live_runs,
    print_config_banner,
)
from run_sq_reading_partc import (  # noqa: E402
    AGENT_LIMIT,
    CONTEXT_LEAKAGE_TERMS,
    NEUTRAL_SCENARIO_ID,
    PREFLIGHT_COST_CAP_USD,
    SEEDS,
    TOTAL_ROUNDS,
    _redact_config_snapshot_blob,
    assert_run_gates,
    build_request,
    capture_system_prompt,
)

from mirofish_backend.api.simulations import (  # noqa: E402
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
    load_documented_network_csv,
    extract_mechanics_metrics,
)
from mirofish_backend.export_bundle import build_export_zip  # noqa: E402
from mirofish_backend.scenarios.loader import load_scenario_for_run  # noqa: E402
from mirofish_backend.scenarios.registry import get_scenario  # noqa: E402

CELLS: tuple[tuple[str, str], ...] = (
    ("positive_rich", "sq_reading_culture_rich"),
    ("adverse_rich", "sq_reading_culture_adverse_rich"),
)

PARTC_COMPARATOR_CELLS = frozenset({"positive_no_shock", "adverse_no_shock"})

SENTINEL_POSITIVE = "in post for several years"
SENTINEL_ADVERSE = "three principals in six years"
PERSONA_SENTINEL = "Twenty-two years in"

PERSONA_VOCAB_LEAKAGE = [
    "no-pay leave",
    "over-promise",
    "Twenty-two years in",
    "works shifts",
    "veteran",
    "reads voraciously",
    "integration not accumulation",
]

STARTING_SUPPORT_ORDER: tuple[str, ...] = (
    "parent_001",
    "senior_teacher_001",
    "vice_principal_001",
    "parent_003",
    "hod_english_001",
    "teacher_001",
    "parent_002",
    "parent_004",
)

LANGUAGE_REUSE_PHRASES = (
    "i need to be direct",
    "before we commit",
    "written confirmation",
    "integration not accumulation",
    "protected reading period",
    "within the protected period",
)

SCENARIO_IDS_TO_REDACT = (
    "sq_reading_culture_adverse_shock",
    "sq_reading_culture_adverse_rich",
    "sq_reading_culture_adverse",
    "sq_reading_culture_shock",
    "sq_reading_culture_rich",
    "sq_reading_culture",
)

_DEFAULT_OUT = _REPO_ROOT / "docs/research/runs/sq_reading_culture/2026-09-11-persona-rich"
_DEFAULT_SQLITE = _REPO_ROOT / "backend/data/sq_reading_persona_rich.sqlite"
_DEFAULT_ENV = _REPO_ROOT / "backend/.env"
_DEFAULT_PARTC_MANIFEST = (
    _REPO_ROOT / "docs/research/runs/sq_reading_culture/2026-09-10/partc_manifest.json"
)


@dataclass
class RunRecord:
    cell: str
    scenario_id: str
    seed: int
    simulation_id: str
    status: str
    source: str  # "rich" | "partc_comparator"
    mechanics: dict[str, Any] = field(default_factory=dict)
    final_support_mean: float | None = None
    final_support_min: float | None = None
    final_support_max: float | None = None
    final_support_stdev: float | None = None
    final_support_spread: float | None = None
    rank_order_match: bool | None = None
    rank_kendall_tau: float | None = None
    language_reuse_hits: list[str] = field(default_factory=list)


def assert_context_sentinel(system_prompt: str, *, valence: str, scenario_id: str, seed: int) -> None:
    needle = SENTINEL_POSITIVE if valence == "positive" else SENTINEL_ADVERSE
    if needle.lower() not in system_prompt.lower():
        raise RuntimeError(
            f"SENTINEL FAIL ({scenario_id} seed {seed}): expected '{needle}' in system prompt"
        )


def capture_teacher_system_prompt(bundle: dict[str, Any]) -> str:
    for turn in bundle.get("transcript") or []:
        aid = str(turn.get("agent_id") or "")
        if not aid.startswith("teacher_001_"):
            continue
        raw = str(turn.get("raw_prompt") or "")
        if "[SYSTEM]" in raw:
            return raw
    return ""


def assert_persona_sentinel(bundle: dict[str, Any], *, scenario_id: str, seed: int) -> None:
    prompt = capture_teacher_system_prompt(bundle)
    if PERSONA_SENTINEL not in prompt:
        raise RuntimeError(
            f"PERSONA SENTINEL FAIL ({scenario_id} seed {seed}): "
            f"expected '{PERSONA_SENTINEL}' in P2 form teacher system prompt"
        )


def final_support_by_agent(bundle: dict[str, Any]) -> dict[str, float]:
    run = bundle.get("run") or {}
    total_rounds = int(run.get("total_rounds") or TOTAL_ROUNDS)
    out: dict[str, float] = {}
    for row in bundle.get("agent_state_snapshots") or []:
        if int(row.get("round_number") or 0) != total_rounds:
            continue
        aid = str(row.get("agent_id") or "")
        if aid:
            out[aid] = float(row.get("support_level") or 0.0)
    return out


def support_spread_stats(levels: list[float]) -> tuple[float | None, float | None, float | None, float | None]:
    if not levels:
        return None, None, None, None
    mn = round(min(levels), 6)
    mx = round(max(levels), 6)
    spread = round(mx - mn, 6) if len(levels) > 1 else 0.0
    stdev = round(statistics.stdev(levels), 6) if len(levels) > 1 else 0.0
    return mn, mx, stdev, spread


def kendall_tau(order_a: list[str], order_b: list[str]) -> float:
    if len(order_a) != len(order_b) or len(order_a) < 2:
        return 1.0
    pos_b = {aid: i for i, aid in enumerate(order_b)}
    concordant = 0
    discordant = 0
    for i in range(len(order_a)):
        for j in range(i + 1, len(order_a)):
            a_i, a_j = order_a[i], order_a[j]
            if a_i not in pos_b or a_j not in pos_b:
                continue
            if pos_b[a_i] < pos_b[a_j]:
                concordant += 1
            elif pos_b[a_i] > pos_b[a_j]:
                discordant += 1
    denom = concordant + discordant
    return 1.0 if denom == 0 else round((concordant - discordant) / denom, 4)


def rank_order_metrics(final_by_agent: dict[str, float]) -> tuple[bool, float]:
    present = [aid for aid in STARTING_SUPPORT_ORDER if aid in final_by_agent]
    if len(present) < 2:
        return False, 0.0
    configured = list(present)
    final_sorted = sorted(present, key=lambda aid: final_by_agent[aid], reverse=True)
    tau = kendall_tau(configured, final_sorted)
    return configured == final_sorted, tau


def scan_language_reuse(bundle: dict[str, Any]) -> list[str]:
    """Phrases used by 3+ distinct agents in one run (Part C blind-analyst pattern)."""
    by_phrase: dict[str, set[str]] = {}
    for turn in bundle.get("transcript") or []:
        aid = str(turn.get("agent_id") or "")
        text = str(turn.get("agent_response") or turn.get("response") or "").lower()
        if not aid or not text:
            continue
        for phrase in LANGUAGE_REUSE_PHRASES:
            if phrase in text:
                by_phrase.setdefault(phrase, set()).add(aid)
    return sorted(p for p, agents in by_phrase.items() if len(agents) >= 3)


def redact_analyst_text(
    text: str, *, run_label: str, redact_configured_values: bool = True
) -> str:
    """Redact identifying metadata from analyst-facing text.

    GM-F, 2026-09-11: redaction must never touch measurements. ``redact_configured_values``
    gates the persona-configured-value scrub (e.g. "0.45") — callers MUST pass
    ``redact_configured_values=False`` for any file/column holding actual simulation state
    (support_level, resistance_level, workload_stress, round_number, agent id). Those are
    real measurements the Analyst needs to compute the finding, not identifying metadata,
    and can legitimately collide with the same decimal strings used in a persona's
    configured starting values.
    """
    out = str(text or "")
    for sid in SCENARIO_IDS_TO_REDACT:
        out = out.replace(sid, NEUTRAL_SCENARIO_ID)
    out = re.sub(r"\bpartc-[\w-]+\b", run_label, out, flags=re.I)
    out = re.sub(r"\bpersona-rich-[\w-]+\b", run_label, out, flags=re.I)
    out = re.sub(r"\bseed[_\s:=]+\d+\b", "", out, flags=re.I)
    out = re.sub(r"\btemperature[_\s:=]+[\d.]+\b", "", out, flags=re.I)
    for term in CONTEXT_LEAKAGE_TERMS:
        out = re.sub(re.escape(term), "[redacted]", out, flags=re.I)
    for term in PERSONA_VOCAB_LEAKAGE:
        out = re.sub(re.escape(term), "[redacted]", out, flags=re.I)
    if redact_configured_values:
        for val in ("0.75", "0.45", "0.80", "0.40", "0.85", "0.35", "0.55", "0.30", "0.60", "0.25"):
            out = out.replace(val, "[redacted]")
    out = re.sub(r"\b[0-9a-f]{32}\b", "[redacted-id]", out, flags=re.I)
    return out


def assert_no_leakage_in_zip(zip_bytes: bytes, *, path: str) -> None:
    design_patterns = (
        r"sq_reading_culture",
        r"\bpartc-",
        r"\bpersona-rich-",
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
            for term in CONTEXT_LEAKAGE_TERMS + PERSONA_VOCAB_LEAKAGE:
                if term.lower() in lower:
                    hits.append(term)
            for pat in design_patterns:
                if re.search(pat, text, re.I):
                    hits.append(pat)
    if hits:
        raise RuntimeError(f"leakage check failed for {path}: {hits[:10]}")


def assert_no_measurement_redaction_in_zip(zip_bytes: bytes, *, path: str) -> None:
    """GM-F, 2026-09-11: redaction must never touch measurements — fail loudly if it did."""
    measurement_files = {
        "agent_state_snapshots.csv": ("support_level", "resistance_level", "workload_stress"),
    }
    with zipfile.ZipFile(io.BytesIO(zip_bytes), "r") as zf:
        for fname, cols in measurement_files.items():
            if fname not in zf.namelist():
                continue
            text = zf.read(fname).decode("utf-8", errors="ignore")
            reader = csv.DictReader(io.StringIO(text))
            for row_num, row in enumerate(reader, start=2):
                for col in cols:
                    val = row.get(col)
                    if val is not None and "[redacted" in val.lower():
                        raise RuntimeError(
                            f"{path}: measurement redaction detected in {fname} "
                            f"row {row_num} column {col!r} \u2014 redaction must never touch "
                            f"measurements (GM-F, 2026-09-11)"
                        )


def package_for_analyst(
    records: list[RunRecord],
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
            never_value_redact_files = {
                "agent_state_snapshots.csv",
                "global_state_snapshots.csv",
                "round_outcomes.csv",
                "agent_round_likert.csv",
            }
            for info in zin.infolist():
                text = zin.read(info.filename).decode("utf-8", errors="ignore")
                text = redact_analyst_text(
                    text,
                    run_label=label,
                    redact_configured_values=info.filename not in never_value_redact_files,
                )
                if info.filename == "simulation_run.csv":
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
                            never_redact_columns = {
                                "support_level",
                                "resistance_level",
                                "workload_stress",
                                "round_number",
                                "agent_id",
                            }
                            for col in list(row):
                                if col in never_redact_columns:
                                    continue
                                if row[col]:
                                    row[col] = redact_analyst_text(str(row[col]), run_label=label)
                            writer.writerow(row)
                        text = out_csv.getvalue()
                zout.writestr(info.filename, text.encode("utf-8"))
        zip_bytes = buf.getvalue()
        assert_no_leakage_in_zip(zip_bytes, path=label)
        assert_no_measurement_redaction_in_zip(zip_bytes, path=label)
        (analyst_dir / f"{label}.zip").write_bytes(zip_bytes)
        key["mapping"][label] = {
            "simulation_id": rec.simulation_id,
            "cell": rec.cell,
            "scenario_id": rec.scenario_id,
            "seed": rec.seed,
            "source": rec.source,
        }

    key_path = out_dir / "analyst_label_key.json"
    key_path.write_text(json.dumps(key, indent=2) + "\n", encoding="utf-8")
    check = {
        "scanned_at": datetime.now(UTC).isoformat(),
        "analyst_package_dir": str(analyst_dir),
        "context_patterns": CONTEXT_LEAKAGE_TERMS,
        "persona_patterns": PERSONA_VOCAB_LEAKAGE,
        "pass": True,
        "hits": [],
    }
    (out_dir / "analyst_redaction_check.json").write_text(
        json.dumps(check, indent=2) + "\n", encoding="utf-8"
    )
    return key_path


def enrich_record(rec: RunRecord, bundle: dict[str, Any], *, elapsed: float) -> None:
    final_by_agent = final_support_by_agent(bundle)
    levels = list(final_by_agent.values())
    rec.final_support_mean = round(statistics.mean(levels), 6) if levels else None
    mn, mx, stdev, spread = support_spread_stats(levels)
    rec.final_support_min = mn
    rec.final_support_max = mx
    rec.final_support_stdev = stdev
    rec.final_support_spread = spread
    match, tau = rank_order_metrics(final_by_agent)
    rec.rank_order_match = match
    rec.rank_kendall_tau = tau
    rec.language_reuse_hits = scan_language_reuse(bundle)
    rec.mechanics = extract_mechanics_metrics(bundle=bundle, wall_clock_seconds=elapsed)


def generate_mechanics_markdown(records: list[RunRecord], *, preflight_usd: float) -> str:
    rich_records = [r for r in records if r.source == "rich"]
    lines = [
        "# Persona-rich mechanics report — sq_reading utility test",
        "",
        f"**Date:** 2026-09-11 · **Preflight estimate (per run):** ${preflight_usd:.4f}",
        "",
        "## Live runs (rich personas)",
        "",
        "| Cell | Seed | Status | Final μ | Min | Max | Stdev | Spread | Rank match | τ | Cost USD | Wall s |",
        "|---|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    total_cost = 0.0
    for rec in rich_records:
        m = rec.mechanics
        cost = float(m.get("estimated_cost_usd") or 0.0)
        total_cost += cost
        lines.append(
            f"| {rec.cell} | {rec.seed} | {rec.status} | {rec.final_support_mean} | "
            f"{rec.final_support_min} | {rec.final_support_max} | {rec.final_support_stdev} | "
            f"{rec.final_support_spread} | {rec.rank_order_match} | {rec.rank_kendall_tau} | "
            f"{m.get('estimated_cost_usd')} | {m.get('wall_clock_seconds')} |"
        )
    lines.extend(
        [
            "",
            f"**Rich-run total cost:** ${total_cost:.4f}",
            "",
            "## Pre-specified checks",
            "",
            "### 1. Final-round support spread (within-run, 8 agents)",
            "",
            "Configured starting order (high→low support): "
            + ", ".join(STARTING_SUPPORT_ORDER),
            "",
        ]
    )
    for rec in rich_records:
        lines.append(
            f"- **{rec.cell} s{rec.seed}:** min={rec.final_support_min}, max={rec.final_support_max}, "
            f"stdev={rec.final_support_stdev}, spread={rec.final_support_spread}"
        )
    lines.extend(["", "### 2. Rank order vs configured starting order", ""])
    for rec in rich_records:
        lines.append(
            f"- **{rec.cell} s{rec.seed}:** exact_match={rec.rank_order_match}, "
            f"kendall_tau={rec.rank_kendall_tau}"
        )
    lines.extend(["", "### 3. Language reuse (phrase in ≥3 agents' turns)", ""])
    for rec in rich_records:
        hits = rec.language_reuse_hits or ["(none)"]
        lines.append(f"- **{rec.cell} s{rec.seed}:** {', '.join(hits)}")
    lines.extend(
        [
            "",
            "## Analyst package",
            "",
            "- **Total runs packaged:** 12 (6 rich + 6 Part C no-shock comparators)",
            "",
            "## Gates",
            "",
            "- Preflight ≤ $0.70/run",
            "- Context sentinel (positive/adverse first rich run each)",
            "- Persona sentinel: `Twenty-two years in` in captured prompt",
            "- state_update_source: model_parsed throughout",
            "- network_csv_applied true, no broadcast fallback",
            "- Analyst redaction includes persona vocabulary",
            "",
            "*Mechanics only — no transcript interpretation.*",
        ]
    )
    return "\n".join(lines) + "\n"


def _manifest_row(rec: RunRecord) -> dict[str, Any]:
    return {
        "cell": rec.cell,
        "scenario_id": rec.scenario_id,
        "seed": rec.seed,
        "simulation_id": rec.simulation_id,
        "status": rec.status,
        "source": rec.source,
        "final_support_mean": rec.final_support_mean,
        "final_support_min": rec.final_support_min,
        "final_support_max": rec.final_support_max,
        "final_support_stdev": rec.final_support_stdev,
        "final_support_spread": rec.final_support_spread,
        "rank_order_match": rec.rank_order_match,
        "rank_kendall_tau": rec.rank_kendall_tau,
        "language_reuse_hits": rec.language_reuse_hits,
        "mechanics": rec.mechanics,
    }


def _record_from_manifest_row(row: dict[str, Any]) -> RunRecord:
    return RunRecord(
        cell=str(row["cell"]),
        scenario_id=str(row["scenario_id"]),
        seed=int(row["seed"]),
        simulation_id=str(row["simulation_id"]),
        status=str(row["status"]),
        source=str(row.get("source") or "rich"),
        mechanics=dict(row.get("mechanics") or {}),
        final_support_mean=row.get("final_support_mean"),
        final_support_min=row.get("final_support_min"),
        final_support_max=row.get("final_support_max"),
        final_support_stdev=row.get("final_support_stdev"),
        final_support_spread=row.get("final_support_spread"),
        rank_order_match=row.get("rank_order_match"),
        rank_kendall_tau=row.get("rank_kendall_tau"),
        language_reuse_hits=list(row.get("language_reuse_hits") or []),
    )


def _write_manifest(path: Path, *, records: list[RunRecord], est: float) -> None:
    payload = {
        "harness": "persona-rich-sq-reading",
        "date": "2026-09-11",
        "seeds": list(SEEDS),
        "preflight_estimated_cost_usd": est,
        "runs": [_manifest_row(r) for r in records],
    }
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


async def load_partc_comparators(
    *,
    manifest_path: Path,
    sqlite_path: str,
) -> tuple[list[RunRecord], dict[str, dict[str, Any]]]:
    if not manifest_path.is_file():
        raise FileNotFoundError(f"Part C manifest not found: {manifest_path}")
    prev = json.loads(manifest_path.read_text(encoding="utf-8"))
    records: list[RunRecord] = []
    bundles: dict[str, dict[str, Any]] = {}
    for row in prev.get("runs") or []:
        if str(row.get("cell")) not in PARTC_COMPARATOR_CELLS:
            continue
        bundle = await get_simulation_export_bundle(sqlite_path, simulation_id=str(row["simulation_id"]))
        if bundle is None:
            raise RuntimeError(f"comparator bundle missing for {row['simulation_id']}")
        rec = RunRecord(
            cell=str(row["cell"]),
            scenario_id=str(row["scenario_id"]),
            seed=int(row["seed"]),
            simulation_id=str(row["simulation_id"]),
            status=str(row.get("status") or "completed"),
            source="partc_comparator",
            mechanics=dict(row.get("mechanics") or {}),
            final_support_mean=row.get("final_support_mean"),
            final_support_spread=row.get("final_support_spread"),
        )
        enrich_record(rec, bundle, elapsed=float(rec.mechanics.get("wall_clock_seconds") or 0.0))
        records.append(rec)
        bundles[rec.simulation_id] = bundle
    if len(records) != 6:
        raise RuntimeError(f"expected 6 Part C no-shock comparators, got {len(records)}")
    return records, bundles


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Persona-rich sq_reading utility harness")
    p.add_argument("--study-repo-path", default=str(_REPO_ROOT.parent / "senna-sstrf-study"))
    p.add_argument("--network-csv-rel-path", default=DEFAULT_NETWORK_CSV_REL)
    p.add_argument("--sqlite-path", default=str(_DEFAULT_SQLITE))
    p.add_argument("--out-dir", type=Path, default=_DEFAULT_OUT)
    p.add_argument("--env-file", type=Path, default=_DEFAULT_ENV)
    p.add_argument("--partc-manifest", type=Path, default=_DEFAULT_PARTC_MANIFEST)
    p.add_argument("--partc-sqlite", default="")
    p.add_argument("--execute", action="store_true")
    p.add_argument("--preflight-only", action="store_true")
    p.add_argument("--waive-preflight-gate", action="store_true")
    p.add_argument("--resume", action="store_true")
    p.add_argument(
        "--package-only",
        action="store_true",
        help="Package from persona_rich_manifest.json + Part C comparators (no new runs)",
    )
    return p


async def _main_async(args: argparse.Namespace) -> dict[str, Any]:
    load_backend_env_for_live_runs(args.env_file)
    settings = get_settings()
    sqlite_path = str(Path(args.sqlite_path or settings.sqlite_path).resolve())
    settings.sqlite_path = sqlite_path
    await schema_init(sqlite_path)

    if not args.package_only:
        if abs(settings.llm_temperature - 0.8) > 0.01:
            raise RuntimeError(f"LLM_TEMPERATURE must be 0.8 (got {settings.llm_temperature})")
        if not settings.anthropic_api_key:
            raise RuntimeError("ANTHROPIC_API_KEY not configured in backend/.env")

    print_config_banner(settings)
    study_repo = Path(args.study_repo_path)
    if not study_repo.is_dir():
        raise FileNotFoundError(f"study repo not found: {study_repo}")

    scenario_cfg, _ = await load_scenario_for_run(sqlite_path, "sq_reading_culture_rich")
    persona_ids = [p.persona_id for p in scenario_cfg.personas[:AGENT_LIMIT]]
    expected_ids = frozenset(build_expected_run_agent_ids(persona_ids=persona_ids))
    network_csv, net_parse = load_documented_network_csv(
        study_repo_path=study_repo,
        rel_path=args.network_csv_rel_path,
        expected_agent_ids=expected_ids,
    )
    print(f"[persona-rich] network CSV: {len(net_parse.edges)} edges", flush=True)

    req = build_request(scenario_id="sq_reading_culture_rich", seed=SEEDS[0], network_csv=network_csv)
    preflight = await build_preflight_response(settings, req)
    est = float((preflight.preflight or {}).get("estimated_cost_usd") or 0.0)
    print(f"[persona-rich] preflight estimated_cost_usd={est:.4f}", flush=True)

    if args.preflight_only or (not args.execute and not args.package_only):
        return {
            "status": "preflight_ok",
            "estimated_cost_usd": est,
            "planned_runs": len(CELLS) * len(SEEDS),
        }

    if est > PREFLIGHT_COST_CAP_USD and not args.package_only:
        msg = f"PREFLIGHT GATE: ${est:.4f}/run exceeds cap ${PREFLIGHT_COST_CAP_USD:.2f}"
        if not args.waive_preflight_gate:
            raise RuntimeError(msg)
        print(f"[persona-rich] WARNING: {msg} — waived under GM EXECUTE", flush=True)

    partc_sqlite = args.partc_sqlite or str(_REPO_ROOT / "backend/data/sq_reading_partc_fresh.sqlite")
    manifest_path = args.out_dir / "persona_rich_manifest.json"
    args.out_dir.mkdir(parents=True, exist_ok=True)

    if args.package_only:
        if not manifest_path.is_file():
            raise FileNotFoundError(f"missing {manifest_path}")
        prev = json.loads(manifest_path.read_text(encoding="utf-8"))
        rich_records = [_record_from_manifest_row(row) for row in prev.get("runs") or []]
        if len(rich_records) != len(CELLS) * len(SEEDS):
            raise RuntimeError(f"expected 6 rich runs in manifest, got {len(rich_records)}")
        bundles: dict[str, dict[str, Any]] = {}
        for rec in rich_records:
            bundle = await get_simulation_export_bundle(sqlite_path, simulation_id=rec.simulation_id)
            if bundle is None:
                raise RuntimeError(f"missing bundle for {rec.simulation_id}")
            bundles[rec.simulation_id] = bundle
        comp_records, comp_bundles = await load_partc_comparators(
            manifest_path=args.partc_manifest,
            sqlite_path=partc_sqlite,
        )
        all_records = rich_records + comp_records
        all_bundles = {**bundles, **comp_bundles}
        md_path = args.out_dir / "PERSONA_RICH_MECHANICS_REPORT.md"
        md_path.write_text(generate_mechanics_markdown(rich_records, preflight_usd=est), encoding="utf-8")
        key_path = package_for_analyst(all_records, all_bundles, args.out_dir)
        print(f"[persona-rich] analyst key: {key_path}", flush=True)
        return {"status": "packaged", "run_count": len(all_records)}

    from run_sq_reading_partc import assert_anthropic_key_from_backend_env  # noqa: WPS433

    await assert_anthropic_key_from_backend_env(settings)
    print("[persona-rich] Anthropic API key OK", flush=True)

    exports_dir = args.out_dir / "exports"
    exports_dir.mkdir(parents=True, exist_ok=True)
    records: list[RunRecord] = []
    bundles: dict[str, dict[str, Any]] = {}
    sentinel_done: set[str] = set()
    done_pairs: set[tuple[str, int]] = set()

    if args.resume and manifest_path.is_file():
        prev = json.loads(manifest_path.read_text(encoding="utf-8"))
        for row in prev.get("runs") or []:
            rec = _record_from_manifest_row(row)
            records.append(rec)
            done_pairs.add((rec.cell, rec.seed))
            bundle = await get_simulation_export_bundle(sqlite_path, simulation_id=rec.simulation_id)
            if bundle is None:
                raise RuntimeError(f"resume: missing bundle for {rec.simulation_id}")
            bundles[rec.simulation_id] = bundle
            valence = "positive" if rec.cell.startswith("positive") else "adverse"
            if rec.seed == SEEDS[0]:
                sentinel_done.add(valence)
        print(f"[persona-rich] resume: {len(done_pairs)} runs complete", flush=True)

    for cell, scenario_id in CELLS:
        valence = "positive" if cell.startswith("positive") else "adverse"
        for seed in SEEDS:
            if (cell, seed) in done_pairs:
                continue
            t0 = time.perf_counter()
            run_req = build_request(scenario_id=scenario_id, seed=seed, network_csv=network_csv)
            resp = await queue_simulation_run(
                settings,
                run_req,
                run_display_name=f"persona-rich-{cell}-s{seed}",
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
                prompt = capture_system_prompt(bundle)
                assert_context_sentinel(prompt, valence=valence, scenario_id=scenario_id, seed=seed)
                assert_persona_sentinel(bundle, scenario_id=scenario_id, seed=seed)
                sentinel_done.add(valence)
                print(f"[persona-rich] SENTINEL PASS ({valence} context + persona)", flush=True)

            rec = RunRecord(
                cell=cell,
                scenario_id=scenario_id,
                seed=seed,
                simulation_id=resp.id,
                status=str(terminal.get("status") or ""),
                source="rich",
            )
            enrich_record(rec, bundle, elapsed=elapsed)
            records.append(rec)
            bundles[resp.id] = bundle
            (exports_dir / f"{resp.id}.zip").write_bytes(build_export_zip(bundle))
            print(
                json.dumps(
                    {
                        "cell": cell,
                        "seed": seed,
                        "simulation_id": resp.id,
                        "spread": rec.final_support_spread,
                        "rank_match": rec.rank_order_match,
                        "cost_usd": rec.mechanics.get("estimated_cost_usd"),
                    }
                ),
                flush=True,
            )
            _write_manifest(manifest_path, records=records, est=est)

    _write_manifest(manifest_path, records=records, est=est)
    comp_records, comp_bundles = await load_partc_comparators(
        manifest_path=args.partc_manifest,
        sqlite_path=partc_sqlite,
    )
    all_records = records + comp_records
    all_bundles = {**bundles, **comp_bundles}
    md_path = args.out_dir / "PERSONA_RICH_MECHANICS_REPORT.md"
    md_path.write_text(generate_mechanics_markdown(records, preflight_usd=est), encoding="utf-8")
    key_path = package_for_analyst(all_records, all_bundles, args.out_dir)
    print(f"[persona-rich] analyst key: {key_path}", flush=True)
    return {"status": "completed", "run_count": len(all_records)}


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        payload = asyncio.run(_main_async(args))
    except (ValueError, RuntimeError, FileNotFoundError, TimeoutError) as exc:
        print(f"\n[persona-rich] FAILED: {exc}\n", file=sys.stderr)
        return 1
    print(json.dumps(payload))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

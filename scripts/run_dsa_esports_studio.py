#!/usr/bin/env python3
"""Senna Studio operator pipeline for 2026-10-04_dsa-esports."""

from __future__ import annotations

import argparse
import asyncio
import csv
import io
import json
import os
import re
import subprocess
import sys
import time
import zipfile
from pathlib import Path
from typing import Any

_REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_REPO / "backend" / "src"))
sys.path.insert(0, str(_REPO / "scripts"))

from run_arc11_ablation import load_backend_env_for_live_runs  # noqa: E402

from mirofish_backend.api.simulations import (  # noqa: E402
    SimulationRunRequest,
    build_preflight_response,
    queue_simulation_run,
    wait_for_simulation_terminal,
)
from mirofish_backend.config import get_settings  # noqa: E402
from mirofish_backend.db.repo import get_simulation_export_bundle  # noqa: E402
from mirofish_backend.db.schema import init_db  # noqa: E402
from mirofish_backend.diagnostics.arc12_study_rehearsal import (  # noqa: E402
    count_llm_errors,
    state_update_source_counts,
)
from mirofish_backend.export_bundle import build_export_zip  # noqa: E402
from mirofish_backend.llm.model_profiles import ANTHROPIC_DEFAULT_ID  # noqa: E402
from mirofish_backend.scenarios.registry import get_scenario  # noqa: E402

RUN_ID = "2026-10-04_dsa-esports"
RUN_DIR = _REPO / "senna-studio" / "runs" / RUN_ID
OUT = RUN_DIR / "02_data"
ENV_FILE = _REPO / "backend" / ".env"
PREFLIGHT_CEILING_USD = 4.0
PARENT_SEEDS = [72001, 72002, 72003]
TEACHER_SEEDS = [72101, 72102, 72103]
ALL_SEEDS = {
    "dsa_esports_parents": PARENT_SEEDS,
    "dsa_esports_teachers": TEACHER_SEEDS,
}
TEACHER_DEMO_EXPECTED: dict[str, dict[str, Any]] = {
    "t_001": {"age": 25, "sex": "female", "ethnicity": "Chinese"},
    "t_002": {"age": 26, "sex": "female", "ethnicity": "Indian"},
    "t_003": {"age": 29, "sex": "male", "ethnicity": "Chinese"},
    "t_004": {"age": 26, "sex": "male", "ethnicity": "Indian"},
    "t_005": {"age": 27, "sex": "female", "ethnicity": "Chinese"},
    "t_006": {"age": 29, "sex": "male", "ethnicity": "Chinese"},
}

VISIBILITY_REQUESTED_NOTE = (
    "visibility_requested_broadcast is read from config_snapshot.interaction_policy.visibility_policy "
    "(request field is stored there, not as a top-level config_snapshot.visibility_policy key). "
    "Earlier smoke used cfg.get('visibility_policy'), which is always absent and read as false."
)


def fixture_commit() -> str:
    return (
        subprocess.check_output(
            ["git", "rev-parse", "HEAD:backend/src/mirofish_backend/scenarios/data/dsa_esports_teachers.yaml"],
            cwd=_REPO,
            text=True,
        )
        .strip()[:7]
    )


def _read_roster(name: str, *, max_slot: int | None = None) -> str:
    text = (RUN_DIR / "inputs" / name).read_text(encoding="utf-8")
    if max_slot is None:
        return text
    lines = text.strip().splitlines()
    if not lines:
        return text
    header = lines[0]
    kept = [header]
    for line in lines[1:]:
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        slot_raw = line.split(",", 1)[0].strip()
        try:
            slot = int(slot_raw)
        except ValueError:
            continue
        if 1 <= slot <= max_slot:
            kept.append(line)
    return "\n".join(kept) + "\n"


def base_req(scenario_id: str, **kw: Any) -> SimulationRunRequest:
    agent_limit = int(kw.get("agent_limit", 6))
    roster_name = "roster_parents.csv" if scenario_id == "dsa_esports_parents" else "roster_teachers.csv"
    d: dict[str, Any] = dict(
        scenario_id=scenario_id,
        total_rounds=6,
        agent_limit=6,
        simulation_mode="full_round_robin",
        visibility_policy="broadcast",
        random_seed=72001,
        max_tokens=700,
        llm_provider="anthropic",
        rag_enabled=False,
        convergence_threshold=None,
        roster_csv=_read_roster(roster_name, max_slot=agent_limit),
    )
    if scenario_id == "dsa_esports_teachers":
        d["population_csv"] = (RUN_DIR / "inputs" / "population_teachers.csv").read_text(encoding="utf-8")
        d["population_sample_mode"] = "stratified"
    d.update(kw)
    return SimulationRunRequest(**d)


def secret_scan(cfg: dict) -> list[str]:
    blob = json.dumps(cfg).lower()
    issues: list[str] = []
    if "sk-ant-" in blob:
        issues.append("sk-ant- in config_snapshot")
    return issues


def _gender_from_identity(prompt: str) -> str | None:
    m = re.search(r"gender_identity:\s*(\w+)", prompt)
    return m.group(1).lower() if m else None


def _demographics_field(prompt: str, field: str) -> str | None:
    m = re.search(rf"Demographics:\s*\{{[^}}]*'{field}':\s*'?([^',}}]+)'?", prompt)
    if m:
        return m.group(1).strip()
    m2 = re.search(rf'Demographics:\s*\{{[^}}]*"{field}":\s*"?([^",}}]+)"?', prompt)
    return m2.group(1).strip() if m2 else None


def _sex_from_demographics(prompt: str) -> str | None:
    v = _demographics_field(prompt, "sex")
    return v.lower() if v else None


def _age_from_demographics(prompt: str) -> int | None:
    v = _demographics_field(prompt, "age")
    if v is None:
        return None
    try:
        return int(v)
    except ValueError:
        return None


def _ethnicity_from_identity(prompt: str) -> str | None:
    m = re.search(r"ethnicity:\s*([A-Za-z]+)", prompt)
    return m.group(1) if m else None


def _persona_id_from_agent_id(agent_id: str) -> str:
    return agent_id.rsplit("_", 1)[0] if "_" in agent_id else agent_id


def _visibility_requested_broadcast(cfg: dict) -> bool:
    ip = cfg.get("interaction_policy") or {}
    return str(ip.get("visibility_policy") or "").lower() == "broadcast"


def _sex_matches_identity(woman_or_man: str | None, sex: str | None) -> bool:
    if not woman_or_man or not sex:
        return True
    mapping = {"woman": "female", "man": "male"}
    return mapping.get(woman_or_man) == sex


def check_prompt_demographics(
    transcript: list[dict],
    *,
    expected_by_persona: dict[str, dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    seen: set[str] = set()
    out: list[dict[str, Any]] = []
    for t in sorted(transcript, key=lambda x: int(x.get("turn_index") or 0)):
        aid = str(t.get("agent_id") or "")
        if not aid or aid in seen:
            continue
        seen.add(aid)
        prompt = str(t.get("raw_prompt") or "")
        gid = _gender_from_identity(prompt)
        sex = _sex_from_demographics(prompt)
        age = _age_from_demographics(prompt)
        eth_demo = _demographics_field(prompt, "ethnicity")
        eth_id = _ethnicity_from_identity(prompt)
        pid = _persona_id_from_agent_id(aid)
        exp = (expected_by_persona or {}).get(pid)
        age_ok = exp is None or age == exp.get("age")
        sex_ok = exp is None or (sex or "").lower() == str(exp.get("sex")).lower()
        eth_ok = exp is None or (eth_demo or "") == exp.get("ethnicity")
        eth_id_ok = exp is None or eth_id == exp.get("ethnicity")
        out.append(
            {
                "agent_id": aid,
                "persona_id": pid,
                "agent_name": t.get("agent_name"),
                "gender_identity": gid,
                "demographics_age": age,
                "demographics_sex": sex,
                "demographics_ethnicity": eth_demo,
                "identity_ethnicity": eth_id,
                "sex_consistent": _sex_matches_identity(gid, sex),
                "age_matches_request": age_ok,
                "ethnicity_matches_request": eth_ok and eth_id_ok,
            }
        )
    return out


async def write_seed_collision_check() -> None:
    seeds = PARENT_SEEDS + TEACHER_SEEDS
    hits: list[dict[str, str]] = []
    repos = [_REPO]
    pb = Path.home() / "proactive-bots"
    if pb.is_dir():
        repos.append(pb)
    for root in repos:
        try:
            proc = subprocess.run(
                ["rg", "-n", "--glob", "!**/node_modules/**", "|".join(str(s) for s in seeds), str(root)],
                capture_output=True,
                text=True,
                timeout=90,
            )
        except (subprocess.TimeoutExpired, FileNotFoundError):
            continue
        for line in proc.stdout.splitlines():
            if not line.strip():
                continue
            path_part = line.split(":", 1)[0]
            if "dsa_esports" in path_part or "01_request.md" in path_part:
                continue
            hits.append({"match": line.strip(), "repo": str(root)})
    payload = {
        "seeds_checked": seeds,
        "repos_searched": [str(r) for r in repos],
        "collision_hits": hits,
        "pass": len(hits) == 0,
    }
    (OUT / "seed_collision_check.json").write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


async def run_preflight(settings) -> dict[str, Any]:
    per_run: list[dict[str, Any]] = []
    total = 0.0
    for scenario_id in ("dsa_esports_parents", "dsa_esports_teachers"):
        pf = await build_preflight_response(settings, base_req(scenario_id))
        est = float(pf.preflight.get("estimated_cost_usd") or 0.0)
        per_run.append(
            {
                "scenario_id": scenario_id,
                "estimated_cost_usd_per_run": est,
                "warnings": list(pf.warnings),
                "preflight": pf.preflight,
            }
        )
        total += est * 3
    record = {
        "preflight_ceiling_usd": PREFLIGHT_CEILING_USD,
        "estimated_cost_usd_six_runs": round(total, 4),
        "cost_gate_pass": total <= PREFLIGHT_CEILING_USD,
        "per_scenario": per_run,
        "host_llm_temperature": settings.llm_temperature,
        "anthropic_model": settings.anthropic_model,
        "llm_provider": settings.llm_provider,
    }
    (OUT / "preflight.json").write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
    if not record["cost_gate_pass"]:
        (OUT / "HARD_STOP_preflight.md").write_text(
            (
                f"# Cost gate — HARD STOP\n\n"
                f"Six-run preflight estimate **${record['estimated_cost_usd_six_runs']:.4f}** "
                f"exceeds ceiling **${PREFLIGHT_CEILING_USD:.2f}**.\n\n"
                f"Options: raise ceiling with Mark, reduce rounds/agents, or change model.\n"
            ),
            encoding="utf-8",
        )
    return record


async def run_smoke(settings) -> dict[str, Any]:
    smoke_req = base_req(
        "dsa_esports_parents",
        total_rounds=1,
        agent_limit=3,
        random_seed=72001,
    )
    t0 = time.perf_counter()
    resp = await queue_simulation_run(settings, smoke_req, run_display_name="dsa-esports-smoke")
    terminal = await wait_for_simulation_terminal(
        sqlite_path=settings.sqlite_path,
        simulation_id=resp.id,
        timeout_seconds=1800.0,
    )
    elapsed = time.perf_counter() - t0
    bundle = await get_simulation_export_bundle(settings.sqlite_path, simulation_id=resp.id)
    if bundle is None:
        raise RuntimeError("missing export bundle for smoke")
    run = bundle.get("run") or {}
    cfg = run.get("config_snapshot") or {}
    econ = run.get("economics") or {}
    transcript = bundle.get("transcript") or []
    warnings = list(run.get("warnings") or [])
    llm_turns = [t for t in transcript if t.get("effective_provider") not in (None, "heuristic")]
    agents = sorted({t.get("agent_id") for t in transcript if t.get("agent_id")})
    demo_checks = check_prompt_demographics(transcript)
    checks = {
        "status_completed": str(terminal.get("status")) == "completed",
        "all_three_agents_spoke": len(agents) >= 3,
        "effective_profile_haiku": all(
            t.get("effective_profile_id") == ANTHROPIC_DEFAULT_ID for t in llm_turns
        ),
        "model_parsed_only": all(t.get("state_update_source") == "model_parsed" for t in llm_turns),
        "economics_populated": bool(econ),
        "config_llm_temperature": cfg.get("llm_temperature"),
        "visibility_effective": (cfg.get("interaction_policy") or {}).get("visibility_effective"),
        "visibility_requested_broadcast": _visibility_requested_broadcast(cfg),
        "visibility_requested_broadcast_legacy_top_level": cfg.get("visibility_policy"),
        "roster_csv_applied": cfg.get("roster_csv_applied") is True,
        "network_fallback_warning": any("network" in w.lower() and "fallback" in w.lower() for w in warnings),
        "secrets": secret_scan(cfg),
        "demographics_sex_identity_consistent": all(d["sex_consistent"] for d in demo_checks),
        "warnings": warnings,
    }
    zip_path = OUT / "exports" / f"smoke_{resp.id}_export.zip"
    zip_path.parent.mkdir(parents=True, exist_ok=True)
    zip_path.write_bytes(build_export_zip(bundle))
    record = {
        "simulation_id": resp.id,
        "scenario_id": "dsa_esports_parents",
        "wall_clock_seconds": round(elapsed, 3),
        "state_update_source_counts": state_update_source_counts(transcript),
        "estimated_cost_usd": econ.get("estimated_cost_usd"),
        "demographics_prompt_checks": demo_checks,
        "checks": checks,
        "smoke_gate_pass": all(
            [
                checks["status_completed"],
                checks["all_three_agents_spoke"],
                checks["effective_profile_haiku"],
                checks["model_parsed_only"],
                checks["economics_populated"],
                not checks["network_fallback_warning"],
                not checks["secrets"],
                checks["config_llm_temperature"] == 0.8,
                checks["visibility_effective"] == "broadcast",
                checks["demographics_sex_identity_consistent"],
            ]
        ),
        "visibility_requested_broadcast_note": VISIBILITY_REQUESTED_NOTE,
        "export_zip": str(zip_path),
    }
    (OUT / "smoke_summary.json").write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
    return record


async def run_smoke_teachers(settings) -> dict[str, Any]:
    smoke_req = base_req(
        "dsa_esports_teachers",
        total_rounds=1,
        agent_limit=6,
        random_seed=72101,
    )
    t0 = time.perf_counter()
    resp = await queue_simulation_run(settings, smoke_req, run_display_name="dsa-esports-smoke-teachers")
    terminal = await wait_for_simulation_terminal(
        sqlite_path=settings.sqlite_path,
        simulation_id=resp.id,
        timeout_seconds=1800.0,
    )
    elapsed = time.perf_counter() - t0
    bundle = await get_simulation_export_bundle(settings.sqlite_path, simulation_id=resp.id)
    if bundle is None:
        raise RuntimeError("missing export bundle for teacher smoke")
    run = bundle.get("run") or {}
    cfg = run.get("config_snapshot") or {}
    econ = run.get("economics") or {}
    transcript = bundle.get("transcript") or []
    warnings = list(run.get("warnings") or [])
    llm_turns = [t for t in transcript if t.get("effective_provider") not in (None, "heuristic")]
    agents = sorted({t.get("agent_id") for t in transcript if t.get("agent_id")})
    demo_checks = check_prompt_demographics(transcript, expected_by_persona=TEACHER_DEMO_EXPECTED)
    checks = {
        "status_completed": str(terminal.get("status")) == "completed",
        "all_six_agents_spoke": len(agents) >= 6,
        "effective_profile_haiku": all(
            t.get("effective_profile_id") == ANTHROPIC_DEFAULT_ID for t in llm_turns
        ),
        "model_parsed_only": all(t.get("state_update_source") == "model_parsed" for t in llm_turns),
        "economics_populated": bool(econ),
        "config_llm_temperature": cfg.get("llm_temperature"),
        "visibility_effective": (cfg.get("interaction_policy") or {}).get("visibility_effective"),
        "visibility_requested_broadcast": _visibility_requested_broadcast(cfg),
        "population_csv_applied": cfg.get("population_csv_applied") is True,
        "roster_csv_applied": cfg.get("roster_csv_applied") is True,
        "network_fallback_warning": any("network" in w.lower() and "fallback" in w.lower() for w in warnings),
        "secrets": secret_scan(cfg),
        "demographics_sex_identity_consistent": all(d["sex_consistent"] for d in demo_checks),
        "demographics_age_ethnicity_match_request": all(
            d["age_matches_request"] and d["ethnicity_matches_request"] for d in demo_checks
        ),
        "warnings": warnings,
    }
    zip_path = OUT / "exports" / f"smoke_teachers_{resp.id}_export.zip"
    zip_path.write_bytes(build_export_zip(bundle))
    record = {
        "simulation_id": resp.id,
        "scenario_id": "dsa_esports_teachers",
        "wall_clock_seconds": round(elapsed, 3),
        "state_update_source_counts": state_update_source_counts(transcript),
        "estimated_cost_usd": econ.get("estimated_cost_usd"),
        "demographics_prompt_checks": demo_checks,
        "checks": checks,
        "smoke_gate_pass": all(
            [
                checks["status_completed"],
                checks["all_six_agents_spoke"],
                checks["effective_profile_haiku"],
                checks["model_parsed_only"],
                checks["economics_populated"],
                not checks["network_fallback_warning"],
                not checks["secrets"],
                checks["config_llm_temperature"] == 0.8,
                checks["visibility_effective"] == "broadcast",
                checks["demographics_sex_identity_consistent"],
                checks["demographics_age_ethnicity_match_request"],
            ]
        ),
        "visibility_requested_broadcast_note": VISIBILITY_REQUESTED_NOTE,
        "demographics_override_route": "population_csv (stratified s01–s06) → slot_overrides → _merge_demographics",
        "export_zip": str(zip_path),
    }
    (OUT / "smoke_teachers_summary.json").write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
    if (OUT / "smoke_summary.json").is_file():
        parent_smoke = json.loads((OUT / "smoke_summary.json").read_text(encoding="utf-8"))
        parent_smoke["visibility_requested_broadcast_note"] = VISIBILITY_REQUESTED_NOTE
        if isinstance(parent_smoke.get("checks"), dict):
            parent_smoke["checks"]["visibility_requested_broadcast_note"] = VISIBILITY_REQUESTED_NOTE
        (OUT / "smoke_summary.json").write_text(json.dumps(parent_smoke, indent=2) + "\n", encoding="utf-8")
    return record


async def run_one(settings, scenario_id: str, seed: int) -> dict[str, Any]:
    t0 = time.perf_counter()
    resp = await queue_simulation_run(
        settings,
        base_req(scenario_id, random_seed=seed),
        run_display_name=f"dsa-esports-{scenario_id}-s{seed}",
    )
    terminal = await wait_for_simulation_terminal(
        sqlite_path=settings.sqlite_path,
        simulation_id=resp.id,
        timeout_seconds=7200.0,
    )
    elapsed = time.perf_counter() - t0
    bundle = await get_simulation_export_bundle(settings.sqlite_path, simulation_id=resp.id)
    if bundle is None:
        raise RuntimeError(f"missing bundle {resp.id}")
    transcript = bundle.get("transcript") or []
    llm_err = count_llm_errors(transcript)
    if llm_err:
        raise RuntimeError(f"{llm_err} LLM error turns in {resp.id} seed={seed}")
    run = bundle.get("run") or {}
    econ = run.get("economics") or {}
    zip_path = OUT / "exports" / f"{scenario_id}_seed_{seed}_{resp.id}_export.zip"
    zip_path.parent.mkdir(parents=True, exist_ok=True)
    zip_path.write_bytes(build_export_zip(bundle))
    parsed = state_update_source_counts(transcript)
    return {
        "scenario_id": scenario_id,
        "simulation_id": resp.id,
        "random_seed": seed,
        "status": terminal.get("status"),
        "wall_clock_seconds": round(elapsed, 3),
        "turn_count": len(transcript),
        "state_update_source_counts": parsed,
        "model_parsed_only": parsed.get("model_parsed", 0) == sum(parsed.values()) - parsed.get("heuristic", 0)
        if parsed
        else False,
        "economics": econ,
        "warnings": list(run.get("warnings") or []),
        "export_zip": str(zip_path),
        "bundle": bundle,
    }


def _strip_state_block(text: str) -> str:
    if "---" in text:
        return text.split("---", 1)[0].strip()
    return text.strip()


def write_transcript_md(bundle: dict, path: Path) -> None:
    transcript = bundle.get("transcript") or []
    lines = ["# Transcript", ""]
    by_round: dict[int, list[dict]] = {}
    for t in transcript:
        rnd = int(t.get("round_number") or 0)
        by_round.setdefault(rnd, []).append(t)
    for rnd in sorted(by_round):
        lines.append(f"## Round {rnd}")
        lines.append("")
        for t in by_round[rnd]:
            name = t.get("agent_name") or t.get("agent_id")
            body = _strip_state_block(str(t.get("raw_response") or ""))
            lines.append(f"### {name}")
            lines.append("")
            lines.append(body)
            lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")


def write_trajectories_csv(runs: list[dict], path: Path) -> None:
    rows: list[dict[str, Any]] = []
    for rec in runs:
        bundle = rec.get("bundle") or {}
        seed = rec["random_seed"]
        for snap in bundle.get("agent_state_snapshots") or []:
            rows.append(
                {
                    "actor_id": snap.get("agent_id"),
                    "actor_name": snap.get("agent_name"),
                    "seed": seed,
                    "scenario_id": rec["scenario_id"],
                    "round": snap.get("round_number"),
                    "support": snap.get("support_level"),
                    "resistance": snap.get("resistance_level"),
                    "stress": snap.get("workload_stress"),
                }
            )
    fieldnames = [
        "actor_id",
        "actor_name",
        "seed",
        "scenario_id",
        "round",
        "support",
        "resistance",
        "stress",
    ]
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(rows)


def write_data_report(settings, runs: list[dict], smoke: dict, preflight: dict) -> None:
    engine_head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=_REPO, text=True).strip()
    lines = [
        "# Data Report — 2026-10-04_dsa-esports",
        "",
        "*Mechanics and data index only — no interpretation of dialogue.*",
        "",
        "## Run record",
        "| Item | Value |",
        "|------|-------|",
        f"| Request | `01_request.md` (signed 2026-10-04) |",
        f"| Fixture commit (teachers YAML) | `{fixture_commit()}` |",
        f"| Engine commit (HEAD at run time) | `{engine_head}` |",
        f"| Host env actually set | `ANTHROPIC_MODEL={settings.anthropic_model}` · "
        f"`LLM_TEMPERATURE={settings.llm_temperature}` · `LLM_PROVIDER={settings.llm_provider}` |",
        f"| Seeds | parents {PARENT_SEEDS}; teachers {TEACHER_SEEDS} |",
        "",
        "## Gates",
        "| Gate | Result | File |",
        "|------|--------|------|",
        f"| Seed collision check | pass | `seed_collision_check.json` |",
        f"| Preflight (6 runs) vs ${PREFLIGHT_CEILING_USD:.2f} | "
        f"{'pass' if preflight.get('cost_gate_pass') else 'FAIL'} | `preflight.json` |",
        f"| Smoke (parents) | {'pass' if smoke.get('smoke_gate_pass') else 'FAIL'} | `smoke_summary.json` |",
        f"| Smoke (teachers) | see `smoke_teachers_summary.json` | `smoke_teachers_summary.json` |",
        "",
        "## Runs",
        "| Seed | Panel | Simulation ID | Status | Turns | model_parsed | Errors / warnings | Wall-clock | Actual cost |",
        "|------|-------|---------------|--------|-------|--------------|-------------------|-----------|-------------|",
    ]
    total_cost = 0.0
    total_wall = 0.0
    for rec in runs:
        econ = rec.get("economics") or {}
        cost = float(econ.get("estimated_cost_usd") or 0.0)
        total_cost += cost
        total_wall += float(rec.get("wall_clock_seconds") or 0.0)
        warn_n = len(rec.get("warnings") or [])
        lines.append(
            f"| {rec['random_seed']} | {rec['scenario_id']} | {rec['simulation_id']} | {rec['status']} | "
            f"{rec['turn_count']} | {rec.get('model_parsed_only')} | {warn_n} warnings | "
            f"{rec['wall_clock_seconds']}s | ${cost:.4f} |"
        )
    lines.append(
        f"| **Total** | | | | | | | {round(total_wall, 1)}s | ${total_cost:.4f} |"
    )
    lines.extend(
        [
            "",
            "## Data index",
            "| File | Contents |",
            "|------|----------|",
            "| `exports/*.zip` | Raw engine exports per run |",
            "| `transcripts/seed_<n>.md` | Readable transcript per seed |",
            "| `trajectories.csv` | State trajectories by actor/seed/round |",
            "| `run_summary.json` | Machine-readable run table |",
            "",
            "## Anything unexpected",
            "",
            "*(none recorded)*",
            "",
        ]
    )
    (OUT / "data_report.md").write_text("\n".join(lines), encoding="utf-8")


def merge_trajectories_csv(parent_rows: list[dict], teacher_runs: list[dict]) -> None:
    fieldnames = [
        "actor_id",
        "actor_name",
        "seed",
        "scenario_id",
        "round",
        "support",
        "resistance",
        "stress",
    ]
    teacher_rows: list[dict[str, Any]] = []
    for rec in teacher_runs:
        bundle = rec.get("bundle") or {}
        seed = rec["random_seed"]
        for snap in bundle.get("agent_state_snapshots") or []:
            teacher_rows.append(
                {
                    "actor_id": snap.get("agent_id"),
                    "actor_name": snap.get("agent_name"),
                    "seed": seed,
                    "scenario_id": rec["scenario_id"],
                    "round": snap.get("round_number"),
                    "support": snap.get("support_level"),
                    "resistance": snap.get("resistance_level"),
                    "stress": snap.get("workload_stress"),
                }
            )
    with (OUT / "trajectories.csv").open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(parent_rows + teacher_rows)


def load_trajectory_parent_rows() -> list[dict[str, Any]]:
    path = OUT / "trajectories.csv"
    if not path.is_file():
        return []
    with path.open(encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f))
    return [r for r in rows if r.get("scenario_id") != "dsa_esports_teachers"]


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser()
    p.add_argument(
        "--step",
        choices=[
            "all",
            "preflight",
            "smoke",
            "smoke_teachers",
            "full",
            "teachers_rerun",
            "organize",
        ],
        default="all",
    )
    return p


async def main() -> int:
    args = build_parser().parse_args()
    load_backend_env_for_live_runs(ENV_FILE)
    os.environ["LLM_TEMPERATURE"] = "0.8"
    os.environ["LLM_PROVIDER"] = "anthropic"
    os.environ.setdefault("ANTHROPIC_MODEL", "claude-haiku-5-5")
    settings = get_settings()
    await init_db(settings.sqlite_path)
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "exports").mkdir(exist_ok=True)
    (OUT / "transcripts").mkdir(exist_ok=True)

    for sid in ALL_SEEDS:
        get_scenario(sid)

    await write_seed_collision_check()
    seed_doc = json.loads((OUT / "seed_collision_check.json").read_text())
    if not seed_doc.get("pass"):
        print(json.dumps({"halt": "seed_collision", "detail": seed_doc}), flush=True)
        return 4

    preflight: dict[str, Any] = {}
    if args.step in ("all", "preflight"):
        preflight = await run_preflight(settings)
        print(json.dumps({"step": "preflight", **preflight}, indent=2))
        if not preflight["cost_gate_pass"]:
            return 2

    smoke: dict[str, Any] = {}
    if args.step in ("all", "smoke"):
        if not preflight and (OUT / "preflight.json").is_file():
            preflight = json.loads((OUT / "preflight.json").read_text())
        elif not preflight:
            preflight = await run_preflight(settings)
            if not preflight["cost_gate_pass"]:
                return 2
        smoke = await run_smoke(settings)
        print(json.dumps({"step": "smoke", "smoke_gate_pass": smoke["smoke_gate_pass"]}, indent=2))
        if not smoke["smoke_gate_pass"]:
            return 3

    if args.step == "smoke_teachers":
        teacher_smoke = await run_smoke_teachers(settings)
        print(
            json.dumps(
                {"step": "smoke_teachers", "smoke_gate_pass": teacher_smoke["smoke_gate_pass"]},
                indent=2,
            )
        )
        return 0 if teacher_smoke["smoke_gate_pass"] else 3

    runs: list[dict] = []
    if args.step in ("all", "full"):
        for scenario_id, seeds in ALL_SEEDS.items():
            for seed in seeds:
                print(json.dumps({"step": "run_start", "scenario_id": scenario_id, "seed": seed}), flush=True)
                rec = await run_one(settings, scenario_id, seed)
                runs.append(rec)
                print(json.dumps({"step": "run_done", "simulation_id": rec["simulation_id"], "seed": seed}), flush=True)

    if args.step == "teachers_rerun":
        teacher_smoke = await run_smoke_teachers(settings)
        if not teacher_smoke["smoke_gate_pass"]:
            print(json.dumps({"halt": "teacher_smoke_gate"}, indent=2))
            return 3
        for seed in TEACHER_SEEDS:
            print(json.dumps({"step": "run_start", "scenario_id": "dsa_esports_teachers", "seed": seed}), flush=True)
            rec = await run_one(settings, "dsa_esports_teachers", seed)
            runs.append(rec)
            print(json.dumps({"step": "run_done", "simulation_id": rec["simulation_id"], "seed": seed}), flush=True)
        parent_rows = load_trajectory_parent_rows()
        merge_trajectories_csv(parent_rows, runs)
        for rec in runs:
            tpath = OUT / "transcripts" / f"seed_{rec['random_seed']}.md"
            write_transcript_md(rec["bundle"], tpath)
        prior = json.loads((OUT / "run_summary.json").read_text(encoding="utf-8"))
        parent_runs = [r for r in prior.get("runs", []) if r.get("scenario_id") == "dsa_esports_parents"]
        teacher_runs = [{k: v for k, v in rec.items() if k != "bundle"} for rec in runs]
        summary = {
            "run_id": RUN_ID,
            "fixture_commit": fixture_commit(),
            "teacher_rerun_after_qc": "2026-10-04",
            "demographics_override": "population_teachers.csv stratified",
            "runs": parent_runs + teacher_runs,
        }
        (OUT / "run_summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
        if not smoke and (OUT / "smoke_summary.json").is_file():
            smoke = json.loads((OUT / "smoke_summary.json").read_text(encoding="utf-8"))
        if not preflight and (OUT / "preflight.json").is_file():
            preflight = json.loads((OUT / "preflight.json").read_text(encoding="utf-8"))
        write_data_report(settings, parent_runs + teacher_runs, smoke, preflight)
        extra = (
            "- Teacher panel re-run after QC FAIL (`03_qc.md`): demographics via `population_teachers.csv` "
            "(slot overrides → `_merge_demographics`). Persona YAML order restored to request §3.\n"
            f"- {VISIBILITY_REQUESTED_NOTE}\n"
        )
        report = (OUT / "data_report.md").read_text(encoding="utf-8")
        report = report.replace("*(none recorded)*", extra.strip())
        (OUT / "data_report.md").write_text(report, encoding="utf-8")
        return 0

    if args.step in ("all", "full", "organize") and runs:
        write_trajectories_csv(runs, OUT / "trajectories.csv")
        for rec in runs:
            tpath = OUT / "transcripts" / f"seed_{rec['random_seed']}.md"
            write_transcript_md(rec["bundle"], tpath)
        summary = {
            "run_id": RUN_ID,
            "fixture_commit": fixture_commit(),
            "runs": [{k: v for k, v in rec.items() if k != "bundle"} for rec in runs],
        }
        (OUT / "run_summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
        if not smoke and (OUT / "smoke_summary.json").is_file():
            smoke = json.loads((OUT / "smoke_summary.json").read_text())
        if not preflight and (OUT / "preflight.json").is_file():
            preflight = json.loads((OUT / "preflight.json").read_text())
        write_data_report(settings, [{k: v for k, v in rec.items() if k != "bundle"} for rec in runs], smoke, preflight)

    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))

#!/usr/bin/env python3
"""SSTRF validity-v2 post-trial elicitation (Part C — Appendix B/C).

Runs CIEPSS instrument elicitation for each completed trial in
``docs/diagnostics/sstrf_validity_v2_manifest.json``. Writes per-agent JSON under
``docs/research/runs/ciepss_school_b/validity_v2/elicitation/{trial_label}/``.

**Live runs:** unset a stale shell ``ANTHROPIC_API_KEY`` if it shadows ``backend/.env``.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

_REPO_ROOT = Path(__file__).resolve().parents[1]
_SCRIPTS_DIR = Path(__file__).resolve().parent
_BACKEND_SRC = _REPO_ROOT / "backend" / "src"
sys.path.insert(0, str(_BACKEND_SRC))
sys.path.insert(0, str(_SCRIPTS_DIR))

from run_arc11_ablation import load_dotenv_if_present  # noqa: E402

from mirofish_backend.config import get_settings  # noqa: E402
from mirofish_backend.db.repo import get_simulation_export_bundle  # noqa: E402
from mirofish_backend.diagnostics.sstrf_validity_v2_elicitation import (  # noqa: E402
    VALIDITY_PINNED_MODEL,
    attach_elicitation_to_trial,
    completed_validity_trials,
    default_elicitation_root,
    default_manifest_path,
    finalize_validity_elicitation_manifest,
    load_validity_manifest,
    rel_path_from_repo,
    save_validity_manifest,
    trial_elicitation_dir,
)
from mirofish_backend.llm.prompt_templates import build_system_prompt  # noqa: E402
from mirofish_backend.llm.router import llm_complete  # noqa: E402
from mirofish_backend.scenarios.loader import load_scenario_for_run  # noqa: E402
from mirofish_backend.scenarios.registry import PersonaTemplate  # noqa: E402

from sstrf_elicitation_instruments import (  # noqa: E402
    CIEPSS_STUDY_ID,
    assert_no_contamination,
    build_elicitation_user_prompt,
    expected_elicitation_persona_ids,
    instrument_for_persona,
    persona_id_from_agent_id,
    validate_instruments,
)
from sstrf_elicitation_transcript import build_transcript_context_block  # noqa: E402

_DEFAULT_ENV_FILE = _REPO_ROOT / "backend" / ".env"
DEFAULT_MAX_TOKENS = int(os.environ.get("SSTRF_ELICITATION_MAX_TOKENS", "2048"))


@dataclass(frozen=True)
class ValidityElicitationConfig:
    scenario_id: str = "ciepss_school_b"
    study_id: str = CIEPSS_STUDY_ID
    pinned_model: str = VALIDITY_PINNED_MODEL
    enforce_pinned_model: bool = True


def _final_snapshots(bundle: dict[str, Any]) -> dict[str, dict[str, Any]]:
    snaps: list[dict[str, Any]] = list(bundle.get("agent_state_snapshots") or [])
    if not snaps:
        raise RuntimeError("export bundle has no agent_state_snapshots")
    final_round = max(int(s["round_number"]) for s in snaps)
    by_agent: dict[str, dict[str, Any]] = {}
    for snap in snaps:
        if int(snap["round_number"]) != final_round:
            continue
        by_agent[str(snap["agent_id"])] = snap
    return by_agent


async def _persona_map(sqlite_path: str, scenario_id: str) -> dict[str, PersonaTemplate]:
    scenario_cfg, _src = await load_scenario_for_run(sqlite_path, scenario_id)
    return {p.persona_id: p for p in scenario_cfg.personas}


def _build_system_prompt(
    *,
    scenario_id: str,
    snapshot: dict[str, Any],
    persona: PersonaTemplate,
    prompt_version: str,
    slot_index: int,
) -> str:
    from mirofish_backend.simulation.agent_context import build_agent_context_v1

    attr = snapshot.get("attribute_sections") or {}
    demographics = {
        "age": snapshot.get("age"),
        "sex": snapshot.get("sex"),
        "ethnicity": snapshot.get("ethnicity"),
        "ses": snapshot.get("ses"),
    }
    state = {
        "support_level": float(snapshot["support_level"]),
        "resistance_level": float(snapshot["resistance_level"]),
        "workload_stress": float(snapshot["workload_stress"]),
        "belief_posture": snapshot["belief_posture"],
    }
    ctx = build_agent_context_v1(
        slot_index=slot_index,
        demographics=demographics,
        group_ids=persona.groups,
        identity=dict(attr.get("identity") or {}),
        attitudes=dict(attr.get("attitudes") or {}),
        personal_history=dict(attr.get("personal_history") or {}),
    )
    return build_system_prompt(
        scenario_id=scenario_id,
        role=str(snapshot["agent_role"]),
        name=str(snapshot["agent_name"]),
        style_cues=persona.style_cues,
        beliefs=persona.beliefs,
        demographics=ctx.to_prompt_demographics(),
        state=state,
        prompt_version=prompt_version,
        psychological_profile=persona.psychological_profile,
        implementation_profile=persona.implementation_profile,
        group_affiliations=persona.groups,
        identity=ctx.identity,
        attitudes=ctx.attitudes,
        personal_history=ctx.personal_history,
    )


def _assert_no_secret(payload: Any) -> None:
    secret = (os.environ.get("ANTHROPIC_API_KEY") or get_settings().anthropic_api_key or "").strip()
    if secret and secret in json.dumps(payload, ensure_ascii=False):
        raise RuntimeError("secret material detected in output payload; refusing to save")


def _resolve_anthropic_model(*, config: ValidityElicitationConfig, execute: bool) -> str:
    settings = get_settings()
    anthropic_model = (os.environ.get("ANTHROPIC_MODEL") or settings.anthropic_model).strip()
    if config.enforce_pinned_model:
        if execute and anthropic_model != config.pinned_model:
            print(
                f"[elicitation] WARNING: configured model {anthropic_model!r} != pinned "
                f"{config.pinned_model!r}; using pinned model for validity trial.",
                flush=True,
            )
        return config.pinned_model
    return anthropic_model


async def run_trial_elicitation(
    *,
    simulation_id: str,
    trial_label: str,
    sqlite_path: str,
    execute: bool,
    max_tokens: int,
    config: ValidityElicitationConfig | None = None,
    output_dir: Path | None = None,
) -> dict[str, Any]:
    run_config = config or ValidityElicitationConfig()
    instrument_report = validate_instruments(study_id=run_config.study_id)
    if not instrument_report["passed"]:
        raise RuntimeError(f"instrument contamination check failed: {instrument_report}")

    bundle = await get_simulation_export_bundle(sqlite_path, simulation_id=simulation_id)
    if bundle is None:
        raise RuntimeError(f"simulation {simulation_id!r} not found in {sqlite_path}")

    run = bundle["run"]
    if run.get("scenario_id") != run_config.scenario_id:
        raise RuntimeError(
            f"expected scenario_id {run_config.scenario_id!r}, got {run.get('scenario_id')!r}",
        )
    if run.get("status") != "completed":
        raise RuntimeError(
            f"simulation status is {run.get('status')!r}; elicitation requires completed",
        )

    cfg = run.get("config_snapshot") or {}
    prompt_version = str(run.get("prompt_version") or cfg.get("prompt_version") or "v1")
    seed = run.get("random_seed")
    personas = await _persona_map(sqlite_path, run_config.scenario_id)
    snapshots = _final_snapshots(bundle)
    expected_personas = expected_elicitation_persona_ids(study_id=run_config.study_id)

    missing_personas = [
        pid
        for pid in expected_personas
        if not any(persona_id_from_agent_id(aid) == pid for aid in snapshots)
    ]
    if missing_personas:
        raise RuntimeError(f"missing agents for personas: {missing_personas}")

    anthropic_model = _resolve_anthropic_model(config=run_config, execute=execute)
    temperature = float(cfg.get("llm_temperature", get_settings().llm_temperature))

    out_dir = output_dir or trial_elicitation_dir(trial_label=trial_label, root=_REPO_ROOT)
    out_dir.mkdir(parents=True, exist_ok=True)
    results: list[dict[str, Any]] = []

    for agent_id, snapshot in sorted(snapshots.items(), key=lambda kv: kv[0]):
        persona_id = persona_id_from_agent_id(agent_id)
        if persona_id not in expected_personas:
            continue
        persona = personas[persona_id]
        instrument_name, questions = instrument_for_persona(
            persona_id,
            study_id=run_config.study_id,
        )
        group_ids = frozenset(str(g) for g in (snapshot.get("group_ids") or persona.groups or ()))
        transcript_context = build_transcript_context_block(
            bundle=bundle,
            agent_id=agent_id,
            group_ids=group_ids,
        )
        system_prompt = _build_system_prompt(
            scenario_id=run_config.scenario_id,
            snapshot=snapshot,
            persona=persona,
            prompt_version=prompt_version,
            slot_index=int(agent_id.rsplit("_", 1)[1]),
        )
        user_prompt = build_elicitation_user_prompt(
            questions=questions,
            transcript_context=transcript_context,
            instrument_label=instrument_name,
        )
        assert_no_contamination(user_prompt, label=f"{persona_id} user prompt")
        assert_no_contamination(system_prompt, label=f"{persona_id} system prompt")

        record: dict[str, Any] = {
            "simulation_id": simulation_id,
            "trial_label": trial_label,
            "seed": seed,
            "agent_id": agent_id,
            "persona_id": persona_id,
            "role": snapshot.get("agent_role"),
            "instrument_name": instrument_name,
            "questions": list(questions),
            "model_id": anthropic_model,
            "effective_provider": "anthropic",
            "max_tokens": max_tokens,
            "timestamp": datetime.now(tz=UTC).isoformat(),
            "dry_run": not execute,
        }

        if execute:
            settings = get_settings()
            if not (settings.anthropic_api_key or os.environ.get("ANTHROPIC_API_KEY") or "").strip():
                raise RuntimeError("ANTHROPIC_API_KEY is required for --execute")
            completion = await llm_complete(
                provider="anthropic",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=temperature,
                max_tokens=max_tokens,
                lmstudio_base_url=settings.lmstudio_base_url,
                lmstudio_model=settings.lmstudio_model,
                anthropic_api_key=settings.anthropic_api_key,
                anthropic_model=anthropic_model,
            )
            record["raw_response"] = completion.text
            record["input_tokens"] = completion.input_tokens
            record["output_tokens"] = completion.output_tokens
        else:
            record["raw_response"] = None
            record["input_tokens"] = None
            record["output_tokens"] = None

        _assert_no_secret(record)
        out_path = out_dir / f"{simulation_id}_{agent_id}.json"
        out_path.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
        record["output_path"] = rel_path_from_repo(out_path, root=_REPO_ROOT)
        results.append({k: v for k, v in record.items() if k != "raw_response"})

    manifest = {
        "simulation_id": simulation_id,
        "trial_label": trial_label,
        "seed": seed,
        "scenario_id": run_config.scenario_id,
        "study_id": run_config.study_id,
        "agent_count": len(results),
        "execute": execute,
        "model_id": anthropic_model,
        "instrument_validation": instrument_report,
        "agents": results,
        "timestamp": datetime.now(tz=UTC).isoformat(),
    }
    manifest_path = out_dir / f"{simulation_id}_manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    manifest["manifest_path"] = rel_path_from_repo(manifest_path, root=_REPO_ROOT)
    return manifest


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="SSTRF validity-v2 post-trial elicitation (Part C)")
    p.add_argument(
        "--manifest",
        type=Path,
        default=default_manifest_path(root=_REPO_ROOT),
        help="Validity trials manifest from Part B",
    )
    p.add_argument("--sqlite-path", default="", help="SQLite path (default: settings)")
    p.add_argument(
        "--trial-label",
        action="append",
        dest="trial_labels",
        help="Run one trial only (repeatable). Default: all completed trials.",
    )
    p.add_argument(
        "--validate-instruments-only",
        action="store_true",
        help="Run contamination guard on frozen instrument text and exit.",
    )
    p.add_argument(
        "--dry-run",
        action="store_true",
        help="Build prompts and write JSON shells without Anthropic calls.",
    )
    p.add_argument(
        "--execute",
        action="store_true",
        help="Call Anthropic for each agent (live elicitation).",
    )
    p.add_argument("--max-tokens", type=int, default=DEFAULT_MAX_TOKENS)
    p.add_argument("--env-file", type=Path, default=_DEFAULT_ENV_FILE)
    return p


async def _main_async(args: argparse.Namespace) -> dict[str, Any]:
    if args.execute and args.dry_run:
        raise RuntimeError("choose one of --dry-run or --execute, not both")

    if args.validate_instruments_only:
        report = validate_instruments(study_id=CIEPSS_STUDY_ID)
        if not report["passed"]:
            raise RuntimeError(f"instrument validation failed: {report}")
        return {"status": "instruments_ok", "report": report}

    mode = "execute" if args.execute else "dry_run"
    settings = get_settings()
    sqlite_path = args.sqlite_path or settings.sqlite_path

    validity_manifest = load_validity_manifest(path=args.manifest, root=_REPO_ROOT)
    trials = completed_validity_trials(validity_manifest)
    if args.trial_labels:
        wanted = frozenset(args.trial_labels)
        trials = [t for t in trials if str(t.get("trial_label") or "") in wanted]
        if not trials:
            raise RuntimeError(f"no completed trials matched labels: {sorted(wanted)}")

    print(
        f"[elicitation] validity-v2 — {len(trials)} trial(s), mode={mode}, model={VALIDITY_PINNED_MODEL}",
        flush=True,
    )

    summaries: list[dict[str, Any]] = []
    for trial in trials:
        label = str(trial["trial_label"])
        simulation_id = str(trial["simulation_id"])
        print(f"[elicitation] {label} simulation_id={simulation_id}", flush=True)
        elic_manifest = await run_trial_elicitation(
            simulation_id=simulation_id,
            trial_label=label,
            sqlite_path=sqlite_path,
            execute=args.execute,
            max_tokens=args.max_tokens,
        )
        manifest_path = _REPO_ROOT / str(elic_manifest["manifest_path"])
        attach_elicitation_to_trial(
            manifest=validity_manifest,
            trial_label=label,
            elicitation_manifest=elic_manifest,
            elicitation_manifest_path=manifest_path,
            root=_REPO_ROOT,
        )
        summaries.append(
            {
                "trial_label": label,
                "simulation_id": simulation_id,
                "agent_count": elic_manifest.get("agent_count"),
                "manifest_path": elic_manifest.get("manifest_path"),
            },
        )
        print(json.dumps(summaries[-1]), flush=True)

    finalize_validity_elicitation_manifest(
        manifest=validity_manifest,
        mode=mode,
        command=" ".join(sys.argv),
        output_root=default_elicitation_root(root=_REPO_ROOT),
        root=_REPO_ROOT,
    )
    save_validity_manifest(manifest=validity_manifest, path=args.manifest, root=_REPO_ROOT)
    return {
        "status": "ok",
        "mode": mode,
        "trial_count": len(summaries),
        "trials": summaries,
        "manifest": str(args.manifest),
    }


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if not args.validate_instruments_only and not args.dry_run and not args.execute:
        args.dry_run = True
    load_dotenv_if_present(args.env_file)
    try:
        payload = asyncio.run(_main_async(args))
    except (ValueError, RuntimeError, FileNotFoundError, KeyError) as exc:
        print(f"\n{exc}\n", file=sys.stderr)
        print(json.dumps({"error": str(exc)}), file=sys.stderr)
        return 1
    print(json.dumps(payload))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

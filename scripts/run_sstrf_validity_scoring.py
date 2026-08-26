#!/usr/bin/env python3
"""SSTRF validity-v2 scoring pipeline (Part D — GM-F v2 judge + adjudication)."""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

_REPO_ROOT = Path(__file__).resolve().parents[1]
_SCRIPTS_DIR = Path(__file__).resolve().parent
_BACKEND_SRC = _REPO_ROOT / "backend" / "src"
if str(_BACKEND_SRC) not in sys.path:
    sys.path.insert(0, str(_BACKEND_SRC))
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

from sstrf_scoring_adjudication import (
    adjudicate_trial,
    apply_human_scores,
    apply_judge_parse_failures,
    build_human_review_queue,
    build_tier1_plausibility_summary,
    collect_auto_resolved_diff_of_one_cells,
    count_adjudication_rules,
    count_drift_disagreements,
    DRIFT_CELL_SAMPLE_SEED,
    DRIFT_TRIAL_SAMPLE_SEED,
    drift_rescore_triggered,
    finalize_study_summary,
    prepare_trials_for_human_review,
    sample_drift_cells,
    trial_passes,
)
from sstrf_scoring_evidence import (
    assert_calibration_set_signed,
    assert_no_secret,
    assemble_trial_evidence,
    build_rater_payload,
    build_stage1_escalation_packets_validity,
    build_tier2_drift_packets_validity,
    build_validity_v2_trial_mapping,
    DEFAULT_VALIDITY_SQLITE,
    load_validity_v2_manifest,
    trial_record_from_validity_label,
    VALIDITY_V2_MANIFEST_PATH,
    VALIDITY_V2_SCORING_DIR,
    VALIDITY_V2_SCORING_MANIFEST,
    VALIDITY_V2_TRIAL_LABEL_MAP,
)
from mirofish_backend.diagnostics.sstrf_validity_v2_scoring import (
    attach_scoring_to_validity_manifest,
    save_validity_manifest_with_scoring,
)
from mirofish_backend.llm.model_profiles import OPENAI_DEFAULT_ID

from sstrf_scoring_judge import (
    calibration_gate_passes,
    profile_spec_from_calibration_gate,
    resolve_judge_chain,
    run_calibration_pass,
    run_judge_pass,
    shuffle_orders,
    build_judge_user_prompt,
    JUDGE_PRIMARY_MODEL,
)

CALIBRATION_GATE_RESULT = VALIDITY_V2_SCORING_DIR / "calibration_gate_result.json"
HUMAN_REVIEW_QUEUE = VALIDITY_V2_SCORING_DIR / "human_review_queue.json"
SCORING_STATE = VALIDITY_V2_SCORING_DIR / "scoring_state.json"
JUDGE_SCORING_SUMMARY = VALIDITY_V2_SCORING_DIR / "validity_v2_judge_scoring_summary.json"
TIER1_PLAUSIBILITY_SUMMARY = VALIDITY_V2_SCORING_DIR / "tier1_plausibility_summary.json"
TIER2_DRIFT_PACKETS = VALIDITY_V2_SCORING_DIR / "tier2_drift_packets.json"
STAGE1_ESCALATION_PACKETS = VALIDITY_V2_SCORING_DIR / "stage1_escalation_packets.json"
CALIBRATION_PASS_THRESHOLD = 12


def _is_primary_openai_judge(spec) -> bool:
    model_id = spec.model_id or JUDGE_PRIMARY_MODEL
    return spec.profile_id == OPENAI_DEFAULT_ID and model_id == JUDGE_PRIMARY_MODEL


def _write_calibration_gate_result(results: dict[str, Any]) -> None:
    VALIDITY_V2_SCORING_DIR.mkdir(parents=True, exist_ok=True)
    CALIBRATION_GATE_RESULT.write_text(json.dumps(results, indent=2) + "\n", encoding="utf-8")


def _finalize_calibration_results(
    results: dict[str, Any],
    passed: bool,
    chosen_model: str | None,
    chosen_profile_id: str | None,
) -> None:
    last_attempt = results["attempts"][-1] if results["attempts"] else {}
    results.update(
        {
            "passed": passed,
            "judge_model_id": chosen_model,
            "judge_profile_id": chosen_profile_id,
            "pass_1_correct": last_attempt.get("pass_1_correct", 0),
            "pass_2_correct": last_attempt.get("pass_2_correct", 0),
            "gate_items": last_attempt.get("gate_items", {}),
            "non_gating_probes": last_attempt.get("non_gating_probes", {}),
        },
    )


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _load_scoring_state() -> dict[str, Any]:
    if not SCORING_STATE.exists():
        return {"trials": {}, "pass_1_seed": None, "pass_2_seed": None}
    return json.loads(SCORING_STATE.read_text(encoding="utf-8"))


def _save_scoring_state(state: dict[str, Any]) -> None:
    VALIDITY_V2_SCORING_DIR.mkdir(parents=True, exist_ok=True)
    assert_no_secret(state, os.environ.get("OPENAI_API_KEY", ""))
    assert_no_secret(state, os.environ.get("OPENROUTER_API_KEY", ""))
    SCORING_STATE.write_text(json.dumps(state, indent=2) + "\n", encoding="utf-8")


def assert_calibration_gate_passed() -> None:
    if not CALIBRATION_GATE_RESULT.exists():
        raise RuntimeError(
            "Calibration gate not passed — run --run-calibration --execute-judge-calls first",
        )
    result = json.loads(CALIBRATION_GATE_RESULT.read_text(encoding="utf-8"))
    if not result.get("passed"):
        raise RuntimeError("Calibration gate failed — cannot score real trials")


def _load_mapping(manifest: dict[str, Any], *, write_label_map: bool) -> dict[str, dict[str, Any]]:
    if VALIDITY_V2_TRIAL_LABEL_MAP.is_file():
        mapping = json.loads(VALIDITY_V2_TRIAL_LABEL_MAP.read_text(encoding="utf-8"))
    else:
        mapping = build_validity_v2_trial_mapping(manifest)
        if write_label_map:
            VALIDITY_V2_SCORING_DIR.mkdir(parents=True, exist_ok=True)
            VALIDITY_V2_TRIAL_LABEL_MAP.write_text(json.dumps(mapping, indent=2) + "\n", encoding="utf-8")
    return mapping


async def cmd_dry_run(args: argparse.Namespace) -> int:
    manifest = load_validity_v2_manifest(Path(args.manifest) if args.manifest else None)
    mapping = _load_mapping(manifest, write_label_map=args.write_label_map)
    label = args.trial_label or next(iter(sorted(mapping)))
    record = trial_record_from_validity_label(label, manifest)
    evidence = await assemble_trial_evidence(
        record=record,
        sqlite_path=Path(args.sqlite),
        get_bundle=None,
    )
    payload = build_rater_payload(evidence)
    prop_order, agent_orders, elic_order, trans_order = shuffle_orders(
        args.pass_1_seed,
        elicitation_count=len(payload["elicitation"]),
        transcript_count=len(evidence.transcript),
    )
    prompt = build_judge_user_prompt(
        evidence,
        proposition_order=prop_order,
        agent_orders=agent_orders,
        elicitation_order=elic_order,
        transcript_order=trans_order,
    )
    print(
        f"dry-run trial={label} staff_elicitation_rows={len(payload['elicitation'])} "
        f"transcript_turns={len(evidence.transcript)} judgements={len(prop_order)}",
    )
    if args.verbose:
        print(json.dumps(payload, indent=2))
        print("--- judge prompt ---")
        print(prompt)
    else:
        print("payload keys:", sorted(payload.keys()))
        print("prompt chars:", len(prompt))
    return 0


async def cmd_run_calibration(args: argparse.Namespace) -> int:
    assert_calibration_set_signed()
    chain = resolve_judge_chain()
    results: dict[str, Any] = {
        "run_at": _utc_now(),
        "harness": "sstrf-validity-v2",
        "pass_1_seed": args.pass_1_seed,
        "pass_2_seed": args.pass_2_seed,
        "attempts": [],
    }
    if not args.execute_judge_calls:
        print(
            "calibration dry-run: would score 15 gating items + 2 probe items × 2 passes "
            "on judge chain",
        )
        return 0

    passed = False
    chosen_model = None
    chosen_profile_id = None
    for spec in chain:
        try:
            p1 = await run_calibration_pass(pass_seed=args.pass_1_seed, profile_spec=spec)
            p2 = await run_calibration_pass(pass_seed=args.pass_2_seed, profile_spec=spec)
        except RuntimeError as exc:
            results["attempts"].append(
                {
                    "profile_id": spec.profile_id,
                    "model_id": spec.model_id or "",
                    "api_error": str(exc),
                    "gate_passed": False,
                },
            )
            if _is_primary_openai_judge(spec):
                print(f"openai_default unavailable ({exc}) — trying openrouter backup")
                continue
            _finalize_calibration_results(results, passed, chosen_model, chosen_profile_id)
            _write_calibration_gate_result(results)
            print("calibration FAILED — judge API error after primary path exhausted")
            return 1

        gate_passed = calibration_gate_passes(
            pass_1_items=p1.gate_item_results,
            pass_2_items=p2.gate_item_results,
            threshold=CALIBRATION_PASS_THRESHOLD,
        )
        results["attempts"].append(
            {
                "profile_id": spec.profile_id,
                "model_id": p1.model_id,
                "pass_1_correct": p1.gate_correct,
                "pass_2_correct": p2.gate_correct,
                "gate_passed": gate_passed,
                "gate_items": {
                    "pass_1": p1.to_gate_dicts(),
                    "pass_2": p2.to_gate_dicts(),
                },
                "non_gating_probes": {
                    "pass_1": p1.to_probe_dicts(),
                    "pass_2": p2.to_probe_dicts(),
                },
            },
        )
        if gate_passed:
            passed = True
            chosen_model = p1.model_id
            chosen_profile_id = p1.profile_id
            break
        if _is_primary_openai_judge(spec):
            print(
                "calibration gate FAILED on openai_default — stopped before backup/escalation "
                "(human decision required per GM-F v2)",
            )
            break
    _finalize_calibration_results(results, passed, chosen_model, chosen_profile_id)
    _write_calibration_gate_result(results)
    if not passed:
        print("calibration FAILED on all judge configurations — stop; human-only scoring required")
        return 1
    print(f"calibration PASSED judge_profile_id={chosen_profile_id} judge_model_id={chosen_model}")
    return 0


async def cmd_score_all_trials(args: argparse.Namespace) -> int:
    assert_calibration_set_signed()
    assert_calibration_gate_passed()
    manifest = load_validity_v2_manifest(Path(args.manifest) if args.manifest else None)
    mapping = _load_mapping(manifest, write_label_map=True)
    state = _load_scoring_state()
    state["pass_1_seed"] = args.pass_1_seed
    state["pass_2_seed"] = args.pass_2_seed
    gate = json.loads(CALIBRATION_GATE_RESULT.read_text(encoding="utf-8"))
    profile_spec = profile_spec_from_calibration_gate(gate)

    for label in sorted(mapping):
        existing = (state.get("trials") or {}).get(label) or {}
        if existing.get("pass_1") and existing.get("pass_2"):
            print(f"skip {label} (already scored)")
            continue
        record = trial_record_from_validity_label(label, manifest)
        evidence = await assemble_trial_evidence(
            record=record,
            sqlite_path=Path(args.sqlite),
            get_bundle=None,
        )
        if args.execute_judge_calls:
            pass_1 = await run_judge_pass(
                evidence, pass_seed=args.pass_1_seed, profile_spec=profile_spec,
            )
            pass_2 = await run_judge_pass(
                evidence, pass_seed=args.pass_2_seed, profile_spec=profile_spec,
            )
            trial_entry: dict[str, Any] = {
                "pass_1": pass_1.scores,
                "pass_2": pass_2.scores,
                "judge_model_id": pass_1.judge_model_id,
                "judge_profile_id": profile_spec.profile_id,
                "parse_failed_pass_1": list(pass_1.parse_failed),
                "parse_failed_pass_2": list(pass_2.parse_failed),
            }
            _, rules, _ = adjudicate_trial(pass_1.scores, pass_2.scores)
            trial_entry["adjudication_rules"] = rules
            apply_judge_parse_failures(trial_entry)
            rules = trial_entry["adjudication_rules"]
            trial_entry["auto_resolved_diff_of_one"] = [
                {
                    "cell_id": cell_id,
                    "proposition": cell_id.split(":", 1)[0],
                    "pass_1": int(pass_1.scores[cell_id]),
                    "pass_2": int(pass_2.scores[cell_id]),
                    "adjudicated": min(int(pass_1.scores[cell_id]), int(pass_2.scores[cell_id])),
                    "auto_resolved_diff_of_one": True,
                }
                for cell_id, rule in rules.items()
                if rule == "lower_of_one"
            ]
            state["trials"][label] = trial_entry
            if trial_entry.get("judge_parse_failed"):
                print(
                    f"WARNING {label}: judge parse failed for "
                    f"{trial_entry['judge_parse_failed']} — queued for Mark",
                )
            if not args.verbose:
                print(f"scored {label}")
            _save_scoring_state(state)
            await asyncio.sleep(3)
        else:
            print(f"would score {label} (use --execute-judge-calls)")

    if args.execute_judge_calls and state.get("trials"):
        rule_counts = count_adjudication_rules(state["trials"])
        diff_of_one = collect_auto_resolved_diff_of_one_cells(state["trials"])
        summary = {
            "scored_at": _utc_now(),
            "harness": "sstrf-validity-v2",
            "judge_profile_id": profile_spec.profile_id,
            "judge_model_id": gate.get("judge_model_id"),
            "pass_1_seed": args.pass_1_seed,
            "pass_2_seed": args.pass_2_seed,
            "trials_scored": len(state["trials"]),
            "adjudication_rule_counts": rule_counts,
            "auto_resolved_diff_of_one_cells": diff_of_one,
            "scoring_state_path": str(SCORING_STATE),
            "manifest_path": str(VALIDITY_V2_SCORING_MANIFEST),
        }
        state["adjudication_rule_counts"] = rule_counts
        state["auto_resolved_diff_of_one_cells"] = diff_of_one
        state["scored_at"] = summary["scored_at"]
        VALIDITY_V2_SCORING_DIR.mkdir(parents=True, exist_ok=True)
        JUDGE_SCORING_SUMMARY.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
        print(
            f"adjudication rules: agree={rule_counts['agree']} "
            f"lower_of_one={rule_counts['lower_of_one']} "
            f"human_required={rule_counts['human_required']} "
            f"judge_parse_failed={rule_counts['judge_parse_failed']}",
        )
    _save_scoring_state(state)
    return 0


def cmd_import_human_scores(args: argparse.Namespace) -> int:
    path = Path(args.import_human_scores)
    imported = json.loads(path.read_text(encoding="utf-8"))
    state = _load_scoring_state()
    apply_human_scores(state["trials"], imported)
    drift_scores = list(imported.get("drift_scores") or [])
    state["imported_drift_scores"] = drift_scores
    if drift_scores:
        disagreements = count_drift_disagreements(state["trials"], drift_scores)
        state["mark_disagreements"] = disagreements
        state["drift_scores_imported_at"] = _utc_now()
        rescore = drift_rescore_triggered(
            mark_disagreements=disagreements, sample_size=len(drift_scores),
        )
        print(
            f"drift check: {disagreements}/{len(drift_scores)} disagreements "
            f"(rescore_triggered={rescore})",
        )
    else:
        state.pop("imported_drift_scores", None)
        state.pop("mark_disagreements", None)
        state.pop("drift_scores_imported_at", None)
    _save_scoring_state(state)
    print(f"imported human scores from {path}")
    return 0


async def cmd_prepare_adjudication(args: argparse.Namespace) -> int:
    state = _load_scoring_state()
    if not state.get("trials"):
        raise RuntimeError("No scored trials in scoring_state.json — run --score-all-trials first")
    queue, drift_sample, drift_meta = prepare_trials_for_human_review(
        state["trials"],
        drift_sampling_mode=args.drift_sampling_mode,
        drift_sample_seed=args.drift_sample_seed,
        drift_trial_sample_seed=args.drift_trial_sample_seed,
    )
    tier1 = build_tier1_plausibility_summary(state["trials"])
    VALIDITY_V2_SCORING_DIR.mkdir(parents=True, exist_ok=True)
    TIER1_PLAUSIBILITY_SUMMARY.write_text(json.dumps(tier1, indent=2) + "\n", encoding="utf-8")

    manifest = load_validity_v2_manifest(Path(args.manifest) if args.manifest else None)
    tier2: dict[str, Any] | None = None
    sampled_trials = list(drift_meta.get("drift_sampled_trials") or [])
    if args.drift_sampling_mode == "trial" and sampled_trials:
        tier2 = build_tier2_drift_packets_validity(sampled_trials, manifest=manifest)
        TIER2_DRIFT_PACKETS.write_text(json.dumps(tier2, indent=2) + "\n", encoding="utf-8")

    stage1_empty = await build_stage1_escalation_packets_validity(
        [],
        manifest=manifest,
        sqlite_path=Path(args.sqlite),
    )
    STAGE1_ESCALATION_PACKETS.write_text(json.dumps(stage1_empty, indent=2) + "\n", encoding="utf-8")

    state["drift_sample"] = drift_sample
    state["drift_sampling_mode"] = args.drift_sampling_mode
    state["drift_sample_seed"] = (
        drift_meta.get("drift_trial_sample_seed")
        if args.drift_sampling_mode == "trial"
        else drift_meta.get("drift_sample_seed")
    )
    state["drift_sampled_trials"] = sampled_trials or None
    state["prepared_at"] = _utc_now()
    HUMAN_REVIEW_QUEUE.write_text(json.dumps(queue, indent=2) + "\n", encoding="utf-8")
    _save_scoring_state(state)
    print(
        f"prepared adjudication queue: "
        f"{len(queue['adjudication_required'])} cells need Mark, "
        f"{len(queue['drift_check_sample'])} drift-sample cells "
        f"({args.drift_sampling_mode} mode, seed={state['drift_sample_seed']})",
    )
    if sampled_trials:
        print(f"drift sampled trials: {', '.join(sampled_trials)}")
        print(f"tier2 packets for Mark drift-check: {TIER2_DRIFT_PACKETS}")
    print(f"tier1 summary: {TIER1_PLAUSIBILITY_SUMMARY}")
    print(f"human review queue: {HUMAN_REVIEW_QUEUE}")
    return 0


def cmd_finalize(args: argparse.Namespace) -> int:
    state = _load_scoring_state()
    if not state.get("drift_scores_imported_at"):
        raise RuntimeError(
            "--import-human-scores with drift_scores is required before --finalize",
        )
    trials_out: list[dict[str, Any]] = []
    trials_state: dict[str, dict[str, Any]] = {}
    human_count = 0
    for label in sorted(state.get("trials") or {}):
        trial = state["trials"][label]
        human_scores = {
            pid: int(val)
            for pid, val in (trial.get("adjudicated") or {}).items()
            if val is not None
        }
        adjudicated, rules, required = adjudicate_trial(
            trial["pass_1"],
            trial["pass_2"],
            human_scores=human_scores,
        )
        trial_work = {
            **trial,
            "adjudicated": adjudicated,
            "adjudication_rules": rules,
        }
        parse_failed = apply_judge_parse_failures(trial_work)
        adjudicated = trial_work["adjudicated"]
        rules = trial_work["adjudication_rules"]
        for pid in parse_failed:
            if pid not in required:
                required.append(pid)
        for pid in required:
            if adjudicated.get(pid) is None:
                raise RuntimeError(f"human score missing for {label} {pid}")
            human_count += 1
        final_scores = {
            pid: int(adjudicated[pid]) for pid in adjudicated if adjudicated[pid] is not None
        }
        trials_state[label] = {
            **trial_work,
            "adjudicated": final_scores,
        }
        trials_out.append(
            {
                "trial_label": label,
                "pass_1": trial["pass_1"],
                "pass_2": trial["pass_2"],
                "adjudicated": final_scores,
                "adjudication_rules": rules,
                "human_notes": trial.get("human_notes") or {},
                "trial_pass": trial_passes(final_scores),
                "judge_model_id": trial.get("judge_model_id"),
            },
        )

    drift_seed = int(state.get("drift_sample_seed") or args.drift_sample_seed)
    drift_sample = list(state.get("drift_sample") or [])
    if not drift_sample:
        raise RuntimeError("drift_sample missing — run --prepare-adjudication before --finalize")
    imported_drift = list(state.get("imported_drift_scores") or [])
    if len(imported_drift) != len(drift_sample):
        raise RuntimeError(
            f"drift_scores length {len(imported_drift)} does not match drift sample "
            f"size {len(drift_sample)}",
        )
    mark_disagreements = int(state.get("mark_disagreements") or 0)
    rescore = drift_rescore_triggered(
        mark_disagreements=mark_disagreements,
        sample_size=len(drift_sample),
    )
    queue = build_human_review_queue(trials=trials_state, drift_sample=drift_sample)
    HUMAN_REVIEW_QUEUE.write_text(json.dumps(queue, indent=2) + "\n", encoding="utf-8")

    calibration_gate = {}
    if CALIBRATION_GATE_RESULT.exists():
        calibration_gate = json.loads(CALIBRATION_GATE_RESULT.read_text(encoding="utf-8"))

    manifest_out = {
        "schema_version": 1,
        "harness": "sstrf-validity-v2",
        "scored_at": _utc_now(),
        "calibration_gate": {
            "passed": bool(calibration_gate.get("passed")),
            "judge_profile_id": calibration_gate.get("judge_profile_id"),
            "judge_model_id": calibration_gate.get("judge_model_id"),
            "pass_1_correct": calibration_gate.get("pass_1_correct"),
            "pass_2_correct": calibration_gate.get("pass_2_correct"),
        },
        "judge_models_used": sorted(
            {t.get("judge_model_id") for t in trials_out if t.get("judge_model_id")},
        ),
        "drift_check": {
            "sample_seed": drift_seed,
            "sampled_cells": drift_sample,
            "mark_disagreements": mark_disagreements,
            "rescore_triggered": rescore,
        },
        "study_summary": finalize_study_summary(trials=trials_out),
        "trials": trials_out,
        "human_adjudication_count": human_count,
        "disclosure": "All results reported regardless of outcome per pre-reg §9",
    }
    assert_no_secret(manifest_out, os.environ.get("OPENAI_API_KEY", ""))
    VALIDITY_V2_SCORING_DIR.mkdir(parents=True, exist_ok=True)
    VALIDITY_V2_SCORING_MANIFEST.write_text(json.dumps(manifest_out, indent=2) + "\n", encoding="utf-8")

    validity_manifest = load_validity_v2_manifest(Path(args.manifest) if args.manifest else None)
    attach_scoring_to_validity_manifest(
        manifest=validity_manifest,
        scoring_manifest_path=VALIDITY_V2_SCORING_MANIFEST,
        mode="finalize",
        command=" ".join(sys.argv),
        root=_REPO_ROOT,
    )
    save_validity_manifest_with_scoring(
        manifest=validity_manifest,
        path=Path(args.manifest) if args.manifest else VALIDITY_V2_MANIFEST_PATH,
        root=_REPO_ROOT,
    )

    print(
        f"manifest written study_pass={manifest_out['study_summary']['study_pass']} "
        f"trials_passed={manifest_out['study_summary']['trials_passed']}/"
        f"{manifest_out['study_summary']['trials_total']}",
    )
    print(f"scoring manifest: {VALIDITY_V2_SCORING_MANIFEST}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="SSTRF validity-v2 scoring pipeline (Part D)")
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--run-calibration", action="store_true")
    p.add_argument("--score-all-trials", action="store_true")
    p.add_argument("--import-human-scores", metavar="PATH")
    p.add_argument("--prepare-adjudication", action="store_true")
    p.add_argument("--finalize", action="store_true")
    p.add_argument("--execute-judge-calls", action="store_true")
    p.add_argument("--trial-label", default=None)
    p.add_argument("--manifest", default=str(VALIDITY_V2_MANIFEST_PATH))
    p.add_argument("--sqlite", default=str(DEFAULT_VALIDITY_SQLITE))
    p.add_argument("--pass-1-seed", type=int, default=101)
    p.add_argument("--pass-2-seed", type=int, default=202)
    p.add_argument("--drift-sampling-mode", choices=["trial", "cell"], default="trial")
    p.add_argument("--drift-sample-seed", type=int, default=DRIFT_CELL_SAMPLE_SEED)
    p.add_argument("--drift-trial-sample-seed", type=int, default=DRIFT_TRIAL_SAMPLE_SEED)
    p.add_argument("--write-label-map", action="store_true")
    p.add_argument("--verbose", action="store_true")
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.dry_run:
        return asyncio.run(cmd_dry_run(args))
    if args.run_calibration:
        return asyncio.run(cmd_run_calibration(args))
    if args.score_all_trials:
        return asyncio.run(cmd_score_all_trials(args))
    if args.import_human_scores:
        return cmd_import_human_scores(args)
    if args.prepare_adjudication:
        return asyncio.run(cmd_prepare_adjudication(args))
    if args.finalize:
        return cmd_finalize(args)
    build_parser().print_help()
    return 2


if __name__ == "__main__":
    raise SystemExit(main())

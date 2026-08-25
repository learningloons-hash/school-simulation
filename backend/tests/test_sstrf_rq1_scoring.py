"""Unit tests for SSTRF RQ1 scoring pipeline (GM-F v2, iter-57)."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

_REPO = Path(__file__).resolve().parents[2]
_SCRIPTS = _REPO / "scripts"
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

from sstrf_scoring_adjudication import (  # noqa: E402
    adjudicate_cell,
    build_human_review_queue,
    build_tier1_plausibility_summary,
    count_drift_disagreements,
    drift_disagree_threshold,
    drift_rescore_triggered,
    expand_drift_trials_to_cells,
    prepare_trials_for_human_review,
    sample_drift_cells,
    sample_drift_trials,
    study_passes,
    trial_passes,
)
from sstrf_scoring_evidence import (  # noqa: E402
    TrialEvidence,
    TrialRecord,
    assert_calibration_set_signed,
    assert_rater_payload_clean,
    assign_trial_labels,
    assemble_trial_evidence,
    build_full_transcript,
    build_rater_payload,
    load_elicitation_responses,
)
from sstrf_scoring_judge import (  # noqa: E402
    CALIBRATION_ITEMS,
    INSTRUCTIONS_VERBATIM,
    JUDGEMENTS_PER_TRIAL,
    PROPOSITIONS_VERBATIM,
    SCALE_VERBATIM,
    SCORED_STAFF_AGENTS,
    JUDGE_OPENROUTER_MODEL,
    JUDGE_PRIMARY_MODEL,
    CalibrationItemResult,
    all_trial_cell_ids,
    build_judge_user_prompt,
    build_rubric_block,
    calibration_gate_passes,
    count_gate_correct,
    no_proposition_double_miss,
    parse_trial_scores,
    profile_spec_from_calibration_gate,
    proposition_incorrect_counts,
    resolve_judge_chain,
    shuffle_orders,
    trial_cell_id,
)
from sstrf_scoring_adjudication import apply_judge_parse_failures  # noqa: E402
from sstrf_elicitation_transcript import _strip_state_block  # noqa: E402


def _sample_trial_scores(**overrides: int) -> dict[str, int]:
    scores = {cell_id: 2 for cell_id in all_trial_cell_ids()}
    scores.update(overrides)
    return scores


def _staff_elicitation() -> list[dict]:
    return [
        {
            "persona_id": agent,
            "role": "staff",
            "agent_name": agent,
            "raw_response": "School leadership filters policy.",
        }
        for agent in SCORED_STAFF_AGENTS
    ]


def _parent_elicitation() -> dict:
    return {
        "persona_id": "parent_001",
        "role": "parent",
        "agent_name": "Parent A",
        "raw_response": "Parent view excluded from proposition scoring.",
    }


def _sample_evidence() -> TrialEvidence:
    return TrialEvidence(
        trial_label="trial-A",
        elicitation=_staff_elicitation() + [_parent_elicitation()],
        transcript=build_full_transcript(_sample_bundle()),
    )
def _sample_bundle() -> dict:
    return {
        "run": {
            "simulation_id": "abc123deadbeefdeadbeefdeadbeef",
            "random_seed": 101,
            "config_snapshot": {"economics": {"cost": 1.0}, "network_csv": "secret"},
        },
        "transcript": [
            {
                "round_number": 1,
                "turn_index": 0,
                "agent_id": "teacher_001_003",
                "agent_name": "Miss M",
                "agent_role": "teacher",
                "raw_response": "School leadership filters MOE guidance. <state>{\"x\":1}</state>",
                "timestamp": "2026-08-08T12:00:00+00:00",
            }
        ],
        "agent_state_snapshots": [{"agent_id": "teacher_001_003", "round_number": 6, "support_level": 0.5}],
        "economics": {"total_cost": 0.5},
    }


def test_evidence_excludes_config_snapshot() -> None:
    evidence = _sample_evidence()
    payload = build_rater_payload(evidence)
    dumped = json.dumps(payload)
    assert "config_snapshot" not in dumped
    assert "economics" not in dumped
    assert_rater_payload_clean(payload)
    assert len(payload["elicitation"]) == len(SCORED_STAFF_AGENTS)
    assert all(row["persona_id"] in SCORED_STAFF_AGENTS for row in payload["elicitation"])


def test_elicitation_loads_from_per_agent_json(tmp_path: Path) -> None:
    rel = "sim_teacher.json"
    agent_path = tmp_path / rel
    agent_path.write_text(
        json.dumps(
            {
                "raw_response": "Teachers adapt materials in small ways.",
                "persona_id": "teacher_001",
                "role": "teacher",
            }
        ),
        encoding="utf-8",
    )
    manifest = {
        "agents": [
            {
                "persona_id": "teacher_001",
                "role": "teacher",
                "agent_name": "Miss M",
                "output_path": rel,
            }
        ]
    }
    rows = load_elicitation_responses(elicitation_manifest=manifest, repo_root=tmp_path)
    assert len(rows) == 1
    assert "small ways" in rows[0]["raw_response"]


def test_transcript_strips_state_blocks() -> None:
    raw = "Hello <state>{\"a\":1}</state> world"
    assert "<state>" not in _strip_state_block(raw)
    turns = build_full_transcript(_sample_bundle())
    assert "<state>" not in turns[0]["raw_response"]


def test_redaction_removes_seed_and_sim_id() -> None:
    turns = build_full_transcript(_sample_bundle())
    dumped = json.dumps(turns)
    assert "abc123deadbeefdeadbeefdeadbeef" not in dumped
    assert "101" not in turns[0]["raw_response"]


def test_rater_payload_strips_trial_and_condition_labels() -> None:
    evidence = _sample_evidence()
    payload = build_rater_payload(evidence)
    dumped = json.dumps(payload)
    assert "trial-A" not in dumped
    assert "trial_label" not in dumped
    assert "condition" not in dumped.lower()


def test_judge_prompt_excludes_leakage_labels() -> None:
    evidence = _sample_evidence()
    prop_order, agent_orders, elic_order, trans_order = shuffle_orders(
        11, elicitation_count=len(SCORED_STAFF_AGENTS), transcript_count=1
    )
    prompt = build_judge_user_prompt(
        evidence,
        proposition_order=prop_order,
        agent_orders=agent_orders,
        elicitation_order=elic_order,
        transcript_order=trans_order,
    )
    assert "trial-A" not in prompt
    assert "101" not in prompt
    assert "phase_v_seed" not in prompt.lower()
    assert "P1:vice_principal_001" in prompt


def test_shuffle_differs_between_passes() -> None:
    p1, a1, e1, t1 = shuffle_orders(11, elicitation_count=4, transcript_count=6)
    p2, a2, e2, t2 = shuffle_orders(22, elicitation_count=4, transcript_count=6)
    assert (p1, a1, e1, t1) != (p2, a2, e2, t2)


def test_adjudication_agree() -> None:
    cell = adjudicate_cell(2, 2)
    assert cell.adjudicated == 2
    assert cell.adjudication_rule == "agree"


def test_adjudication_lower_of_one() -> None:
    cell = adjudicate_cell(2, 1)
    assert cell.adjudicated == 1
    assert cell.adjudication_rule == "lower_of_one"


def test_collect_auto_resolved_diff_of_one_cells() -> None:
    from sstrf_scoring_adjudication import collect_auto_resolved_diff_of_one_cells

    scores = _sample_trial_scores()
    scores[trial_cell_id("P2")] = 1
    pass_2 = dict(scores)
    pass_2[trial_cell_id("P2")] = 2
    trials = {
        "trial-A": {
            "pass_1": scores,
            "pass_2": pass_2,
            "parse_failed_pass_1": [],
            "parse_failed_pass_2": [],
        }
    }
    cells = collect_auto_resolved_diff_of_one_cells(trials)
    assert len(cells) == 1
    assert cells[0]["cell_id"] == "P2"


def test_count_adjudication_rules() -> None:
    from sstrf_scoring_adjudication import count_adjudication_rules

    pass_1 = _sample_trial_scores()
    pass_2 = _sample_trial_scores()
    pass_1[trial_cell_id("P2")] = 1
    pass_2[trial_cell_id("P2")] = 2
    pass_1[trial_cell_id("P3", SCORED_STAFF_AGENTS[0])] = 0
    pass_2[trial_cell_id("P3", SCORED_STAFF_AGENTS[0])] = 2
    pass_1[trial_cell_id("P4", SCORED_STAFF_AGENTS[0])] = -1
    pass_2[trial_cell_id("P4", SCORED_STAFF_AGENTS[0])] = 1
    trials = {
        "trial-A": {
            "pass_1": pass_1,
            "pass_2": pass_2,
            "parse_failed_pass_1": [],
            "parse_failed_pass_2": [],
        }
    }
    counts = count_adjudication_rules(trials)
    assert counts["agree"] == JUDGEMENTS_PER_TRIAL - 3
    assert counts["lower_of_one"] == 1
    assert counts["human_required"] == 2
    assert counts["judge_parse_failed"] == 0


def test_adjudication_human_required_diff_ge_2() -> None:
    cell = adjudicate_cell(2, 0)
    assert cell.human_required is True
    assert cell.adjudication_rule == "human_required"


def test_adjudication_human_required_minus_one() -> None:
    cell = adjudicate_cell(-1, 1)
    assert cell.human_required is True


@pytest.mark.parametrize(
    "overrides,expected",
    [
        ({}, True),
        ({trial_cell_id("P1", SCORED_STAFF_AGENTS[0]): 1,
          trial_cell_id("P1", SCORED_STAFF_AGENTS[1]): 1}, False),
        ({trial_cell_id("P2"): 1}, False),
        ({trial_cell_id("P3", SCORED_STAFF_AGENTS[0]): -1}, False),
        ({trial_cell_id("P4", SCORED_STAFF_AGENTS[0]): 1,
          trial_cell_id("P4", SCORED_STAFF_AGENTS[1]): 1,
          trial_cell_id("P4", SCORED_STAFF_AGENTS[2]): 1,
          trial_cell_id("P4", SCORED_STAFF_AGENTS[3]): 1}, False),
    ],
)
def test_trial_pass_v2_rules(overrides: dict[str, int], expected: bool) -> None:
    assert trial_passes(_sample_trial_scores(**overrides)) is expected


def test_study_pass_eight_of_ten() -> None:
    assert study_passes([True] * 7 + [False] * 3) is False
    assert study_passes([True] * 8 + [False] * 2) is True


def test_drift_rescore_trigger() -> None:
    assert drift_rescore_triggered(mark_disagreements=2) is False
    assert drift_rescore_triggered(mark_disagreements=3) is True


def test_calibration_gate_blocks_draft(tmp_path: Path) -> None:
    draft = tmp_path / "cal.md"
    draft.write_text("**Status: DRAFT** — not signed\n", encoding="utf-8")
    with patch("sstrf_scoring_evidence.CALIBRATION_SET", draft):
        with pytest.raises(RuntimeError, match="DRAFT"):
            assert_calibration_set_signed()


def test_calibration_gate_allows_ops_draft_prose_in_body(tmp_path: Path) -> None:
    signed = tmp_path / "cal.md"
    signed.write_text(
        "**Status: gating 10-item set COMPLETE**\n\n"
        "GM-F note: Ops' draft distractors were replaced.\n",
        encoding="utf-8",
    )
    with patch("sstrf_scoring_evidence.CALIBRATION_SET", signed):
        assert_calibration_set_signed()


def test_calibration_gate_passes_signed_repo_file() -> None:
    assert_calibration_set_signed()


def test_seventeen_judgements_per_trial() -> None:
    assert len(all_trial_cell_ids()) == 17
    assert JUDGEMENTS_PER_TRIAL == 17


def test_rubric_prompt_verbatim_snapshot() -> None:
    block = build_rubric_block()
    assert PROPOSITIONS_VERBATIM["P1"] in block
    assert "Clearly exhibited" in block
    assert SCALE_VERBATIM.strip() in block
    assert INSTRUCTIONS_VERBATIM in block
    assert "vice_principal_001" in block


def test_parse_trial_scores() -> None:
    payload = {cell_id: 2 for cell_id in all_trial_cell_ids()}
    payload["P2"] = 1
    scores = parse_trial_scores(json.dumps(payload))
    assert scores["P2"] == 1
    assert len(scores) == 17


def test_judge_primary_is_gpt4o() -> None:
    assert JUDGE_PRIMARY_MODEL == "gpt-4o"
    specs = resolve_judge_chain()
    assert specs[0].model_id == "gpt-4o"
    assert all("anthropic" not in s.profile_id for s in specs)


def test_score_all_trials_blocked_without_calibration(tmp_path: Path) -> None:
    from sstrf_rq1_scoring import assert_calibration_gate_passed

    with patch("sstrf_rq1_scoring.CALIBRATION_GATE_RESULT", tmp_path / "missing.json"):
        with pytest.raises(RuntimeError, match="Calibration gate not passed"):
            assert_calibration_gate_passed()


def test_manifest_schema_round_trip(tmp_path: Path) -> None:
    manifest = {
        "schema_version": 1,
        "scored_at": "2026-08-11T00:00:00+00:00",
        "calibration_gate": {"passed": True, "judge_model_id": "gpt-4o-mini", "pass_1_correct": 9, "pass_2_correct": 10},
        "judge_models_used": ["gpt-4o-mini"],
        "drift_check": {"sample_seed": 42, "sampled_cells": [], "mark_disagreements": 0, "rescore_triggered": False},
        "study_summary": {
            "trials_passed": 8,
            "trials_total": 10,
            "study_pass": True,
            "framing_disclosure": "Reports how consistently",
        },
        "trials": [
            {
                "trial_label": "trial-A",
                "pass_1": {"P1": 2, "P2": 2, "P3": 2, "P4": 1, "P5": 2},
                "pass_2": {"P1": 2, "P2": 2, "P3": 2, "P4": 1, "P5": 2},
                "adjudicated": {"P1": 2, "P2": 2, "P3": 2, "P4": 1, "P5": 2},
                "adjudication_rules": {"P1": "agree", "P2": "agree", "P3": "agree", "P4": "agree", "P5": "agree"},
                "human_notes": {},
                "trial_pass": True,
                "judge_model_id": "gpt-4o-mini",
            }
        ],
        "human_adjudication_count": 0,
        "disclosure": "All results reported regardless of outcome per pre-reg §7.1",
    }
    path = tmp_path / "phase_v_scoring_manifest.json"
    path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    loaded = json.loads(path.read_text(encoding="utf-8"))
    assert loaded["schema_version"] == 1
    assert loaded["study_summary"]["study_pass"] is True


@pytest.mark.asyncio
async def test_run_judge_pass_parse_failure_persisted() -> None:
    from sstrf_scoring_judge import run_judge_pass

    evidence = _sample_evidence()

    async def bad_call(**kwargs):
        return ("not json", "gpt-4o")

    spec = resolve_judge_chain()[0]
    result = await run_judge_pass(evidence, pass_seed=5, profile_spec=spec, judge_call=bad_call)
    assert result.parse_failed == all_trial_cell_ids()
    trial_entry = {
        "pass_1": result.scores,
        "pass_2": result.scores,
        "parse_failed_pass_1": result.parse_failed,
        "parse_failed_pass_2": [],
    }
    failed = apply_judge_parse_failures(trial_entry)
    assert set(failed) == set(all_trial_cell_ids())
    assert trial_entry["adjudication_rules"]["P2"] == "judge_parse_failed"


def test_profile_spec_from_calibration_gate_uses_profile_id() -> None:
    spec = profile_spec_from_calibration_gate(
        {
            "judge_profile_id": "openrouter_default",
            "judge_model_id": "openai/gpt-4o-mini",
        }
    )
    assert spec.profile_id == "openrouter_default"
    assert spec.model_id == "openai/gpt-4o-mini"


def test_judge_chain_pins_models() -> None:
    specs = resolve_judge_chain()
    assert specs[0].model_id == JUDGE_PRIMARY_MODEL
    assert specs[2].model_id == JUDGE_OPENROUTER_MODEL


def test_probe_items_count_and_expectations() -> None:
    from sstrf_scoring_judge import PROBE_ITEMS

    assert len(PROBE_ITEMS) == 2
    item_11 = next(i for i in PROBE_ITEMS if i["item_id"] == 11)
    item_12 = next(i for i in PROBE_ITEMS if i["item_id"] == 12)
    assert item_11["expected_proposition"] == "P4"
    assert item_11["expected_score"] == 0
    assert "Primary 2 materials" in item_11["passage"]
    assert "P2 materials" not in item_11["passage"]
    assert item_12["expected_proposition"] == "P1"
    assert item_12["expected_score"] == 0


def _gate_results_from_overrides(
    overrides: dict[int, tuple[str, int]],
) -> list[CalibrationItemResult]:
    results: list[CalibrationItemResult] = []
    for item in CALIBRATION_ITEMS:
        item_id = int(item["item_id"])
        if item_id in overrides:
            actual_prop, actual_score = overrides[item_id]
        else:
            actual_prop = str(item["expected_proposition"])
            actual_score = int(item["expected_score"])
        results.append(
            CalibrationItemResult(
                item_id=item_id,
                expected_proposition=str(item["expected_proposition"]),
                expected_score=int(item["expected_score"]),
                actual_proposition=actual_prop,
                actual_score=actual_score,
                scored_correctly=(
                    actual_prop == item["expected_proposition"]
                    and actual_score == item["expected_score"]
                ),
            )
        )
    return results


def test_calibration_gate_has_fifteen_gating_items() -> None:
    assert len(CALIBRATION_ITEMS) == 15
    by_prop: dict[str, list[int]] = {pid: [] for pid in ("P1", "P2", "P3", "P4", "P5")}
    for item in CALIBRATION_ITEMS:
        by_prop[item["expected_proposition"]].append(int(item["expected_score"]))
    for scores in by_prop.values():
        assert sorted(scores) == [-1, 1, 2]


def test_c1_c5_calibration_content_verbatim() -> None:
    partial = [item for item in CALIBRATION_ITEMS if item.get("item_kind") == "partial_presence"]
    assert len(partial) == 5
    c1 = next(item for item in partial if item.get("calibration_id") == "C1")
    assert "I suppose the department does set the direction" in c1["passage"]
    c5 = next(item for item in partial if item.get("calibration_id") == "C5")
    assert "quite prescriptive" in c5["passage"]


def test_no_proposition_double_miss_groups_by_proposition() -> None:
    items = _gate_results_from_overrides({9: ("P5", 1), 17: ("P5", 2)})
    assert count_gate_correct(items) == 13
    assert proposition_incorrect_counts(items)["P5"] == 2
    assert not no_proposition_double_miss(items)
    assert no_proposition_double_miss(_gate_results_from_overrides({13: ("P1", 2)}))


def test_calibration_gate_passes_adequate_judge() -> None:
    items = _gate_results_from_overrides({13: ("P1", 2), 4: ("P2", 2)})
    assert count_gate_correct(items) == 13
    assert calibration_gate_passes(pass_1_items=items, pass_2_items=items)


def test_calibration_gate_rejects_p5_phase_v_regression_despite_aggregate() -> None:
    """13/15 both passes but two P5 misses — old 8/10 gate would have passed."""
    items = _gate_results_from_overrides({9: ("P5", 1), 17: ("P5", 2)})
    assert count_gate_correct(items) == 13
    assert not no_proposition_double_miss(items)
    assert not calibration_gate_passes(pass_1_items=items, pass_2_items=items)


def test_calibration_gate_rejects_over_reading_all_partial_items() -> None:
    overrides = {
        int(item["item_id"]): (str(item["expected_proposition"]), 2)
        for item in CALIBRATION_ITEMS
        if int(item["expected_score"]) == 1
    }
    items = _gate_results_from_overrides(overrides)
    assert count_gate_correct(items) == 10
    assert not calibration_gate_passes(pass_1_items=items, pass_2_items=items)


def test_calibration_gate_rejects_below_aggregate_threshold() -> None:
    items = _gate_results_from_overrides(
        {
            13: ("P1", 2),
            14: ("P2", 2),
            15: ("P3", 2),
            16: ("P4", 2),
        }
    )
    assert count_gate_correct(items) == 11
    assert not calibration_gate_passes(pass_1_items=items, pass_2_items=items)


def test_calibration_gate_ignores_probe_scores() -> None:
    perfect = _gate_results_from_overrides({})
    assert calibration_gate_passes(pass_1_items=perfect, pass_2_items=perfect)
    imperfect = _gate_results_from_overrides({1: ("P1", 1), 2: ("P1", 1)})
    assert count_gate_correct(imperfect) == 13
    assert not calibration_gate_passes(pass_1_items=imperfect, pass_2_items=perfect)


@pytest.mark.asyncio
async def test_run_calibration_pass_gate_independent_of_probe_wrong_answers() -> None:
    from sstrf_scoring_judge import (
        CALIBRATION_ITEMS,
        PROBE_ITEMS,
        calibration_gate_passes,
        run_calibration_pass,
    )

    async def fake_call(**kwargs):
        user = kwargs["messages"][1]["content"]
        for item in CALIBRATION_ITEMS + PROBE_ITEMS:
            if item["passage"] in user:
                return (
                    json.dumps(
                        {
                            "proposition": item["expected_proposition"],
                            "score": item["expected_score"],
                        }
                    ),
                    "gpt-4o-mini",
                )
        return json.dumps({"proposition": "P1", "score": -1}), "gpt-4o-mini"

    spec = resolve_judge_chain()[0]
    perfect = await run_calibration_pass(pass_seed=1, profile_spec=spec, judge_call=fake_call)
    assert perfect.gate_correct == len(CALIBRATION_ITEMS)
    assert len(perfect.gate_item_results) == len(CALIBRATION_ITEMS)
    assert all(g.scored_correctly for g in perfect.gate_item_results)
    assert all(p.scored_correctly for p in perfect.probe_results)

    async def wrong_probes_call(**kwargs):
        user = kwargs["messages"][1]["content"]
        for item in CALIBRATION_ITEMS:
            if item["passage"] in user:
                return (
                    json.dumps(
                        {
                            "proposition": item["expected_proposition"],
                            "score": item["expected_score"],
                        }
                    ),
                    "gpt-4o-mini",
                )
        for probe in PROBE_ITEMS:
            if probe["passage"] in user:
                return json.dumps({"proposition": probe["expected_proposition"], "score": -1}), "gpt-4o-mini"
        return json.dumps({"proposition": "P1", "score": 0}), "gpt-4o-mini"

    wrong_probes = await run_calibration_pass(
        pass_seed=2, profile_spec=spec, judge_call=wrong_probes_call
    )
    assert wrong_probes.gate_correct == len(CALIBRATION_ITEMS)
    assert len(wrong_probes.gate_item_results) == len(CALIBRATION_ITEMS)
    assert all(g.scored_correctly for g in wrong_probes.gate_item_results)
    assert all(not p.scored_correctly for p in wrong_probes.probe_results)
    assert calibration_gate_passes(
        pass_1_items=perfect.gate_item_results,
        pass_2_items=wrong_probes.gate_item_results,
    )
    assert calibration_gate_passes(
        pass_1_items=wrong_probes.gate_item_results,
        pass_2_items=wrong_probes.gate_item_results,
    ) == calibration_gate_passes(
        pass_1_items=perfect.gate_item_results,
        pass_2_items=perfect.gate_item_results,
    )


def test_finalize_requires_drift_scores(tmp_path: Path) -> None:
    from sstrf_rq1_scoring import cmd_finalize

    state_path = tmp_path / "scoring_state.json"
    state_path.write_text(
        json.dumps(
            {
                "trials": {
                    "trial-A": {
                        "pass_1": _sample_trial_scores(),
                        "pass_2": _sample_trial_scores(),
                    }
                },
                "drift_sample": [{"trial_label": "trial-A", "cell_id": "P2", "proposition": "P2"}],
                "drift_sample_seed": 42,
            }
        ),
        encoding="utf-8",
    )
    with patch("sstrf_rq1_scoring.SCORING_STATE", state_path):
        with patch("sstrf_rq1_scoring.load_trial_label_map", return_value={"trial-A": {}}):
            with pytest.raises(RuntimeError, match="drift_scores"):
                cmd_finalize(argparse.Namespace(drift_sample_seed=42))


@pytest.mark.asyncio
async def test_run_judge_pass_mocked() -> None:
    from sstrf_scoring_judge import run_judge_pass

    evidence = _sample_evidence()
    payload = {cell_id: 2 for cell_id in all_trial_cell_ids()}
    payload["P2"] = 1

    async def fake_call(**kwargs):
        return (json.dumps(payload), "gpt-4o")

    spec = resolve_judge_chain()[0]
    result = await run_judge_pass(evidence, pass_seed=5, profile_spec=spec, judge_call=fake_call)
    assert result.scores["P2"] == 1
    assert len(result.scores) == 17
    assert result.judge_model_id == "gpt-4o"


def test_human_review_queue_builds() -> None:
    pass_1 = _sample_trial_scores()
    pass_2 = _sample_trial_scores()
    pass_2["P2"] = 0
    trials = {
        "trial-C": {
            "pass_1": pass_1,
            "pass_2": pass_2,
            "adjudicated": {"P2": None},
            "adjudication_rules": {"P2": "human_required"},
        }
    }
    drift = [{"trial_label": "trial-C", "cell_id": "P2", "proposition": "P2"}]
    queue = build_human_review_queue(trials=trials, drift_sample=drift)
    assert queue["adjudication_required"][0]["reason"] == "diff_ge_2"


def test_assign_trial_labels_count() -> None:
    trials = [{"seed": 101 + i, "attempts": [{"attempt_number": 1, "full_gate_passed": True, "simulation_id": f"s{i}"}]} for i in range(10)]
    mapping = assign_trial_labels(trials, assignment_seed=7)
    assert len(mapping) == 10
    assert all(label.startswith("trial-") for label in mapping)


@pytest.mark.asyncio
async def test_assemble_trial_evidence_passes_simulation_id_keyword() -> None:
    record = TrialRecord(
        trial_label="trial-A",
        seed=101,
        simulation_id="abc123",
        elicitation_manifest={
            "agents": [
                {
                    "persona_id": "teacher_001",
                    "role": "teacher",
                    "agent_name": "Miss M",
                    "output_path": "unused.json",
                }
            ]
        },
    )

    async def fake_bundle(sqlite_path: str, *, simulation_id: str):
        assert sqlite_path == "/tmp/test.sqlite"
        assert simulation_id == "abc123"
        return {
            "transcript": [
                {
                    "round_number": 1,
                    "turn_index": 0,
                    "agent_id": "teacher_001_003",
                    "agent_name": "Miss M",
                    "agent_role": "teacher",
                    "raw_response": "School filters policy.",
                }
            ]
        }

    with patch(
        "sstrf_scoring_evidence.load_elicitation_responses",
        return_value=[{"persona_id": "teacher_001", "role": "teacher", "agent_name": "Miss M", "raw_response": "x"}],
    ):
        evidence = await assemble_trial_evidence(
            record=record,
            sqlite_path=Path("/tmp/test.sqlite"),
            get_bundle=fake_bundle,
        )
    assert evidence.trial_label == "trial-A"
    assert len(evidence.transcript) == 1


def test_prepare_adjudication_writes_queue(tmp_path: Path) -> None:
    pass_1 = _sample_trial_scores()
    pass_2 = _sample_trial_scores()
    pass_1["P2"] = 2
    pass_2["P2"] = 0
    trials = {"trial-A": {"pass_1": pass_1, "pass_2": pass_2}}
    queue, drift, meta = prepare_trials_for_human_review(
        trials,
        drift_sampling_mode="cell",
        drift_sample_seed=99,
    )
    assert len(drift) == min(10, JUDGEMENTS_PER_TRIAL)
    assert meta["drift_check_design"] == "cell_level_v1_4"
    assert any(item["cell_id"] == "P2" for item in queue["adjudication_required"])
    assert trials["trial-A"]["adjudication_rules"]["P2"] == "human_required"


def test_sample_drift_trials_expands_to_sixty_eight_cells() -> None:
    labels = [f"trial-{c}" for c in "ABCDEFGHIJ"]
    sampled = sample_drift_trials(labels, sample_seed=515)
    assert len(sampled) == 4
    cells = expand_drift_trials_to_cells(sampled)
    assert len(cells) == 4 * JUDGEMENTS_PER_TRIAL
    assert all({"trial_label", "cell_id", "proposition"} <= set(c.keys()) for c in cells)


def test_sample_drift_trials_reproducible_with_v15_seed() -> None:
    labels = [f"trial-{c}" for c in "ABCDEFGHIJ"]
    a = sample_drift_trials(labels, sample_seed=515)
    b = sample_drift_trials(labels, sample_seed=515)
    assert a == b
    assert a != sample_drift_trials(labels, sample_seed=42)


def test_prepare_adjudication_trial_mode_default() -> None:
    trials = {
        f"trial-{c}": {"pass_1": _sample_trial_scores(), "pass_2": _sample_trial_scores()}
        for c in "ABCDE"
    }
    queue, drift, meta = prepare_trials_for_human_review(trials)
    assert meta["drift_check_design"] == "trial_level_v1_5"
    assert meta["drift_trial_sample_seed"] == 515
    assert len(meta["drift_sampled_trials"]) == 4
    assert len(drift) == 4 * JUDGEMENTS_PER_TRIAL


def test_drift_disagree_threshold_scales_with_sample_size() -> None:
    assert drift_disagree_threshold(10) == 3
    assert drift_disagree_threshold(20) == 6
    assert drift_rescore_triggered(mark_disagreements=5, sample_size=20) is False
    assert drift_rescore_triggered(mark_disagreements=6, sample_size=20) is True


def test_build_tier1_plausibility_summary() -> None:
    trials = {
        "trial-A": {"pass_1": _sample_trial_scores(), "pass_2": _sample_trial_scores()}
    }
    summary = build_tier1_plausibility_summary(trials)
    assert summary["cell_count"] == JUDGEMENTS_PER_TRIAL
    assert summary["trial_count"] == 1
    assert summary["trial_verdicts"][0]["trial_pass"] is True


def test_build_tier2_elicitation_packet_omits_transcript(tmp_path: Path) -> None:
    from sstrf_scoring_evidence import build_tier2_elicitation_packet, TrialRecord

    elic_dir = tmp_path / "elicitation"
    elic_dir.mkdir()
    elic_path = elic_dir / "agent.json"
    elic_path.write_text(
        json.dumps(
            {
                "persona_id": "teacher_001",
                "role": "teacher",
                "agent_name": "Miss M",
                "raw_response": "We follow school guidance.",
            }
        ),
        encoding="utf-8",
    )
    record = TrialRecord(
        trial_label="trial-A",
        seed=101,
        simulation_id="abc",
        elicitation_manifest={
            "agents": [
                {
                    "persona_id": "teacher_001",
                    "role": "teacher",
                    "agent_name": "Miss M",
                    "output_path": str(elic_path),
                }
            ]
        },
    )
    packet = build_tier2_elicitation_packet(record)
    assert "elicitation" in packet
    assert "transcript" not in packet
    assert "trial_label" not in packet


@pytest.mark.asyncio
async def test_build_stage1_escalation_packets_adds_transcript() -> None:
    from sstrf_scoring_evidence import TrialRecord, build_stage1_escalation_packets

    record = TrialRecord(
        trial_label="trial-A",
        seed=101,
        simulation_id="abc123",
        elicitation_manifest={
            "agents": [
                {
                    "persona_id": "teacher_001",
                    "role": "teacher",
                    "agent_name": "Miss M",
                    "output_path": "unused.json",
                }
            ]
        },
    )
    mapping = {"trial-A": {"seed": 101, "simulation_id": "abc123"}}
    manifest = {
        "trials": [
            {
                "seed": 101,
                "attempts": [
                    {
                        "attempt_number": 1,
                        "full_gate_passed": True,
                        "simulation_id": "abc123",
                        "elicitation": record.elicitation_manifest,
                    }
                ],
            }
        ]
    }

    async def fake_bundle(sqlite_path: str, *, simulation_id: str):
        return {
            "transcript": [
                {
                    "round_number": 1,
                    "turn_index": 0,
                    "agent_id": "teacher_001_003",
                    "agent_name": "Miss M",
                    "agent_role": "teacher",
                    "raw_response": "School filters policy.",
                }
            ]
        }

    with patch(
        "sstrf_scoring_evidence.load_elicitation_responses",
        return_value=[{"persona_id": "teacher_001", "role": "teacher", "agent_name": "Miss M", "raw_response": "x"}],
    ):
        out = await build_stage1_escalation_packets(
            [{"trial_label": "trial-A", "proposition": "P2"}],
            mapping=mapping,
            manifest=manifest,
            sqlite_path=Path("/tmp/test.sqlite"),
            get_bundle=fake_bundle,
        )
    assert out["disputed_cells"][0]["proposition"] == "P2"
    assert "transcript" in out["packets"]["trial-A"]
    assert out["packets"]["trial-A"]["propositions_to_rescore"] == ["P2"]


def test_import_records_drift_disagreements() -> None:
    scores = _sample_trial_scores()
    trials = {
        "trial-F": {
            "pass_1": scores,
            "pass_2": scores,
            "adjudicated": scores,
        }
    }
    cell = trial_cell_id("P4", SCORED_STAFF_AGENTS[0])
    drift_scores = [
        {"trial_label": "trial-F", "cell_id": cell, "score": 1},
    ]
    assert count_drift_disagreements(trials, drift_scores) == 1

"""Adjudication, drift sampling, and pass/fail for SSTRF RQ1 scoring (GM-F v2)."""

from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Any

from sstrf_scoring_cells import (
    JUDGEMENTS_PER_TRIAL,
    SCORED_STAFF_AGENTS,
    all_trial_cell_ids,
    proposition_for_cell,
    trial_cell_id,
)

TOTAL_CELLS = JUDGEMENTS_PER_TRIAL * 10  # 170 across 10 trials

# Legacy cell-level drift check (pre-reg v1.4; superseded by v1.5 trial-level design).
DRIFT_SAMPLE_SIZE = 10
DRIFT_CELL_SAMPLE_SIZE = DRIFT_SAMPLE_SIZE
DRIFT_CELL_SAMPLE_SEED = 42

# Trial-level drift check (pre-reg v1.5 — GM-F §7).
DRIFT_TRIAL_SAMPLE_SIZE = 4
DRIFT_TRIAL_CELL_COUNT = DRIFT_TRIAL_SAMPLE_SIZE * JUDGEMENTS_PER_TRIAL
DRIFT_TRIAL_SAMPLE_SEED = 515

DRIFT_DISAGREE_THRESHOLD = 3  # legacy default for n=10 cell-level samples

FRAMING_DISCLOSURE = (
    "Reports how consistently the simulation reproduces the case across stochastic "
    "(seed) variation. Trials share one fixture/case/model and differ only by seed — "
    "not 10 independent statistical replications."
)


@dataclass
class AdjudicatedCell:
    proposition: str
    pass_1: int
    pass_2: int
    adjudicated: int | None
    adjudication_rule: str
    human_required: bool


def adjudicate_cell(pass_1: int, pass_2: int) -> AdjudicatedCell:
    prop_placeholder = "P?"
    if pass_1 == pass_2:
        return AdjudicatedCell(
            proposition=prop_placeholder,
            pass_1=pass_1,
            pass_2=pass_2,
            adjudicated=pass_1,
            adjudication_rule="agree",
            human_required=False,
        )
    if pass_1 == -1 or pass_2 == -1:
        return AdjudicatedCell(
            proposition=prop_placeholder,
            pass_1=pass_1,
            pass_2=pass_2,
            adjudicated=None,
            adjudication_rule="human_required",
            human_required=True,
        )
    if abs(pass_1 - pass_2) >= 2:
        return AdjudicatedCell(
            proposition=prop_placeholder,
            pass_1=pass_1,
            pass_2=pass_2,
            adjudicated=None,
            adjudication_rule="human_required",
            human_required=True,
        )
    lower = min(pass_1, pass_2)
    return AdjudicatedCell(
        proposition=prop_placeholder,
        pass_1=pass_1,
        pass_2=pass_2,
        adjudicated=lower,
        adjudication_rule="lower_of_one",
        human_required=False,
    )


def adjudicate_trial(
    pass_1: dict[str, int],
    pass_2: dict[str, int],
    *,
    human_scores: dict[str, int] | None = None,
) -> tuple[dict[str, int | None], dict[str, str], list[str]]:
    adjudicated: dict[str, int | None] = {}
    rules: dict[str, str] = {}
    human_required: list[str] = []
    human_scores = human_scores or {}
    for cell_id in all_trial_cell_ids():
        cell = adjudicate_cell(int(pass_1[cell_id]), int(pass_2[cell_id]))
        cell.proposition = cell_id
        rules[cell_id] = cell.adjudication_rule
        if cell.human_required:
            human_required.append(cell_id)
            if cell_id in human_scores:
                adjudicated[cell_id] = int(human_scores[cell_id])
            else:
                adjudicated[cell_id] = None
        else:
            adjudicated[cell_id] = cell.adjudicated
    return adjudicated, rules, human_required


def cell_adjudication_rule(
    pass_1: dict[str, int],
    pass_2: dict[str, int],
    cell_id: str,
    *,
    parse_failed: set[str] | None = None,
) -> str:
    if parse_failed and cell_id in parse_failed:
        return "judge_parse_failed"
    return adjudicate_cell(int(pass_1[cell_id]), int(pass_2[cell_id])).adjudication_rule


def collect_auto_resolved_diff_of_one_cells(
    trials: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    """Cells where passes differ by 1 and the lower score auto-stands (visibility only)."""
    cells: list[dict[str, Any]] = []
    for label in sorted(trials):
        trial = trials[label]
        pass_1 = trial.get("pass_1") or {}
        pass_2 = trial.get("pass_2") or {}
        parse_failed = set(trial.get("parse_failed_pass_1") or []) | set(
            trial.get("parse_failed_pass_2") or []
        )
        for cell_id in all_trial_cell_ids():
            if cell_id in parse_failed:
                continue
            p1 = int(pass_1[cell_id])
            p2 = int(pass_2[cell_id])
            cell = adjudicate_cell(p1, p2)
            if cell.adjudication_rule != "lower_of_one":
                continue
            cells.append(
                {
                    "trial_label": label,
                    "cell_id": cell_id,
                    "proposition": proposition_for_cell(cell_id),
                    "pass_1": p1,
                    "pass_2": p2,
                    "adjudicated": cell.adjudicated,
                    "auto_resolved_diff_of_one": True,
                }
            )
    return cells


def count_adjudication_rules(trials: dict[str, dict[str, Any]]) -> dict[str, int]:
    counts = {
        "agree": 0,
        "lower_of_one": 0,
        "human_required": 0,
        "judge_parse_failed": 0,
    }
    for trial in trials.values():
        pass_1 = trial.get("pass_1") or {}
        pass_2 = trial.get("pass_2") or {}
        parse_failed = set(trial.get("parse_failed_pass_1") or []) | set(
            trial.get("parse_failed_pass_2") or []
        )
        for cell_id in all_trial_cell_ids():
            rule = cell_adjudication_rule(pass_1, pass_2, cell_id, parse_failed=parse_failed)
            counts[rule] = counts.get(rule, 0) + 1
    return counts


def _agent_scores(scores: dict[str, int], proposition: str) -> list[int]:
    return [int(scores[trial_cell_id(proposition, agent)]) for agent in SCORED_STAFF_AGENTS]


def _n_clear(scores: dict[str, int], proposition: str) -> int:
    return sum(1 for val in _agent_scores(scores, proposition) if val == 2)


def trial_passes(scores: dict[str, int]) -> bool:
    """GM-F v2 §2.4 — per-trial pass rule on adjudicated cell scores."""
    if int(scores["P2"]) == -1:
        return False
    for prop in ("P1", "P3"):
        if any(val == -1 for val in _agent_scores(scores, prop)):
            return False
    if _n_clear(scores, "P1") < 3:
        return False
    if _n_clear(scores, "P3") < 3:
        return False
    if int(scores["P2"]) != 2:
        return False
    if _n_clear(scores, "P4") < 2:
        return False
    if _n_clear(scores, "P5") < 2:
        return False
    return True


def study_passes(trial_results: list[bool]) -> bool:
    return sum(1 for passed in trial_results if passed) >= 8


def sample_drift_cells(
    trial_labels: list[str],
    *,
    sample_seed: int,
    sample_size: int = DRIFT_SAMPLE_SIZE,
) -> list[dict[str, str]]:
    """Legacy cell-level sampling: random cells from the 50-cell grid (pre-reg v1.4)."""
    cells = [
        {"trial_label": label, "cell_id": cell_id, "proposition": proposition_for_cell(cell_id)}
        for label in sorted(trial_labels)
        for cell_id in all_trial_cell_ids()
    ]
    rng = random.Random(sample_seed)
    rng.shuffle(cells)
    return cells[:sample_size]


def sample_drift_trials(
    trial_labels: list[str],
    *,
    sample_seed: int,
    trial_count: int = DRIFT_TRIAL_SAMPLE_SIZE,
) -> list[str]:
    """Trial-level sampling (pre-reg v1.5): select N trials by seed, expand to all propositions."""
    labels = sorted(trial_labels)
    rng = random.Random(sample_seed)
    shuffled = labels.copy()
    rng.shuffle(shuffled)
    return shuffled[: min(trial_count, len(shuffled))]


def expand_drift_trials_to_cells(trial_labels: list[str]) -> list[dict[str, str]]:
    cells: list[dict[str, str]] = []
    for label in sorted(trial_labels):
        for cell_id in all_trial_cell_ids():
            cells.append(
                {
                    "trial_label": label,
                    "cell_id": cell_id,
                    "proposition": proposition_for_cell(cell_id),
                }
            )
    return cells


def drift_disagree_threshold(sample_size: int) -> int:
    """More than 25% disagreement (e.g. 3+ of 10, 6+ of 20)."""
    return int(sample_size * 0.25) + 1


def drift_rescore_triggered(
    *,
    mark_disagreements: int,
    sample_size: int = DRIFT_SAMPLE_SIZE,
    threshold: int | None = None,
) -> bool:
    limit = threshold if threshold is not None else drift_disagree_threshold(sample_size)
    return mark_disagreements >= limit


def apply_judge_parse_failures(trial: dict[str, Any]) -> list[str]:
    """Mark cells that failed judge JSON parse as human-required."""
    failed = sorted(
        set(trial.get("parse_failed_pass_1") or [])
        | set(trial.get("parse_failed_pass_2") or [])
    )
    if not failed:
        trial.pop("judge_parse_failed", None)
        return []
    trial["judge_parse_failed"] = failed
    rules = trial.setdefault("adjudication_rules", {})
    adjudicated = trial.setdefault("adjudicated", {})
    for cell_id in failed:
        rules[cell_id] = "judge_parse_failed"
        adjudicated[cell_id] = None
    return failed


def build_tier1_plausibility_summary(
    trials: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    """Tier 1: all adjudicated cell scores + trial pass/fail verdicts (no raw evidence)."""
    cell_scores: list[dict[str, Any]] = []
    trial_verdicts: list[dict[str, Any]] = []
    cell_ids = all_trial_cell_ids()
    for label in sorted(trials):
        trial = trials[label]
        pass_1 = trial.get("pass_1") or {}
        pass_2 = trial.get("pass_2") or {}
        adjudicated, rules, _required = adjudicate_trial(pass_1, pass_2)
        work = {**trial, "adjudicated": adjudicated, "adjudication_rules": rules}
        apply_judge_parse_failures(work)
        adjudicated = work.get("adjudicated") or {}
        rules = work.get("adjudication_rules") or {}
        final_scores = {
            cell_id: int(adjudicated[cell_id])
            for cell_id in cell_ids
            if adjudicated.get(cell_id) is not None
        }
        for cell_id in cell_ids:
            cell_scores.append(
                {
                    "trial_label": label,
                    "cell_id": cell_id,
                    "proposition": proposition_for_cell(cell_id),
                    "adjudicated_score": adjudicated.get(cell_id),
                    "adjudication_rule": rules.get(cell_id),
                }
            )
        trial_verdicts.append(
            {
                "trial_label": label,
                "trial_pass": trial_passes(final_scores)
                if len(final_scores) == JUDGEMENTS_PER_TRIAL
                else None,
                "scores": final_scores,
            }
        )
    return {
        "design": "tier1_plausibility_v2",
        "cell_count": len(cell_scores),
        "trial_count": len(trial_verdicts),
        "cell_scores": cell_scores,
        "trial_verdicts": trial_verdicts,
    }


def build_human_review_queue(
    *,
    trials: dict[str, dict[str, Any]],
    drift_sample: list[dict[str, str]],
    drift_metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    adjudication_required: list[dict[str, Any]] = []
    for label, trial in trials.items():
        pass_1 = trial.get("pass_1") or {}
        pass_2 = trial.get("pass_2") or {}
        rules = trial.get("adjudication_rules") or {}
        for cell_id in all_trial_cell_ids():
            rule = rules.get(cell_id)
            if rule not in ("human_required", "judge_parse_failed"):
                continue
            if rule == "judge_parse_failed":
                reason = "judge_parse_failed"
            elif pass_1.get(cell_id) == -1 or pass_2.get(cell_id) == -1:
                reason = "minus_one"
            else:
                reason = "diff_ge_2"
            adjudication_required.append(
                {
                    "trial_label": label,
                    "cell_id": cell_id,
                    "proposition": proposition_for_cell(cell_id),
                    "pass_1": pass_1.get(cell_id),
                    "pass_2": pass_2.get(cell_id),
                    "reason": reason,
                }
            )
    drift_check_sample = []
    for cell in drift_sample:
        label = cell["trial_label"]
        cell_id = str(cell.get("cell_id") or cell.get("proposition", ""))
        if ":" not in cell_id and cell_id in {"P1", "P2", "P3", "P4", "P5"}:
            cell_id = str(cell.get("proposition", cell_id))
        adj = (trials.get(label) or {}).get("adjudicated") or {}
        drift_check_sample.append(
            {
                "trial_label": label,
                "cell_id": cell_id,
                "proposition": proposition_for_cell(cell_id),
                "adjudicated_score": adj.get(cell_id),
            }
        )
    out: dict[str, Any] = {
        "adjudication_required": adjudication_required,
        "drift_check_sample": drift_check_sample,
    }
    if drift_metadata:
        out.update(drift_metadata)
    return out


def finalize_study_summary(
    *,
    trials: list[dict[str, Any]],
) -> dict[str, Any]:
    passed = [bool(t.get("trial_pass")) for t in trials]
    return {
        "trials_passed": sum(1 for p in passed if p),
        "trials_total": len(trials),
        "study_pass": study_passes(passed),
        "framing_disclosure": FRAMING_DISCLOSURE,
    }


def apply_human_scores(
    trials: dict[str, dict[str, Any]],
    imported: dict[str, Any],
) -> None:
    for entry in imported.get("scores") or []:
        label = str(entry["trial_label"])
        cell_id = str(entry.get("cell_id") or entry.get("proposition"))
        score = int(entry["score"])
        trial = trials.setdefault(label, {})
        adjudicated = trial.setdefault("adjudicated", {})
        adjudicated[cell_id] = score
        notes = trial.setdefault("human_notes", {})
        if entry.get("note"):
            notes[cell_id] = str(entry["note"])


def count_drift_disagreements(
    trials: dict[str, dict[str, Any]],
    drift_scores: list[dict[str, Any]],
) -> int:
    """Count drift-sample cells where Mark's score differs from auto-adjudicated."""
    disagreements = 0
    for entry in drift_scores:
        label = str(entry["trial_label"])
        cell_id = str(entry.get("cell_id") or entry.get("proposition"))
        mark_score = int(entry["score"])
        trial = trials.get(label) or {}
        adjudicated = trial.get("adjudicated") or {}
        ref = adjudicated.get(cell_id)
        if ref is None:
            raise ValueError(
                f"drift check {label} {cell_id}: no auto-adjudicated score — "
                "run --prepare-adjudication first"
            )
        if int(ref) != mark_score:
            disagreements += 1
    return disagreements


def prepare_trials_for_human_review(
    trials: dict[str, dict[str, Any]],
    *,
    drift_sampling_mode: str = "trial",
    drift_sample_seed: int = DRIFT_CELL_SAMPLE_SEED,
    drift_trial_sample_seed: int = DRIFT_TRIAL_SAMPLE_SEED,
) -> tuple[dict[str, Any], list[dict[str, str]], dict[str, Any]]:
    """Auto-adjudicate judge passes and build Mark's review queue payload."""
    prepared: dict[str, dict[str, Any]] = {}
    for label in sorted(trials):
        trial = trials[label]
        if "pass_1" not in trial or "pass_2" not in trial:
            raise ValueError(f"{label} missing pass_1/pass_2 — run --score-all-trials first")
        human_scores = {
            pid: int(val)
            for pid, val in (trial.get("adjudicated") or {}).items()
            if val is not None
        }
        adjudicated, rules, _required = adjudicate_trial(
            trial["pass_1"],
            trial["pass_2"],
            human_scores=human_scores,
        )
        auto_scores = {pid: val for pid, val in adjudicated.items() if val is not None}
        prepared[label] = {
            **trial,
            "adjudicated": auto_scores,
            "adjudication_rules": rules,
        }
        apply_judge_parse_failures(prepared[label])
        trials[label] = prepared[label]

    if drift_sampling_mode == "cell":
        drift_sample = sample_drift_cells(list(prepared.keys()), sample_seed=drift_sample_seed)
        drift_metadata = {
            "drift_check_design": "cell_level_v1_4",
            "drift_sample_seed": drift_sample_seed,
            "drift_sampled_trials": None,
        }
    elif drift_sampling_mode == "trial":
        sampled_trials = sample_drift_trials(
            list(prepared.keys()),
            sample_seed=drift_trial_sample_seed,
        )
        drift_sample = expand_drift_trials_to_cells(sampled_trials)
        drift_metadata = {
            "drift_check_design": "trial_level_v1_5",
            "drift_trial_sample_seed": drift_trial_sample_seed,
            "drift_sampled_trials": sampled_trials,
            "drift_sample_cell_count": len(drift_sample),
        }
    else:
        raise ValueError(f"unknown drift_sampling_mode {drift_sampling_mode!r}")

    queue = build_human_review_queue(
        trials=prepared,
        drift_sample=drift_sample,
        drift_metadata=drift_metadata,
    )
    return queue, drift_sample, drift_metadata

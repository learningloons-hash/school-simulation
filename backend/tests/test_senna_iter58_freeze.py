"""senna-iter-58 Part B — study seeds and platform freeze manifest."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

_REPO = Path(__file__).resolve().parents[2]
_DIAG = _REPO / "docs" / "diagnostics"
_SEEDS_PATH = _DIAG / "ARC12_STUDY_SEEDS.json"
_FREEZE_PATH = _DIAG / "ARC12_PLATFORM_FREEZE.json"
_SCORING_PATH = _REPO / "docs" / "research" / "SSTRF_RQ1_SCORING_SYSTEM_V2.md"

_EXPECTED_LABELS = [f"trial-{chr(ord('A') + i)}" for i in range(10)]

_REQUIRED_FREEZE_KEYS = frozenset(
    {
        "platform_code_commit",
        "pre_reg_commit",
        "pre_reg_path",
        "fixture_provenance",
        "scoring_system",
        "study_seeds",
        "export_version",
        "frozen_at",
        "signature_status",
    }
)


def _collect_seeds(value: object, out: set[int]) -> None:
    if isinstance(value, dict):
        seed = value.get("seed")
        if isinstance(seed, int):
            out.add(seed)
        for item in value.values():
            _collect_seeds(item, out)
    elif isinstance(value, list):
        for item in value:
            _collect_seeds(item, out)


def _excluded_seeds_from_diagnostics() -> set[int]:
    seeds: set[int] = set()
    for path in sorted(_DIAG.glob("*.json")):
        if path.name == "ARC12_STUDY_SEEDS.json":
            continue
        _collect_seeds(json.loads(path.read_text(encoding="utf-8")), seeds)
    return seeds


def _git_hash_object(path: Path) -> str:
    result = subprocess.run(
        ["git", "hash-object", str(path)],
        cwd=_REPO,
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


@pytest.fixture
def seeds_doc() -> dict:
    return json.loads(_SEEDS_PATH.read_text(encoding="utf-8"))


@pytest.fixture
def freeze_doc() -> dict:
    return json.loads(_FREEZE_PATH.read_text(encoding="utf-8"))


def test_study_seeds_has_ten_trials_a_through_j(seeds_doc: dict) -> None:
    trials = seeds_doc["trials"]
    assert len(trials) == 10
    labels = [trial["trial_label"] for trial in trials]
    assert labels == _EXPECTED_LABELS
    assert all(isinstance(trial["random_seed"], int) for trial in trials)


def test_study_seeds_not_in_exclusion_set(seeds_doc: dict) -> None:
    excluded = _excluded_seeds_from_diagnostics()
    assert seeds_doc["excluded_seeds"] == sorted(excluded)
    study_seeds = {trial["random_seed"] for trial in seeds_doc["trials"]}
    assert study_seeds.isdisjoint(excluded)


def test_study_seeds_selection_rule_documented(seeds_doc: dict) -> None:
    assert "selection_rule" in seeds_doc
    assert seeds_doc["trials"][0]["random_seed"] == 500
    assert seeds_doc["trials"][-1]["random_seed"] == 509


def test_freeze_manifest_required_keys_and_unsigned(freeze_doc: dict) -> None:
    assert _REQUIRED_FREEZE_KEYS <= set(freeze_doc)
    assert freeze_doc["signature_status"] == "unsigned"
    assert freeze_doc["export_version"] == 14
    assert freeze_doc["pre_reg_path"] == "docs/research/PREREG_SSTRF_RQ1_V2.md"
    assert freeze_doc["study_seeds"]["path"] == "docs/diagnostics/ARC12_STUDY_SEEDS.json"


def test_freeze_scoring_blob_hash_matches_git(freeze_doc: dict) -> None:
    assert _SCORING_PATH.is_file(), "SSTRF_RQ1_SCORING_SYSTEM_V2.md must be tracked in git"
    expected = _git_hash_object(_SCORING_PATH)
    assert freeze_doc["scoring_system"]["blob_hash"] == expected
    assert freeze_doc["scoring_system"]["path"] == "docs/research/SSTRF_RQ1_SCORING_SYSTEM_V2.md"

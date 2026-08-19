"""Tests for MemBench adapter (senna-iter-46)."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

_REPO = Path(__file__).resolve().parents[2]
_SCRIPTS = _REPO / "scripts"
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

from membench_adapter import (  # noqa: E402
    MEMORY_FACTUAL,
    MEMORY_REFLECTIVE,
    SCENARIO_OBSERVATION,
    SCENARIO_PARTICIPATION,
    discover_fixtures,
    load_fixture,
    make_ground_truth_agent,
    make_memory_match_agent,
    membench_accuracy,
    run_all_fixtures,
    run_membench_suite,
    score_membench_answer,
    summarize_reports,
    validate_all_fixtures,
)

FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures/membench"
README = FIXTURES_DIR / "README.md"


def test_license_readme_present() -> None:
    assert README.is_file()
    text = README.read_text(encoding="utf-8")
    assert "github.com/import-myself/Membench" in text
    assert "f66d8d1028d3f68627d00f77a967b93fbb8694b6" in text
    assert "MIT" in text
    assert "Permission is hereby granted" in text


def test_fixture_files_offline() -> None:
    fixtures = discover_fixtures(FIXTURES_DIR)
    assert len(fixtures) == 4
    for (scenario, level), fixture in fixtures.items():
        assert fixture.scenario == scenario
        assert fixture.memory_level == level
        assert fixture.trajectories
        assert fixture.trajectories[0].qa.ground_truth in {"A", "B", "C", "D"}


def test_membench_scoring_exact_choice_match() -> None:
    assert score_membench_answer("D", "D") is True
    assert score_membench_answer("d", "D") is True
    assert score_membench_answer("C", "D") is False
    assert membench_accuracy(1, 1) == 1.0
    assert membench_accuracy(0, 1) == 0.0


def test_fixture_qa_evidence_preserved() -> None:
    validate_all_fixtures(FIXTURES_DIR)


def test_ground_truth_agent_perfect_accuracy() -> None:
    reports = run_all_fixtures(FIXTURES_DIR, make_ground_truth_agent())
    for report in reports.values():
        assert report.accuracy == 1.0
        assert report.correct == report.total


def test_memory_match_finds_evidence_in_all_cells() -> None:
    reports = run_all_fixtures(FIXTURES_DIR, make_memory_match_agent(seed=46))
    summary = summarize_reports(reports)
    for scenario in ("participation", "observation"):
        for level in ("factual", "reflective"):
            assert summary[scenario][level]["accuracy"] == 1.0
    assert summary["participation"]["factual"]["memory_level"] == MEMORY_FACTUAL
    assert summary["participation"]["reflective"]["memory_level"] == MEMORY_REFLECTIVE
    assert summary["observation"]["factual"]["scenario"] == SCENARIO_OBSERVATION
    assert summary["participation"]["factual"]["scenario"] == SCENARIO_PARTICIPATION


def test_determinism_same_seed_same_scores() -> None:
    a = run_membench_suite(fixtures_dir=FIXTURES_DIR, seed=101, answer_mode="memory_match")
    b = run_membench_suite(fixtures_dir=FIXTURES_DIR, seed=101, answer_mode="memory_match")
    assert a == b
    c = run_membench_suite(fixtures_dir=FIXTURES_DIR, seed=202, answer_mode="memory_match")
    assert a != c


def test_factual_and_reflective_reported_separately() -> None:
    report = run_membench_suite(fixtures_dir=FIXTURES_DIR, seed=42)
    assert set(report["participation"]) == {"factual", "reflective"}
    assert set(report["observation"]) == {"factual", "reflective"}
    assert report["participation"]["factual"]["metric"] == "memory_accuracy"
    assert report["observation"]["reflective"]["metric"] == "memory_accuracy"


def test_load_fixture_round_trip() -> None:
    path = FIXTURES_DIR / "observation_factual.json"
    fixture = load_fixture(path)
    assert fixture.scenario == SCENARIO_OBSERVATION
    assert fixture.memory_level == MEMORY_FACTUAL
    assert isinstance(fixture.trajectories[0].message_list[0], str)


def test_run_membench_suite_no_network(monkeypatch: pytest.MonkeyPatch) -> None:
    def _fail(*_args, **_kwargs):
        raise AssertionError("network fetch attempted during offline test")

    monkeypatch.setattr("urllib.request.urlopen", _fail)
    run_membench_suite(fixtures_dir=FIXTURES_DIR, seed=1)

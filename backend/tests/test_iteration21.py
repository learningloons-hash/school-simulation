"""Iteration 21 — generic engine: YAML initial_state, domain-agnostic synthetic demographics."""

from __future__ import annotations

from mirofish_backend.scenarios.registry import PersonaTemplate, get_scenario
from mirofish_backend.scenarios.validate import validate_scenario_document
from mirofish_backend.simulation.orchestrator import (
    _build_demographics,
    _initial_state_from_persona,
    _neutral_initial_state,
)


def test_psle_yaml_initial_state_matches_legacy_engine_defaults() -> None:
    cfg = get_scenario("psle_reform_mvp")
    expected = [
        (0.62, 0.30, 0.40, "strategic_support"),
        (0.55, 0.35, 0.52, "operational_balancing"),
        (0.50, 0.38, 0.58, "classroom_caution"),
    ]
    assert len(cfg.personas) == len(expected)
    for persona, exp in zip(cfg.personas, expected, strict=True):
        st = _initial_state_from_persona(persona)
        assert (st.support_level, st.resistance_level, st.workload_stress, st.belief_posture) == exp


def test_fsbb_yaml_initial_state_matches_legacy_engine_defaults() -> None:
    cfg = get_scenario("fsbb_comparator")
    expected = [
        (0.62, 0.30, 0.40, "strategic_support"),
        (0.55, 0.35, 0.52, "operational_balancing"),
        (0.50, 0.38, 0.58, "classroom_caution"),
    ]
    for persona, exp in zip(cfg.personas, expected, strict=True):
        st = _initial_state_from_persona(persona)
        assert (st.support_level, st.resistance_level, st.workload_stress, st.belief_posture) == exp


def test_neutral_initial_state_when_persona_has_no_initial_block() -> None:
    p = PersonaTemplate(
        persona_id="analyst_001",
        role="analyst",
        name="Analyst",
        role_level=2,
        style_cues="Brief.",
        beliefs={},
    )
    st = _initial_state_from_persona(p)
    assert st == _neutral_initial_state()


def test_build_demographics_high_role_level_clamps_age() -> None:
    dem = _build_demographics(role_level=10, idx=0)
    assert dem["age"] >= 22


def test_build_demographics_role_level_based_no_role_strings() -> None:
    assert _build_demographics(role_level=1, idx=0) == {
        "age": 49,
        "sex": "female",
        "ethnicity": "unspecified",
        "ses": "unspecified",
    }
    assert _build_demographics(role_level=2, idx=1) == {
        "age": 42,
        "sex": "male",
        "ethnicity": "unspecified",
        "ses": "unspecified",
    }
    assert _build_demographics(role_level=3, idx=2) == {
        "age": 35,
        "sex": "female",
        "ethnicity": "unspecified",
        "ses": "unspecified",
    }


def test_validate_warns_when_role_level_below_one() -> None:
    doc = {
        "scenario_id": "bad_rl",
        "name": "T",
        "policy_events": {"1": "event"},
        "personas": [
            {
                "persona_id": "a1",
                "role": "lead",
                "name": "L",
                "role_level": 0,
                "style_cues": "s",
                "beliefs": {},
            }
        ],
    }
    errs, warns = validate_scenario_document(doc, is_update=False, allowed_corpus_paths=frozenset())
    assert not errs
    assert any("positive integer" in w and "highest authority" in w for w in warns)


def test_validate_warns_initial_state_out_of_range() -> None:
    doc = {
        "scenario_id": "bad_is",
        "name": "T",
        "policy_events": {"1": "event"},
        "personas": [
            {
                "persona_id": "a1",
                "role": "lead",
                "name": "L",
                "role_level": 1,
                "style_cues": "s",
                "beliefs": {},
                "initial_state": {"support_level": 1.5, "resistance_level": 0.3, "workload_stress": 0.4},
            }
        ],
    }
    errs, warns = validate_scenario_document(doc, is_update=False, allowed_corpus_paths=frozenset())
    assert not errs
    assert any("initial_state.support_level" in w and "0.0 and 1.0" in w for w in warns)


def test_validate_errors_initial_state_non_numeric() -> None:
    doc = {
        "scenario_id": "bad_is2",
        "name": "T",
        "policy_events": {"1": "event"},
        "personas": [
            {
                "persona_id": "a1",
                "role": "lead",
                "name": "L",
                "role_level": 1,
                "style_cues": "s",
                "beliefs": {},
                "initial_state": {"support_level": "high"},
            }
        ],
    }
    errs, warns = validate_scenario_document(doc, is_update=False, allowed_corpus_paths=frozenset())
    assert any("initial_state.support_level" in e and "must be a number" in e for e in errs)
    assert not warns


def test_validate_no_warning_for_role_level_four() -> None:
    doc = {
        "scenario_id": "ok_rl4",
        "name": "T",
        "policy_events": {"1": "event"},
        "personas": [
            {
                "persona_id": "a1",
                "role": "staff",
                "name": "S",
                "role_level": 4,
                "style_cues": "s",
                "beliefs": {},
            }
        ],
    }
    errs, warns = validate_scenario_document(doc, is_update=False, allowed_corpus_paths=frozenset())
    assert not errs
    assert not any("positive integer" in w for w in warns)

"""scenario-context-field Part B — sq_reading_culture fixture pair."""

from __future__ import annotations

from dataclasses import asdict
from typing import Any

import pytest

from mirofish_backend.scenarios.registry import PersonaTemplate, get_scenario, scenario_from_mapping
from mirofish_backend.scenarios.serialize import scenario_config_to_document

BASELINE_ID = "sq_reading_culture"
ADVERSE_ID = "sq_reading_culture_adverse"


def _persona_roster(personas: list[PersonaTemplate]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for p in personas:
        d = asdict(p)
        d.pop("likert_anchor_labels", None)
        out.append(d)
    return out


def test_sq_reading_culture_fixtures_load_with_non_empty_context() -> None:
    baseline = get_scenario(BASELINE_ID)
    adverse = get_scenario(ADVERSE_ID)
    assert baseline.context
    assert adverse.context
    assert len(baseline.personas) == 8
    assert len(adverse.personas) == 8


def test_sq_reading_culture_contexts_differ() -> None:
    baseline = get_scenario(BASELINE_ID)
    adverse = get_scenario(ADVERSE_ID)
    assert baseline.context != adverse.context


def test_sq_reading_culture_identical_policy_events_and_roster() -> None:
    baseline = get_scenario(BASELINE_ID)
    adverse = get_scenario(ADVERSE_ID)
    assert baseline.policy_events == adverse.policy_events
    assert _persona_roster(baseline.personas) == _persona_roster(adverse.personas)


def test_sq_reading_culture_only_context_and_identity_fields_differ() -> None:
    baseline = get_scenario(BASELINE_ID)
    adverse = get_scenario(ADVERSE_ID)
    assert baseline.scenario_id != adverse.scenario_id
    assert baseline.name != adverse.name
    assert baseline.interaction_overlay == adverse.interaction_overlay == "school_trinidad"


@pytest.mark.parametrize("scenario_id", [BASELINE_ID, ADVERSE_ID])
def test_sq_reading_culture_context_round_trips(scenario_id: str) -> None:
    cfg = get_scenario(scenario_id)
    doc = scenario_config_to_document(cfg)
    assert doc.get("context") == cfg.context
    roundtrip = scenario_from_mapping(doc)
    assert roundtrip.context == cfg.context
    assert roundtrip.policy_events == cfg.policy_events
    assert len(roundtrip.personas) == len(cfg.personas)

"""GM-F 2026-09-11 — sq_reading_culture_rich persona differentiation fixtures."""

from __future__ import annotations

from dataclasses import asdict
from pathlib import Path
from typing import Any

import pytest
import yaml

from mirofish_backend.scenarios.registry import PersonaTemplate, get_scenario
from mirofish_backend.scenarios.serialize import scenario_config_to_document

POSITIVE_RICH_ID = "sq_reading_culture_rich"
ADVERSE_RICH_ID = "sq_reading_culture_adverse_rich"
BASELINE_ID = "sq_reading_culture"
ADVERSE_ID = "sq_reading_culture_adverse"

_DATA_DIR = Path(__file__).resolve().parents[1] / "src/mirofish_backend/scenarios/data"


def _persona_roster(personas: list[PersonaTemplate]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for p in personas:
        d = asdict(p)
        d.pop("likert_anchor_labels", None)
        out.append(d)
    return out


def test_sq_reading_culture_rich_fixtures_load() -> None:
    positive = get_scenario(POSITIVE_RICH_ID)
    adverse = get_scenario(ADVERSE_RICH_ID)
    assert len(positive.personas) == 8
    assert len(adverse.personas) == 8
    assert positive.context
    assert adverse.context


def test_sq_reading_culture_rich_header_warns_utility_only() -> None:
    for path in (
        _DATA_DIR / "sq_reading_culture_rich.yaml",
        _DATA_DIR / "sq_reading_culture_adverse_rich.yaml",
    ):
        text = path.read_text(encoding="utf-8")
        assert "INVENTED FOR UTILITY TESTING" in text
        assert "must never be used for validity" in text.lower()


def test_sq_reading_culture_rich_no_shared_anchor() -> None:
    for path in (
        _DATA_DIR / "sq_reading_culture_rich.yaml",
        _DATA_DIR / "sq_reading_culture_adverse_rich.yaml",
    ):
        text = path.read_text(encoding="utf-8")
        assert "&neutral_calibration_prior" not in text
        assert "*neutral_calibration_prior" not in text


def test_sq_reading_culture_rich_personas_differ_from_neutral_pair() -> None:
    rich = get_scenario(POSITIVE_RICH_ID)
    baseline = get_scenario(BASELINE_ID)
    assert _persona_roster(rich.personas) != _persona_roster(baseline.personas)


def test_sq_reading_culture_rich_identical_personas_across_contexts() -> None:
    positive = get_scenario(POSITIVE_RICH_ID)
    adverse = get_scenario(ADVERSE_RICH_ID)
    assert _persona_roster(positive.personas) == _persona_roster(adverse.personas)


def test_sq_reading_culture_rich_policy_events_match_baseline_pair() -> None:
    rich = get_scenario(POSITIVE_RICH_ID)
    baseline = get_scenario(BASELINE_ID)
    adverse_rich = get_scenario(ADVERSE_RICH_ID)
    adverse = get_scenario(ADVERSE_ID)
    assert rich.policy_events == baseline.policy_events
    assert adverse_rich.policy_events == adverse.policy_events


def test_sq_reading_culture_rich_context_matches_neutral_pair() -> None:
    rich = get_scenario(POSITIVE_RICH_ID)
    baseline = get_scenario(BASELINE_ID)
    adverse_rich = get_scenario(ADVERSE_RICH_ID)
    adverse = get_scenario(ADVERSE_ID)
    assert rich.context == baseline.context
    assert adverse_rich.context == adverse.context


@pytest.mark.parametrize("scenario_id", [POSITIVE_RICH_ID, ADVERSE_RICH_ID])
def test_sq_reading_culture_rich_configured_support_levels(scenario_id: str) -> None:
    cfg = get_scenario(scenario_id)
    by_id = {p.persona_id: p.initial_state for p in cfg.personas}
    assert by_id["vice_principal_001"]["support_level"] == 0.75
    assert by_id["hod_english_001"]["support_level"] == 0.45
    assert by_id["senior_teacher_001"]["support_level"] == 0.80
    assert by_id["teacher_001"]["support_level"] == 0.40
    assert by_id["parent_001"]["support_level"] == 0.85
    assert by_id["parent_002"]["support_level"] == 0.35
    assert by_id["parent_003"]["support_level"] == 0.55
    assert by_id["parent_004"]["support_level"] == 0.30


def test_sq_reading_culture_rich_teacher_style_has_sentinel_phrase() -> None:
    cfg = get_scenario(POSITIVE_RICH_ID)
    teacher = next(p for p in cfg.personas if p.persona_id == "teacher_001")
    assert "Twenty-two years in" in teacher.style_cues


@pytest.mark.parametrize("scenario_id", [POSITIVE_RICH_ID, ADVERSE_RICH_ID])
def test_sq_reading_culture_rich_round_trips(scenario_id: str) -> None:
    cfg = get_scenario(scenario_id)
    doc = scenario_config_to_document(cfg)
    raw = yaml.safe_load((_DATA_DIR / f"{scenario_id}.yaml").read_text(encoding="utf-8"))
    assert doc.get("context") == raw.get("context")
    assert len(doc.get("personas") or []) == 8

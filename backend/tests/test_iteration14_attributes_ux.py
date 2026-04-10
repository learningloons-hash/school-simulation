"""Iteration 14: Roster CSV _json columns; LLM-fill endpoint contract tests."""

from __future__ import annotations

import json

import pytest
from fastapi.testclient import TestClient

from mirofish_backend.llm.router import LLMCompletion
from mirofish_backend.main import app
from mirofish_backend.scenarios.registry import get_scenario
from mirofish_backend.roster.csv_roster import (
    merge_persona_for_slot,
    parse_roster_csv,
)


# ---------------------------------------------------------------------------
# Roster CSV _json column tests
# ---------------------------------------------------------------------------

def test_roster_identity_json_parses_and_merges() -> None:
    scenario = get_scenario("psle_reform_mvp")
    csv_text = (
        "slot,persona_id,identity_json,attitudes_json,personal_history_json\n"
        '1,principal_001,{"locale":"north"},{"stance":"pro"},{"years_in_role":"5"}\n'
    )
    result = parse_roster_csv(csv_text, agent_limit=3, scenario=scenario)
    row = result.by_slot[1]
    assert row.identity == {"locale": "north"}
    assert row.attitudes == {"stance": "pro"}
    assert row.personal_history == {"years_in_role": "5"}


def test_roster_section_json_merges_over_base_persona() -> None:
    scenario = get_scenario("psle_reform_mvp")
    base = scenario.personas[0]
    csv_text = (
        "slot,persona_id,identity_json\n"
        '1,principal_001,{"extra_key":"added"}\n'
    )
    result = parse_roster_csv(csv_text, agent_limit=3, scenario=scenario)
    merged = merge_persona_for_slot(base, result.by_slot[1])
    # Original YAML identity keys are preserved; CSV overlay added
    assert merged.identity.get("extra_key") == "added"
    # nationality came from YAML (psle principal has nationality: Singaporean)
    assert merged.identity.get("nationality") == "Singaporean"


def test_roster_section_json_overlay_wins_on_conflict() -> None:
    scenario = get_scenario("psle_reform_mvp")
    base = scenario.personas[0]
    # Override a key that exists in YAML
    csv_text = (
        "slot,persona_id,identity_json\n"
        '1,principal_001,{"nationality":"Malaysian"}\n'
    )
    result = parse_roster_csv(csv_text, agent_limit=3, scenario=scenario)
    merged = merge_persona_for_slot(base, result.by_slot[1])
    assert merged.identity["nationality"] == "Malaysian"


def test_roster_invalid_identity_json_raises() -> None:
    scenario = get_scenario("psle_reform_mvp")
    csv_text = "slot,persona_id,identity_json\n1,principal_001,not-json\n"
    with pytest.raises(ValueError, match="invalid JSON"):
        parse_roster_csv(csv_text, agent_limit=3, scenario=scenario)


def test_roster_identity_json_array_raises() -> None:
    scenario = get_scenario("psle_reform_mvp")
    # JSON array — must be quoted in CSV so the comma doesn't split it into extra columns
    csv_text = 'slot,persona_id,identity_json\n1,principal_001,"[1,2,3]"\n'
    with pytest.raises(ValueError, match="must be a JSON object"):
        parse_roster_csv(csv_text, agent_limit=3, scenario=scenario)


def test_roster_section_columns_absent_leaves_base_unchanged() -> None:
    """v1-style roster without _json columns still works; sections come from YAML."""
    scenario = get_scenario("psle_reform_mvp")
    base = scenario.personas[0]
    csv_text = "slot,persona_id,name\n1,principal_001,Override Name\n"
    result = parse_roster_csv(csv_text, agent_limit=3, scenario=scenario)
    merged = merge_persona_for_slot(base, result.by_slot[1])
    assert merged.name == "Override Name"
    assert merged.identity == base.identity


# ---------------------------------------------------------------------------
# LLM-fill endpoint contract test (no real LLM — monkeypatched)
# ---------------------------------------------------------------------------

def test_llm_fill_endpoint_returns_section_dicts(monkeypatch, tmp_path) -> None:
    db = tmp_path / "fill_test.sqlite"
    monkeypatch.setenv("SQLITE_PATH", str(db))

    async def fake_llm_complete(**kwargs) -> LLMCompletion:
        return LLMCompletion(
            text=json.dumps({
                "identity": {"nationality": "Singaporean", "gender_identity": "woman"},
                "attitudes": {"policy_stance": "cautiously_supportive"},
                "personal_history": {"years_in_role": "8"},
            })
        )

    monkeypatch.setattr("mirofish_backend.api.scenario_catalog.llm_complete", fake_llm_complete)

    with TestClient(app) as client:
        r = client.post(
            "/scenarios/psle_reform_mvp/llm-fill",
            json={
                "persona_id": "principal_001",
                "role": "principal",
                "name": "Ms Tan",
                "style_cues": "Formal, strategic",
            },
        )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["identity"]["nationality"] == "Singaporean"
    assert "policy_stance" in body["attitudes"]
    assert body["personal_history"]["years_in_role"] == "8"


def test_llm_fill_empty_sections_raises_422(monkeypatch, tmp_path) -> None:
    db = tmp_path / "fill_test2.sqlite"
    monkeypatch.setenv("SQLITE_PATH", str(db))
    with TestClient(app) as client:
        r = client.post(
            "/scenarios/psle_reform_mvp/llm-fill",
            json={
                "persona_id": "principal_001",
                "role": "principal",
                "sections": [],
            },
        )
    assert r.status_code == 422

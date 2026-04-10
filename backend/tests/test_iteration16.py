"""Iteration 16: /capabilities, generate-from-brief, simulation analyze."""

from __future__ import annotations

import asyncio
import json

import pytest
from fastapi.testclient import TestClient

from mirofish_backend.api.simulations import (
    ANALYZE_RAW_RESPONSE_MAX_CHARS_FIRST_PASS,
    ANALYZE_TRANSCRIPT_MAX_TURNS_FIRST_PASS,
)
from mirofish_backend.db.repo import create_simulation_run
from mirofish_backend.db.schema import init_db
from mirofish_backend.export_bundle import EXPORT_VERSION
from mirofish_backend.llm.router import LLMCompletion
from mirofish_backend.main import app


@pytest.fixture
def client(tmp_path, monkeypatch):
    db = tmp_path / "i16_client.sqlite"
    monkeypatch.setenv("SQLITE_PATH", str(db))
    with TestClient(app) as c:
        yield c


def _valid_scenario_doc(sid: str = "analyst_gen_brief") -> dict:
    return {
        "scenario_id": sid,
        "name": "Generated test",
        "policy_events": {"1": "Policy announcement.", "2": "Follow-up discussion."},
        "personas": [
            {
                "persona_id": "principal_001",
                "role": "principal",
                "name": "Principal",
                "role_level": 1,
                "style_cues": "Formal.",
                "beliefs": {"trust_in_moe_policy": 0.5},
            },
            {
                "persona_id": "teacher_001",
                "role": "teacher",
                "name": "Teacher",
                "role_level": 3,
                "style_cues": "Practical.",
                "beliefs": {"workload_sensitivity": 0.6},
            },
        ],
    }


def test_capabilities_endpoint_reflects_enums_and_constants(client: TestClient) -> None:
    r = client.get("/capabilities")
    assert r.status_code == 200
    body = r.json()
    assert body["export_version"] == EXPORT_VERSION
    assert body["agent_context_version"] == "2"
    assert body["population_schema_version"] == "2"
    assert body["interaction_policy_version"] == "1"
    assert "round_robin" in body["interaction_policy"]["turn_order_policies"]
    assert "hierarchical" in body["interaction_policy"]["turn_order_policies"]
    assert "full_round_robin" in body["simulation_run"]["simulation_modes"]
    assert "weighted" in body["simulation_run"]["population_sample_modes"]
    assert "lmstudio" in body["simulation_run"]["llm_providers"]
    assert body["persona_attribute_sections"] == ["identity", "attitudes", "personal_history"]
    assert isinstance(body["bundled_rag_paths"], list)


def test_generate_from_brief_success(monkeypatch, tmp_path) -> None:
    db = tmp_path / "i16_gen.sqlite"
    monkeypatch.setenv("SQLITE_PATH", str(db))

    async def fake_llm_complete(**kwargs) -> LLMCompletion:
        return LLMCompletion(text=json.dumps(_valid_scenario_doc()))

    monkeypatch.setattr("mirofish_backend.api.scenarios_generate.llm_complete", fake_llm_complete)

    with TestClient(app) as client:
        r = client.post(
            "/scenarios/generate-from-brief",
            json={"brief": "A school policy simulation about curriculum change with principal and teacher."},
        )
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["document"]["scenario_id"] == "analyst_gen_brief"
    assert len(data["document"]["personas"]) == 2


def test_generate_from_brief_validation_422(monkeypatch, tmp_path) -> None:
    db = tmp_path / "i16_bad.sqlite"
    monkeypatch.setenv("SQLITE_PATH", str(db))

    async def fake_llm_bad(**kwargs) -> LLMCompletion:
        return LLMCompletion(text=json.dumps({"scenario_id": "BAD", "name": "x", "policy_events": {"1": "a"}, "personas": []}))

    monkeypatch.setattr("mirofish_backend.api.scenarios_generate.llm_complete", fake_llm_bad)

    with TestClient(app) as client:
        r = client.post(
            "/scenarios/generate-from-brief",
            json={"brief": "Twenty chars minimum!!" * 2},
        )
    assert r.status_code == 422
    err = r.json()
    assert "detail" in err
    d = err["detail"]
    assert "errors" in d
    assert isinstance(d["errors"], list)


def test_analyze_requires_completed(monkeypatch, tmp_path) -> None:
    db = tmp_path / "i16_an.sqlite"
    monkeypatch.setenv("SQLITE_PATH", str(db))

    async def _run():
        await init_db(str(db))
        return await create_simulation_run(
            str(db),
            name="Pend",
            scenario_id="psle_reform_mvp",
            status="pending",
            total_rounds=2,
            random_seed=1,
            prompt_version="v1",
            model_used="m",
            config_snapshot={},
        )

    sim_id = asyncio.run(_run())

    with TestClient(app) as client:
        r = client.post(
            f"/simulations/{sim_id}/analyze",
            json={"research_question": "What patterns appear in resistance?"},
        )
    assert r.status_code == 409


def test_analyze_completed_run(monkeypatch, tmp_path) -> None:
    db = tmp_path / "i16_an2.sqlite"
    monkeypatch.setenv("SQLITE_PATH", str(db))

    async def _setup():
        await init_db(str(db))
        return await create_simulation_run(
            str(db),
            name="Done",
            scenario_id="psle_reform_mvp",
            status="completed",
            total_rounds=1,
            random_seed=1,
            prompt_version="v1",
            model_used="m",
            config_snapshot={"scenario_id": "psle_reform_mvp"},
        )

    sim_id = asyncio.run(_setup())

    async def fake_analyze_llm(**kwargs) -> LLMCompletion:
        return LLMCompletion(
            text=json.dumps(
                {
                    "key_findings": ["Teachers raised workload"],
                    "per_agent_summary": {"teacher_001": "Concerned about time"},
                    "trajectory_narrative": "Discussion moved from policy to implementation.",
                    "suggested_follow_ups": ["Run longer horizon"],
                }
            )
        )

    monkeypatch.setattr("mirofish_backend.api.simulations.llm_complete", fake_analyze_llm)

    with TestClient(app) as client:
        r = client.post(
            f"/simulations/{sim_id}/analyze",
            json={"research_question": "Summarize main themes."},
        )
    assert r.status_code == 200, r.text
    body = r.json()
    assert "workload" in body["key_findings"][0]
    assert body["per_agent_summary"].get("teacher_001")


def test_analyze_second_stage_reclips_transcript_for_char_budget(monkeypatch, tmp_path) -> None:
    """When JSON payload exceeds budget, head+tail transcript reclipping runs (architect follow-up)."""
    db = tmp_path / "i16_shrink.sqlite"
    monkeypatch.setenv("SQLITE_PATH", str(db))
    asyncio.run(init_db(str(db)))
    sim_id = "huge_run_id"
    captured_user: dict[str, str] = {}

    async def fake_bundle(_sqlite_path: str, *, simulation_id: str) -> dict:
        run = {
            "id": simulation_id,
            "name": "Big",
            "scenario_id": "psle_reform_mvp",
            "status": "completed",
            "total_rounds": 1,
            "current_round": 1,
            "random_seed": 1,
            "prompt_version": "v1",
            "model_used": "m",
            "config_snapshot": {},
            "failure_reason": None,
            "created_at": "2026-01-01",
            "completed_at": "2026-01-01",
        }
        transcript = []
        for i in range(ANALYZE_TRANSCRIPT_MAX_TURNS_FIRST_PASS):
            transcript.append(
                {
                    "round_number": 1,
                    "turn_index": i + 1,
                    "agent_id": f"a{i}",
                    "agent_role": "teacher",
                    "agent_name": "T",
                    "interaction_type": "broadcast",
                    "target_scope": "all",
                    "intent_tag": None,
                    "raw_response": "R" * 2500,
                    "raw_prompt": "P" * 5000,
                }
            )
        return {
            "run": run,
            "transcript": transcript,
            "outcome_indicators": [],
            "state_timeline": [],
            "validity_notes": [],
        }

    async def fake_llm(**kwargs) -> LLMCompletion:
        msgs = kwargs.get("messages") or []
        if msgs:
            captured_user["content"] = str(msgs[-1].get("content") or "")
        return LLMCompletion(
            text=json.dumps(
                {
                    "key_findings": ["shrink ok"],
                    "per_agent_summary": {},
                    "trajectory_narrative": "n",
                    "suggested_follow_ups": [],
                }
            )
        )

    monkeypatch.setattr("mirofish_backend.api.simulations.get_simulation_export_bundle", fake_bundle)
    monkeypatch.setattr("mirofish_backend.api.simulations.llm_complete", fake_llm)

    with TestClient(app) as client:
        r = client.post(
            f"/simulations/{sim_id}/analyze",
            json={"research_question": "Summarize the run."},
        )
    assert r.status_code == 200, r.text
    assert "transcript_reclipped" in captured_user["content"]
    assert "hard char budget" in captured_user["content"]


def test_analyze_second_stage_shortens_responses_when_few_turns(monkeypatch, tmp_path) -> None:
    """When turn count is below reclip threshold but JSON is still huge, per-response cap applies."""
    db = tmp_path / "i16_shrink2.sqlite"
    monkeypatch.setenv("SQLITE_PATH", str(db))
    asyncio.run(init_db(str(db)))
    sim_id = "huge_run_id_2"
    captured_user: dict[str, str] = {}

    async def fake_bundle(_sqlite_path: str, *, simulation_id: str) -> dict:
        run = {
            "id": simulation_id,
            "name": "Big2",
            "scenario_id": "psle_reform_mvp",
            "status": "completed",
            "total_rounds": 1,
            "current_round": 1,
            "random_seed": 1,
            "prompt_version": "v1",
            "model_used": "m",
            "config_snapshot": {},
            "failure_reason": None,
            "created_at": "2026-01-01",
            "completed_at": "2026-01-01",
        }
        # 70 turns; first pass caps each raw_response at ANALYZE_RAW_RESPONSE_MAX_CHARS_FIRST_PASS
        long_body = "X" * (ANALYZE_RAW_RESPONSE_MAX_CHARS_FIRST_PASS + 800)
        transcript = []
        for i in range(70):
            transcript.append(
                {
                    "round_number": 1,
                    "turn_index": i + 1,
                    "agent_id": f"b{i}",
                    "agent_role": "teacher",
                    "agent_name": "T",
                    "interaction_type": "broadcast",
                    "target_scope": "all",
                    "intent_tag": None,
                    "raw_response": long_body,
                    "raw_prompt": "p",
                }
            )
        return {
            "run": run,
            "transcript": transcript,
            "outcome_indicators": [],
            "state_timeline": [],
            "validity_notes": [],
        }

    async def fake_llm(**kwargs) -> LLMCompletion:
        msgs = kwargs.get("messages") or []
        if msgs:
            captured_user["content"] = str(msgs[-1].get("content") or "")
        return LLMCompletion(
            text=json.dumps(
                {
                    "key_findings": ["shorten ok"],
                    "per_agent_summary": {},
                    "trajectory_narrative": "n",
                    "suggested_follow_ups": [],
                }
            )
        )

    monkeypatch.setattr("mirofish_backend.api.simulations.get_simulation_export_bundle", fake_bundle)
    monkeypatch.setattr("mirofish_backend.api.simulations.llm_complete", fake_llm)

    with TestClient(app) as client:
        r = client.post(
            f"/simulations/{sim_id}/analyze",
            json={"research_question": "Summarize the run."},
        )
    assert r.status_code == 200, r.text
    assert "raw_response_shortened" in captured_user["content"]

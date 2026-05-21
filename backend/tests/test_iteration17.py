"""Iteration 17: /agent/plan, /agent/execute, /agent/ask."""

from __future__ import annotations

import asyncio
import json

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from mirofish_backend.agent.orchestrator import (
    ExecutionPlan,
    PlanSimulationParams,
    _simulation_run_request,
    execute_plan,
    validate_plan_against_capabilities,
)
from mirofish_backend.llm.model_profiles import ANTHROPIC_DEFAULT_ID, LOCAL_LMSTUDIO_DEFAULT_ID
from mirofish_backend.api.capabilities import build_capabilities_dict
from mirofish_backend.api.simulations import SimulationAnalyzeResponse, SimulationRunResponse
from mirofish_backend.config import get_settings
from mirofish_backend.llm.router import LLMCompletion
from mirofish_backend.main import app


@pytest.fixture
def client(tmp_path, monkeypatch):
    db = tmp_path / "i17.sqlite"
    monkeypatch.setenv("SQLITE_PATH", str(db))
    with TestClient(app) as c:
        yield c


def test_simulation_run_request_forwards_model_profile_id() -> None:
    sim = PlanSimulationParams(model_profile_id=ANTHROPIC_DEFAULT_ID)
    req = _simulation_run_request("psle_reform_mvp", sim)
    assert req.model_profile_id == ANTHROPIC_DEFAULT_ID


def test_plan_simulation_params_model_profile_id_optional() -> None:
    sim = PlanSimulationParams()
    assert sim.model_profile_id is None
    req = _simulation_run_request("fsbb_comparator", sim)
    assert req.model_profile_id is None


def test_validate_plan_against_capabilities_rejects_bad_model_profile_id() -> None:
    with pytest.raises(ValueError, match="model_profile_id must be one of"):
        ExecutionPlan.model_validate(
            {
                "runs": [
                    {
                        "research_question": "What happened?",
                        "scenario_id": "psle_reform_mvp",
                        "simulation": {"model_profile_id": "not_a_real_profile"},
                    }
                ]
            }
        )


def test_validate_plan_against_capabilities_rejects_unknown_profile_in_capabilities() -> None:
    cap = build_capabilities_dict()
    cap["model_profiles"] = {"profiles": [{"profile_id": "local_lmstudio_default"}]}
    plan = ExecutionPlan.model_validate(
        {
            "runs": [
                {
                    "research_question": "What happened?",
                    "scenario_id": "psle_reform_mvp",
                    "simulation": {"model_profile_id": ANTHROPIC_DEFAULT_ID},
                }
            ]
        }
    )
    errs = validate_plan_against_capabilities(cap, plan)
    assert any("model_profile_id" in e for e in errs)


def test_execute_plan_forwards_model_profile_id_to_queue(monkeypatch, tmp_path) -> None:
    db = tmp_path / "i17_profile.sqlite"
    monkeypatch.setenv("SQLITE_PATH", str(db))
    captured: dict[str, str | None] = {}

    async def fake_queue(settings, req):
        captured["model_profile_id"] = req.model_profile_id
        return SimulationRunResponse(id="sim_profile", warnings=[])

    async def fake_wait(**kwargs):
        return {"status": "completed", "id": "sim_profile", "failure_reason": None}

    async def fake_analyze(simulation_id, body):
        return SimulationAnalyzeResponse(
            key_findings=["ok"],
            per_agent_summary={},
            trajectory_narrative="n",
            suggested_follow_ups=[],
        )

    monkeypatch.setattr("mirofish_backend.agent.orchestrator.queue_simulation_run", fake_queue)
    monkeypatch.setattr("mirofish_backend.agent.orchestrator.wait_for_simulation_terminal", fake_wait)
    monkeypatch.setattr("mirofish_backend.agent.orchestrator.analyze_simulation_export", fake_analyze)

    plan = ExecutionPlan.model_validate(
        {
            "runs": [
                {
                    "research_question": "How did agents respond?",
                    "scenario_id": "psle_reform_mvp",
                    "simulation": {
                        "total_rounds": 1,
                        "agent_limit": 2,
                        "model_profile_id": LOCAL_LMSTUDIO_DEFAULT_ID,
                    },
                }
            ]
        }
    )
    result = asyncio.run(execute_plan(get_settings(), plan))
    assert result["runs"][0]["status"] == "completed"
    assert captured["model_profile_id"] == LOCAL_LMSTUDIO_DEFAULT_ID


def test_validate_plan_against_capabilities_rejects_bad_mode() -> None:
    cap = build_capabilities_dict()
    plan = ExecutionPlan.model_validate(
        {
            "runs": [
                {
                    "research_question": "What happened?",
                    "scenario_id": "psle_reform_mvp",
                    "simulation": {"simulation_mode": "not_valid_mode"},
                }
            ]
        }
    )
    errs = validate_plan_against_capabilities(cap, plan)
    assert any("simulation_mode" in e for e in errs)


def test_agent_execute_with_mocks(monkeypatch, tmp_path) -> None:
    db = tmp_path / "i17_ex.sqlite"
    monkeypatch.setenv("SQLITE_PATH", str(db))

    async def fake_queue(settings, req):
        return SimulationRunResponse(id="sim1", warnings=["w"])

    async def fake_wait(**kwargs):
        return {"status": "completed", "id": "sim1", "failure_reason": None}

    async def fake_analyze(simulation_id, body):
        return SimulationAnalyzeResponse(
            key_findings=["finding"],
            per_agent_summary={"a": "b"},
            trajectory_narrative="story",
            suggested_follow_ups=["more"],
        )

    monkeypatch.setattr("mirofish_backend.agent.orchestrator.queue_simulation_run", fake_queue)
    monkeypatch.setattr("mirofish_backend.agent.orchestrator.wait_for_simulation_terminal", fake_wait)
    monkeypatch.setattr("mirofish_backend.agent.orchestrator.analyze_simulation_export", fake_analyze)

    with TestClient(app) as client:
        r = client.post(
            "/agent/execute",
            json={
                "runs": [
                    {
                        "research_question": "What happened?",
                        "scenario_id": "psle_reform_mvp",
                        "simulation": {"total_rounds": 1, "agent_limit": 2},
                    }
                ]
            },
        )
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["runs"][0]["simulation_id"] == "sim1"
    assert data["runs"][0]["analysis"]["key_findings"] == ["finding"]


def test_execute_plan_continues_after_generate_http_exception(monkeypatch, tmp_path) -> None:
    db = tmp_path / "i17_genfail.sqlite"
    monkeypatch.setenv("SQLITE_PATH", str(db))
    calls = {"n": 0}

    async def gen_side_effect(body):
        calls["n"] += 1
        if calls["n"] == 1:
            raise HTTPException(status_code=422, detail={"errors": ["bad scenario"]})
        raise AssertionError("second step should use scenario_id, not brief")

    async def fake_queue(settings, req):
        return SimulationRunResponse(id="sim_ok", warnings=[])

    async def fake_wait(**kwargs):
        return {"status": "completed", "id": "sim_ok", "failure_reason": None}

    async def fake_analyze(simulation_id, body):
        return SimulationAnalyzeResponse(
            key_findings=["ok"],
            per_agent_summary={},
            trajectory_narrative="n",
            suggested_follow_ups=[],
        )

    monkeypatch.setattr("mirofish_backend.agent.orchestrator.generate_scenario_from_brief", gen_side_effect)
    monkeypatch.setattr("mirofish_backend.agent.orchestrator.queue_simulation_run", fake_queue)
    monkeypatch.setattr("mirofish_backend.agent.orchestrator.wait_for_simulation_terminal", fake_wait)
    monkeypatch.setattr("mirofish_backend.agent.orchestrator.analyze_simulation_export", fake_analyze)

    plan = ExecutionPlan.model_validate(
        {
            "runs": [
                {"research_question": "First run?", "scenario_brief": "x" * 25},
                {
                    "research_question": "Second run?",
                    "scenario_id": "psle_reform_mvp",
                    "simulation": {"total_rounds": 1, "agent_limit": 2},
                },
            ]
        }
    )
    result = asyncio.run(execute_plan(get_settings(), plan))
    assert len(result["runs"]) == 2
    assert result["runs"][0]["status"] == "generate_failed"
    assert "generate_from_brief" in (result["runs"][0].get("analysis_error") or "")
    assert result["runs"][1]["simulation_id"] == "sim_ok"
    assert result["runs"][1]["status"] == "completed"
    assert result["runs"][1]["analysis"]["key_findings"] == ["ok"]


def test_agent_execute_422_on_invalid_plan_body(client: TestClient) -> None:
    r = client.post(
        "/agent/execute",
        json={
            "runs": [
                {
                    "research_question": "What?",
                    "scenario_id": "psle_reform_mvp",
                    "simulation": {"simulation_mode": "invalid_xyz"},
                }
            ]
        },
    )
    assert r.status_code == 422


def test_agent_plan_mock_llm(monkeypatch, tmp_path) -> None:
    db = tmp_path / "i17_pl.sqlite"
    monkeypatch.setenv("SQLITE_PATH", str(db))

    async def fake_llm_build(settings, **kwargs):
        return ExecutionPlan.model_validate(
            {
                "runs": [
                    {
                        "research_question": "Summarize tensions.",
                        "scenario_id": "psle_reform_mvp",
                        "simulation": {"total_rounds": 1, "agent_limit": 2},
                    }
                ]
            }
        )

    # Patch where the route uses the symbol (api.agent imports it), not the defining module.
    monkeypatch.setattr("mirofish_backend.api.agent.llm_build_execution_plan", fake_llm_build)

    with TestClient(app) as client:
        r = client.post(
            "/agent/plan",
            json={"question": "Plan a minimal PSLE policy tabletop run."},
        )
    assert r.status_code == 200
    assert r.json()["plan"]["runs"][0]["scenario_id"] == "psle_reform_mvp"


def test_agent_plan_forwards_plan_temperature_to_llm(monkeypatch, tmp_path) -> None:
    db = tmp_path / "i17_temp.sqlite"
    monkeypatch.setenv("SQLITE_PATH", str(db))
    captured: dict[str, float | None] = {}

    async def fake_llm_complete(*, temperature=None, **kwargs):
        captured["temperature"] = temperature
        return LLMCompletion(
            text=json.dumps(
                {
                    "runs": [
                        {
                            "research_question": "Summarize tensions.",
                            "scenario_id": "psle_reform_mvp",
                            "simulation": {"total_rounds": 1, "agent_limit": 2},
                        }
                    ]
                }
            )
        )

    monkeypatch.setattr("mirofish_backend.agent.orchestrator.llm_complete", fake_llm_complete)

    with TestClient(app) as client:
        r = client.post(
            "/agent/plan",
            json={"question": "Plan one minimal PSLE run.", "plan_temperature": 0.88},
        )
    assert r.status_code == 200, r.text
    assert captured.get("temperature") == 0.88


@pytest.mark.manual
def test_agent_ask_sse_use_curl_instead_of_ci() -> None:
    pytest.skip("SSE: use curl in docs/iterations/iteration-17-closeout.md; TestClient.stream is flaky")


def test_agent_ask_json_mock(monkeypatch, tmp_path) -> None:
    db = tmp_path / "i17_ask.sqlite"
    monkeypatch.setenv("SQLITE_PATH", str(db))

    async def fake_llm_build(settings, **kwargs):
        return ExecutionPlan.model_validate(
            {
                "runs": [
                    {
                        "research_question": "Summary?",
                        "scenario_id": "psle_reform_mvp",
                        "simulation": {"total_rounds": 1, "agent_limit": 2},
                    }
                ]
            }
        )

    async def fake_execute(settings, plan, *, emit=None, wait_timeout_seconds=900.0):
        return {
            "runs": [
                {
                    "label": "run_0",
                    "scenario_id": "psle_reform_mvp",
                    "simulation_id": "sid",
                    "status": "completed",
                    "analysis": {"key_findings": ["ok"]},
                }
            ]
        }

    monkeypatch.setattr("mirofish_backend.api.agent.llm_build_execution_plan", fake_llm_build)
    monkeypatch.setattr("mirofish_backend.api.agent.execute_plan", fake_execute)

    with TestClient(app) as client:
        r = client.post(
            "/agent/ask",
            json={"question": "Run one round on psle_reform_mvp and tell me what you found."},
        )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["plan"]["runs"]
    assert body["runs"][0]["analysis"]["key_findings"] == ["ok"]


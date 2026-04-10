"""Iteration 28 — convergence stopping: threshold + patience, deltas, converged_at_round, exports."""

from __future__ import annotations

import asyncio
import json
import time

import pytest
from fastapi.testclient import TestClient

from mirofish_backend.db.schema import init_db
from mirofish_backend.llm.router import LLMCompletion
from mirofish_backend.main import app


@pytest.fixture
def client_i28(monkeypatch, tmp_path):
    db = tmp_path / "i28.sqlite"
    monkeypatch.setenv("SQLITE_PATH", str(db))
    asyncio.run(init_db(str(db)))

    async def fake_llm(**_kwargs: object) -> LLMCompletion:
        state = {
            "support_level": 0.52,
            "resistance_level": 0.48,
            "workload_stress": 0.5,
            "belief_posture": "neutral",
            "perceived_conflict": False,
        }
        return LLMCompletion(text="OK.\n\n<state>\n" + json.dumps(state) + "\n</state>", input_tokens=10, output_tokens=5)

    monkeypatch.setattr("mirofish_backend.simulation.orchestrator.llm_complete", fake_llm)

    with TestClient(app) as c:
        yield c, db


def _wait_completed(client: TestClient, sid: str, *, max_wait_s: float = 90.0) -> dict:
    deadline = time.monotonic() + max_wait_s
    last: dict = {}
    while time.monotonic() < deadline:
        r = client.get(f"/simulations/{sid}")
        assert r.status_code == 200, r.text
        last = r.json()
        if last.get("status") in ("completed", "failed"):
            return last
        time.sleep(0.08)
    raise AssertionError(f"simulation {sid} did not finish within {max_wait_s}s; last={last}")


def test_convergence_early_stop(client_i28) -> None:
    client, _db = client_i28
    r = client.post(
        "/simulations/run",
        json={
            "scenario_id": "psle_reform_mvp",
            "total_rounds": 12,
            "agent_limit": 3,
            "random_seed": 7,
            "convergence_threshold": 0.05,
            "convergence_patience": 2,
        },
    )
    assert r.status_code == 200, r.text
    sid = r.json()["id"]
    body = _wait_completed(client, sid)
    assert body["status"] == "completed"
    assert body["current_round"] == 3
    assert body["converged_at_round"] == 3
    tl = body.get("state_timeline") or []
    assert len(tl) == 3
    assert "convergence_delta" not in (tl[0].get("global_state") or {})
    assert isinstance((tl[1].get("global_state") or {}).get("convergence_delta"), float)
    cfg = body.get("config_snapshot") or {}
    assert cfg.get("convergence_threshold") == 0.05
    assert cfg.get("convergence_patience") == 2
    assert cfg.get("converged_at_round") == 3


def test_no_convergence_runs_full_rounds(client_i28) -> None:
    client, _db = client_i28
    r = client.post(
        "/simulations/run",
        json={
            "scenario_id": "psle_reform_mvp",
            "total_rounds": 3,
            "agent_limit": 3,
            "random_seed": 8,
        },
    )
    assert r.status_code == 200, r.text
    sid = r.json()["id"]
    body = _wait_completed(client, sid)
    assert body["status"] == "completed"
    assert body["current_round"] == 3
    assert body.get("converged_at_round") is None
    tl = body.get("state_timeline") or []
    assert len(tl) == 3


def test_export_json_includes_convergence_fields(client_i28) -> None:
    client, _db = client_i28
    r = client.post(
        "/simulations/run",
        json={
            "scenario_id": "psle_reform_mvp",
            "total_rounds": 4,
            "agent_limit": 2,
            "random_seed": 9,
            "convergence_threshold": 0.02,
            "convergence_patience": 2,
        },
    )
    assert r.status_code == 200, r.text
    sid = r.json()["id"]
    _wait_completed(client, sid)
    ej = client.get(f"/simulations/{sid}/export.json")
    assert ej.status_code == 200, ej.text
    payload = ej.json()
    assert payload.get("export_version") == "8"
    run = payload.get("run") or {}
    assert run.get("converged_at_round") == 3
    globs = payload.get("global_state_snapshots") or []
    assert len(globs) == 3
    assert "convergence_delta" not in globs[0]
    assert isinstance(globs[1].get("convergence_delta"), float)


def test_convergence_streak_resets_then_requires_fresh_patience(monkeypatch, tmp_path) -> None:
    """Varying states for rounds 1–3 (high deltas); stable thereafter — patience applies only after a reset."""
    db = tmp_path / "i28_streak.sqlite"
    monkeypatch.setenv("SQLITE_PATH", str(db))
    asyncio.run(init_db(str(db)))

    calls = {"n": 0}

    async def fake_llm_varying(**_kwargs: object) -> LLMCompletion:
        calls["n"] += 1
        rnum = (calls["n"] - 1) // 2 + 1
        if rnum <= 3:
            seq = [
                (0.52, 0.48, 0.50),
                (0.80, 0.20, 0.60),
                (0.40, 0.60, 0.40),
            ]
            s, res, w = seq[rnum - 1]
        else:
            s, res, w = (0.55, 0.45, 0.50)
        state = {
            "support_level": s,
            "resistance_level": res,
            "workload_stress": w,
            "belief_posture": "neutral",
            "perceived_conflict": False,
        }
        return LLMCompletion(text="OK.\n\n<state>\n" + json.dumps(state) + "\n</state>", input_tokens=4, output_tokens=4)

    monkeypatch.setattr("mirofish_backend.simulation.orchestrator.llm_complete", fake_llm_varying)

    with TestClient(app) as client:
        r = client.post(
            "/simulations/run",
            json={
                "scenario_id": "psle_reform_mvp",
                "total_rounds": 20,
                "agent_limit": 2,
                "random_seed": 11,
                "convergence_threshold": 0.01,
                "convergence_patience": 2,
            },
        )
        assert r.status_code == 200, r.text
        sid = r.json()["id"]
        body = _wait_completed(client, sid)
    assert body["converged_at_round"] == 6
    assert body["current_round"] == 6


def test_experiment_create_passes_convergence_to_child_runs(monkeypatch, tmp_path) -> None:
    db = tmp_path / "i28_exp.sqlite"
    monkeypatch.setenv("SQLITE_PATH", str(db))
    asyncio.run(init_db(str(db)))

    async def fake_llm(**_kwargs: object) -> LLMCompletion:
        state = {
            "support_level": 0.52,
            "resistance_level": 0.48,
            "workload_stress": 0.5,
            "belief_posture": "neutral",
            "perceived_conflict": False,
        }
        return LLMCompletion(text="OK.\n\n<state>\n" + json.dumps(state) + "\n</state>", input_tokens=10, output_tokens=5)

    monkeypatch.setattr("mirofish_backend.simulation.orchestrator.llm_complete", fake_llm)

    with TestClient(app) as client:
        r = client.post(
            "/experiments",
            json={
                "name": "conv sweep",
                "scenario_id": "psle_reform_mvp",
                "random_seed": 44,
                "total_rounds": 10,
                "agent_limit": 3,
                "convergence_threshold": 0.05,
                "convergence_patience": 2,
                "runs": [
                    {"label": "a", "sampling_strategy": "full_census"},
                    {"label": "b", "sampling_strategy": "role_stratified"},
                ],
            },
        )
        assert r.status_code == 200, r.text
        payload = r.json()
        exp_id = payload["experiment_id"]
        sim_ids = payload["simulation_ids"]
        assert len(sim_ids) == 2
        for sid in sim_ids:
            body = _wait_completed(client, sid)
            assert body.get("converged_at_round") == 3
            assert body["current_round"] == 3
        det = client.get(f"/experiments/{exp_id}")
        assert det.status_code == 200
        data = det.json()
        for run in data["runs"]:
            assert run.get("converged_at_round") == 3
        comp = data.get("comparison") or []
        r2 = next(x for x in comp if x["round_number"] == 2)
        for _sk, met in (r2.get("by_run") or {}).items():
            assert "convergence_delta" in met
            assert isinstance(met["convergence_delta"], float)


def test_agent_plan_accepts_convergence_fields() -> None:
    from mirofish_backend.agent.orchestrator import (
        ExecutionPlan,
        PlanRunStep,
        PlanSimulationParams,
        validate_plan_against_capabilities,
    )
    from mirofish_backend.api.capabilities import build_capabilities_dict

    cap = build_capabilities_dict()
    plan = ExecutionPlan(
        runs=[
            PlanRunStep(
                research_question="Compare strategies with early stopping",
                scenario_id="psle_reform_mvp",
                simulation=PlanSimulationParams(convergence_threshold=0.02, convergence_patience=3),
            )
        ]
    )
    assert validate_plan_against_capabilities(cap, plan) == []

    # Out-of-range threshold is rejected by capability check (bypass Pydantic le=1 with model_construct).
    good_dump = PlanSimulationParams().model_dump(mode="python")
    good_dump["convergence_threshold"] = 1.5
    bad_sim = PlanSimulationParams.model_construct(**good_dump)
    bad_step = PlanRunStep(
        research_question="bad threshold",
        scenario_id="psle_reform_mvp",
        simulation=bad_sim,
    )
    bad_plan = ExecutionPlan(runs=[bad_step])
    errs = validate_plan_against_capabilities(cap, bad_plan)
    assert any("convergence_threshold" in e for e in errs)

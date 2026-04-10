"""Iteration 27 — experiments: POST/GET, exports, experiment_id on simulation_runs."""

from __future__ import annotations

import asyncio
import io
import json
import zipfile

import pytest
from fastapi.testclient import TestClient

import mirofish_backend.api.experiments as experiments_api
from mirofish_backend.db.repo import (
    create_simulation_run,
    get_experiment_row,
    list_experiment_run_links,
    list_experiments,
)
from mirofish_backend.db.schema import init_db
from mirofish_backend.main import app


@pytest.fixture
def client_exp(monkeypatch, tmp_path):
    db = tmp_path / "i27.sqlite"
    monkeypatch.setenv("SQLITE_PATH", str(db))
    asyncio.run(init_db(str(db)))
    with TestClient(app) as c:
        yield c, db


def test_standalone_run_has_null_experiment_id(client_exp) -> None:
    client, db = client_exp

    async def _mk():
        return await create_simulation_run(
            str(db),
            name="solo",
            scenario_id="psle_reform_mvp",
            status="completed",
            total_rounds=1,
            random_seed=1,
            prompt_version="v1",
            model_used="m",
            config_snapshot={"sampling_strategy": "full_census"},
        )

    sid = asyncio.run(_mk())
    r = client.get("/simulations")
    assert r.status_code == 200
    rows = r.json()
    mine = next(x for x in rows if x["id"] == sid)
    assert mine.get("experiment_id") in (None, "")


def test_create_experiment_two_runs_sequential_fake_llm(monkeypatch, tmp_path) -> None:
    db = tmp_path / "i27_e2e.sqlite"
    monkeypatch.setenv("SQLITE_PATH", str(db))
    asyncio.run(init_db(str(db)))

    async def fake_llm(**_kwargs: object) -> str:
        state = {
            "support_level": 0.52,
            "resistance_level": 0.48,
            "workload_stress": 0.5,
            "belief_posture": "neutral",
            "perceived_conflict": False,
        }
        return "OK.\n\n<state>\n" + json.dumps(state) + "\n</state>"

    monkeypatch.setattr("mirofish_backend.simulation.orchestrator.llm_complete", fake_llm)

    with TestClient(app) as client:
        r = client.post(
            "/experiments",
            json={
                "name": "E2E strat compare",
                "scenario_id": "psle_reform_mvp",
                "random_seed": 99,
                "total_rounds": 1,
                "agent_limit": 3,
                "runs": [
                    {"label": "fc", "sampling_strategy": "full_census"},
                    {"label": "rs", "sampling_strategy": "role_stratified"},
                ],
            },
        )
        assert r.status_code == 200, r.text
        body = r.json()
        exp_id = body["experiment_id"]
        sim_ids = body["simulation_ids"]
        assert len(sim_ids) == 2

        row = asyncio.run(get_experiment_row(str(db), experiment_id=exp_id))
        assert row is not None
        assert row["status"] == "completed"
        assert row["base_random_seed"] == 99

        links = asyncio.run(list_experiment_run_links(str(db), experiment_id=exp_id))
        assert len(links) == 2

        r2 = client.get(f"/experiments/{exp_id}")
        assert r2.status_code == 200, r2.text
        detail = r2.json()
        assert detail["experiment"]["id"] == exp_id
        assert len(detail["runs"]) == 2
        comp = detail["comparison"]
        assert len(comp) == 1
        assert "fc" in comp[0]["by_run"] and "rs" in comp[0]["by_run"]

        r3 = client.get(f"/experiments/{exp_id}/export.json")
        assert r3.status_code == 200
        expj = r3.json()
        assert expj["experiment"]["id"] == exp_id
        assert len(expj["runs"]) == 2

        r4 = client.get(f"/experiments/{exp_id}/export.zip")
        assert r4.status_code == 200
        zf = zipfile.ZipFile(io.BytesIO(r4.content))
        names = zf.namelist()
        assert "comparison.csv" in names
        assert "experiment.json" in names
        csv_raw = zf.read("comparison.csv").decode("utf-8")
        assert "run_label" in csv_raw and "fc" in csv_raw


def test_capabilities_includes_experiments_meta(client_exp) -> None:
    client, _ = client_exp
    r = client.get("/capabilities")
    assert r.status_code == 200
    ex = r.json().get("experiments")
    assert isinstance(ex, dict)
    assert ex.get("max_runs_per_experiment") == 16
    assert "POST /experiments" in str(ex.get("endpoints", {}))


def test_deduplicate_key_collision_suffix() -> None:
    used: set[str] = set()
    assert experiments_api._deduplicate_key("a", used) == "a"
    assert experiments_api._deduplicate_key("a", used) == "a__2"
    assert experiments_api._deduplicate_key("a", used) == "a__3"


def test_experiment_failure_sets_status_failed(monkeypatch, tmp_path) -> None:
    """Post-27 hardening: exception mid-loop → experiment failed + completed_at; HTTP 500."""
    db = tmp_path / "i27_fail.sqlite"
    monkeypatch.setenv("SQLITE_PATH", str(db))
    asyncio.run(init_db(str(db)))

    async def fake_llm(**_kwargs: object) -> str:
        state = {
            "support_level": 0.52,
            "resistance_level": 0.48,
            "workload_stress": 0.5,
            "belief_posture": "neutral",
            "perceived_conflict": False,
        }
        return "OK.\n\n<state>\n" + json.dumps(state) + "\n</state>"

    monkeypatch.setattr("mirofish_backend.simulation.orchestrator.llm_complete", fake_llm)

    real_queue = experiments_api.queue_simulation_run
    calls = {"n": 0}

    async def flaky_queue(settings, req, **kwargs):  # type: ignore[no-untyped-def]
        calls["n"] += 1
        if calls["n"] >= 2:
            raise RuntimeError("forced experiment failure")
        return await real_queue(settings, req, **kwargs)

    monkeypatch.setattr(experiments_api, "queue_simulation_run", flaky_queue)

    with TestClient(app) as client:
        r = client.post(
            "/experiments",
            json={
                "name": "fail mid",
                "scenario_id": "psle_reform_mvp",
                "random_seed": 1,
                "total_rounds": 1,
                "agent_limit": 3,
                "runs": [
                    {"label": "one", "sampling_strategy": "full_census"},
                    {"label": "two", "sampling_strategy": "role_stratified"},
                ],
            },
        )
        assert r.status_code == 500

    rows = asyncio.run(list_experiments(str(db), limit=1))
    assert len(rows) == 1
    exp_id = rows[0]["id"]
    row = asyncio.run(get_experiment_row(str(db), experiment_id=exp_id))
    assert row is not None
    assert row["status"] == "failed"
    assert row["completed_at"] is not None


def test_list_experiments_includes_run_count(monkeypatch, tmp_path) -> None:
    db = tmp_path / "i27_rc.sqlite"
    monkeypatch.setenv("SQLITE_PATH", str(db))
    asyncio.run(init_db(str(db)))

    async def fake_llm(**_kwargs: object) -> str:
        state = {
            "support_level": 0.52,
            "resistance_level": 0.48,
            "workload_stress": 0.5,
            "belief_posture": "neutral",
            "perceived_conflict": False,
        }
        return "OK.\n\n<state>\n" + json.dumps(state) + "\n</state>"

    monkeypatch.setattr("mirofish_backend.simulation.orchestrator.llm_complete", fake_llm)

    with TestClient(app) as client:
        r = client.post(
            "/experiments",
            json={
                "name": "rc",
                "scenario_id": "psle_reform_mvp",
                "random_seed": 7,
                "total_rounds": 1,
                "agent_limit": 3,
                "runs": [{"sampling_strategy": "full_census"}],
            },
        )
        assert r.status_code == 200, r.text
        lst = client.get("/experiments?limit=5")
        assert lst.status_code == 200
        body = lst.json()
        mine = next(x for x in body if x["name"] == "rc")
        assert mine.get("run_count") == 1

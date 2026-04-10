"""Iteration 26 — implementation_posture, posture_maxvar, sampling-report API."""

from __future__ import annotations

import asyncio
import json
import uuid
from dataclasses import replace

import pytest
from fastapi.testclient import TestClient

from mirofish_backend.api.simulations import wait_for_simulation_terminal
from mirofish_backend.db.repo import create_simulation_run
from mirofish_backend.db.schema import init_db
from mirofish_backend.main import app
from mirofish_backend.roster.csv_roster import parse_roster_csv
from mirofish_backend.scenarios.registry import get_scenario
from mirofish_backend.scenarios.validate import validate_scenario_document
from mirofish_backend.simulation.sampling_report import build_sampling_report_json
from mirofish_backend.simulation.sampling_strategy import compute_fidelity_tiers


def test_posture_maxvar_distinct_postures_tier_one() -> None:
    cfg = get_scenario("psle_reform_mvp")
    personas = cfg.personas[:3]
    tiers, rats = compute_fidelity_tiers(
        sampling_strategy="posture_maxvar",
        scenario=cfg,
        personas_for_run=personas,
        roster_by_slot=None,
    )
    assert tiers[0] == 1 and tiers[2] == 1
    assert tiers[1] in (2, 3)
    assert any("posture_maxvar" in r for r in rats)
    assert any("active_sense_maker" in r for r in rats)
    assert any("selective_adopter" in r for r in rats)


def test_posture_maxvar_no_tags_falls_back_to_role_stratified_rationale() -> None:
    cfg = get_scenario("psle_reform_mvp")
    personas = [replace(p, implementation_posture="") for p in cfg.personas[:3]]
    tiers, rats = compute_fidelity_tiers(
        sampling_strategy="posture_maxvar",
        scenario=cfg,
        personas_for_run=personas,
        roster_by_slot=None,
    )
    assert all("no posture tags" in r or "role_stratified" in r for r in rats if r)


def test_build_sampling_report_json_shape() -> None:
    snap = {
        "sampling_audit": {
            "sampling_strategy": "posture_maxvar",
            "tier_counts": {1: 1, 2: 1, 3: 0},
            "scenario_roles_ordered": ["principal", "teacher"],
            "scenario_roles_not_represented": [],
            "per_agent": [
                {
                    "agent_id": "a0",
                    "tier": 1,
                    "rationale": "x",
                    "role": "principal",
                    "implementation_posture": "p1",
                },
                {"agent_id": "a1", "tier": 2, "rationale": "y", "role": "teacher", "implementation_posture": None},
            ],
        }
    }
    out = build_sampling_report_json(snap)
    assert out["sampling_strategy"] == "posture_maxvar"
    assert out["tier_summary"] == {"1": 1, "2": 1, "3": 0}
    assert "principal" in out["by_role"]
    assert "p1" in out["by_posture"]
    assert "(untagged)" in out["by_posture"]
    assert out["centrality"] is None
    assert len(out["per_agent"]) == 2


def test_build_sampling_report_json_requires_audit() -> None:
    with pytest.raises(ValueError, match="sampling_audit"):
        build_sampling_report_json({"sampling_audit": None})
    with pytest.raises(ValueError, match="empty"):
        build_sampling_report_json(None)


def test_validate_implementation_posture_must_be_string() -> None:
    doc = {
        "scenario_id": "x_y",
        "name": "N",
        "policy_events": {"1": "e"},
        "personas": [
            {
                "persona_id": "p1",
                "role": "r",
                "name": "n",
                "role_level": 1,
                "style_cues": "s",
                "implementation_posture": 99,
            }
        ],
    }
    errs, _ = validate_scenario_document(doc, is_update=False, allowed_corpus_paths=frozenset())
    assert any("implementation_posture" in e for e in errs)


def test_roster_csv_parses_implementation_posture() -> None:
    cfg = get_scenario("psle_reform_mvp")
    text = (
        "slot,persona_id,role,name,role_level,style_cues,beliefs_json,groups,fidelity_tier,"
        "implementation_posture,identity_json,attitudes_json,personal_history_json\n"
        "1,,,,,,,,,active_sense_maker,,,\n"
    )
    res = parse_roster_csv(text, agent_limit=3, scenario=cfg)
    assert res.by_slot[1].implementation_posture == "active_sense_maker"


@pytest.fixture
def client_i26(monkeypatch, tmp_path):
    db = tmp_path / "i26.sqlite"
    monkeypatch.setenv("SQLITE_PATH", str(db))

    async def _init():
        await init_db(str(db))

    asyncio.run(_init())
    with TestClient(app) as c:
        yield c


def test_sampling_report_404(client_i26: TestClient) -> None:
    r = client_i26.get(f"/simulations/{uuid.uuid4().hex}/sampling-report")
    assert r.status_code == 404


def test_sampling_report_409_pending(client_i26: TestClient, tmp_path) -> None:
    db = tmp_path / "i26.sqlite"

    async def _mk():
        return await create_simulation_run(
            str(db),
            name="P",
            scenario_id="psle_reform_mvp",
            status="pending",
            total_rounds=1,
            random_seed=1,
            prompt_version="v1",
            model_used="m",
            config_snapshot={"sampling_audit": {"per_agent": []}},
        )

    sim_id = asyncio.run(_mk())
    r = client_i26.get(f"/simulations/{sim_id}/sampling-report")
    assert r.status_code == 409


def test_sampling_report_200_completed(client_i26: TestClient, tmp_path) -> None:
    db = tmp_path / "i26.sqlite"
    audit = {
        "sampling_strategy": "full_census",
        "tier_counts": {1: 1, 2: 0, 3: 0},
        "scenario_roles_ordered": ["principal"],
        "scenario_roles_not_represented": [],
        "per_agent": [{"agent_id": "x", "tier": 1, "rationale": "fc", "role": "principal", "implementation_posture": None}],
    }

    async def _mk():
        return await create_simulation_run(
            str(db),
            name="D",
            scenario_id="psle_reform_mvp",
            status="completed",
            total_rounds=1,
            random_seed=1,
            prompt_version="v1",
            model_used="m",
            config_snapshot={"sampling_audit": audit},
        )

    sim_id = asyncio.run(_mk())
    r = client_i26.get(f"/simulations/{sim_id}/sampling-report")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["sampling_strategy"] == "full_census"
    assert body["tier_summary"].get("1") == 1


def test_capabilities_includes_implementation_posture_meta(client_i26: TestClient) -> None:
    r = client_i26.get("/capabilities")
    assert r.status_code == 200
    ip = r.json().get("simulation_run", {}).get("implementation_posture")
    assert isinstance(ip, dict) and "posture_maxvar" in ip.get("description", "")


def test_posture_maxvar_queued_run_audit_and_sampling_report(monkeypatch, tmp_path) -> None:
    """Architect hardening: full API path with fake LLM — persisted audit + GET sampling-report."""
    db = tmp_path / "i26_e2e.sqlite"
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
            "/simulations/run",
            json={
                "scenario_id": "psle_reform_mvp",
                "agent_limit": 3,
                "total_rounds": 1,
                "sampling_strategy": "posture_maxvar",
            },
        )
        assert r.status_code == 200, r.text
        sim_id = r.json()["id"]
        asyncio.run(
            wait_for_simulation_terminal(
                sqlite_path=str(db),
                simulation_id=sim_id,
                poll_interval=0.05,
                timeout_seconds=60.0,
            )
        )
        r2 = client.get(f"/simulations/{sim_id}")
        assert r2.status_code == 200, r2.text
        body = r2.json()
        assert body.get("status") == "completed"
        snap = body.get("config_snapshot") or {}
        audit = snap.get("sampling_audit") or {}
        assert audit.get("sampling_strategy") == "posture_maxvar"
        per = audit.get("per_agent") or []
        assert len(per) == 3
        tc = audit.get("tier_counts") or {}
        n1 = int(tc.get("1", tc.get(1, 0)))
        n2 = int(tc.get("2", tc.get(2, 0)))
        n3 = int(tc.get("3", tc.get(3, 0)))
        assert n1 == 2 and n2 + n3 == 1
        posts = {(e.get("implementation_posture"), e.get("tier")) for e in per}
        assert ("active_sense_maker", 1) in posts
        assert ("selective_adopter", 1) in posts
        assert any(e.get("implementation_posture") in (None, "") and e.get("tier") in (2, 3) for e in per)

        r3 = client.get(f"/simulations/{sim_id}/sampling-report")
        assert r3.status_code == 200, r3.text
        rep = r3.json()
        assert rep.get("sampling_strategy") == "posture_maxvar"
        assert "active_sense_maker" in (rep.get("by_posture") or {})
        assert "selective_adopter" in (rep.get("by_posture") or {})
        assert "(untagged)" in (rep.get("by_posture") or {})

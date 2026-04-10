"""Iteration 22 — sampling strategy contract (metadata only)."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from mirofish_backend.main import app
from mirofish_backend.roster.csv_roster import parse_roster_csv
from mirofish_backend.scenarios.registry import get_scenario
from mirofish_backend.simulation.orchestrator import _build_agent_instances
from mirofish_backend.simulation.sampling_strategy import (
    SAMPLING_STRATEGY_VALUES,
    build_sampling_audit_extended,
    compute_fidelity_tiers,
    unique_roles_from_scenario,
)


def test_unique_roles_from_scenario_order() -> None:
    cfg = get_scenario("psle_reform_mvp")
    assert unique_roles_from_scenario(cfg) == ("principal", "middle_manager", "teacher")


def test_full_census_all_tier_one() -> None:
    cfg = get_scenario("psle_reform_mvp")
    personas = cfg.personas[:3]
    tiers, rats = compute_fidelity_tiers(
        sampling_strategy="full_census",
        scenario=cfg,
        personas_for_run=personas,
        roster_by_slot=None,
    )
    assert tiers == [1, 1, 1]
    assert all("full_census" in r for r in rats)


def test_role_stratified_three_distinct_roles_all_tier_one() -> None:
    cfg = get_scenario("psle_reform_mvp")
    personas = cfg.personas[:3]
    tiers, _ = compute_fidelity_tiers(
        sampling_strategy="role_stratified",
        scenario=cfg,
        personas_for_run=personas,
        roster_by_slot=None,
    )
    assert tiers == [1, 1, 1]


def test_role_stratified_all_same_role() -> None:
    cfg = get_scenario("psle_reform_mvp")
    # Four agents all "teacher" (role_level 3)
    personas = [cfg.personas[2]] * 4
    tiers, rats = compute_fidelity_tiers(
        sampling_strategy="role_stratified",
        scenario=cfg,
        personas_for_run=personas,
        roster_by_slot=None,
    )
    assert tiers[0] == 1
    assert set(tiers[1:]) <= {2, 3}
    assert all(r for r in rats)


def test_sampling_audit_reports_missing_roles() -> None:
    cfg = get_scenario("psle_reform_mvp")
    personas = [cfg.personas[0]]
    tiers, rats = compute_fidelity_tiers(
        sampling_strategy="role_stratified",
        scenario=cfg,
        personas_for_run=personas,
        roster_by_slot=None,
    )
    audit = build_sampling_audit_extended(
        sampling_strategy="role_stratified",
        tiers=tiers,
        rationales=rats,
        agent_ids=["principal_001_000"],
        scenario=cfg,
        personas_for_run=personas,
    )
    missing = audit["scenario_roles_not_represented"]
    assert "middle_manager" in missing
    assert "teacher" in missing
    assert "principal" not in missing


def test_role_stratified_duplicate_roles_splits_remainder() -> None:
    cfg = get_scenario("psle_reform_mvp")
    # 6 agents: principal, HoD, teacher, then three more teachers (repeat last persona)
    personas = [cfg.personas[0], cfg.personas[1], cfg.personas[2], cfg.personas[2], cfg.personas[2], cfg.personas[2]]
    tiers, _ = compute_fidelity_tiers(
        sampling_strategy="role_stratified",
        scenario=cfg,
        personas_for_run=personas,
        roster_by_slot=None,
    )
    assert tiers[0] == 1 and tiers[1] == 1 and tiers[2] == 1
    assert tiers[3] == 3 and tiers[4] == 2 and tiers[5] == 2


def test_roster_fidelity_tier_overrides_strategy() -> None:
    cfg = get_scenario("psle_reform_mvp")
    personas = cfg.personas[:3]
    csv_text = (
        "slot,fidelity_tier\n"
        "1,3\n"
        "2,\n"
        "3,\n"
    )
    roster = parse_roster_csv(csv_text, agent_limit=3, scenario=cfg)
    tiers, rats = compute_fidelity_tiers(
        sampling_strategy="role_stratified",
        scenario=cfg,
        personas_for_run=personas,
        roster_by_slot=roster.by_slot,
    )
    assert tiers[0] == 3
    assert "roster" in rats[0]
    assert tiers[1] == 1 and tiers[2] == 1


def test_roster_invalid_fidelity_tier_raises() -> None:
    cfg = get_scenario("psle_reform_mvp")
    csv_text = "slot,fidelity_tier\n1,99\n"
    with pytest.raises(ValueError, match="fidelity_tier"):
        parse_roster_csv(csv_text, agent_limit=1, scenario=cfg)


@pytest.fixture()
def client_skip_sim(monkeypatch, tmp_path):
    db = tmp_path / "iter22_api.sqlite"
    monkeypatch.setenv("SQLITE_PATH", str(db))

    async def skip_run(**kwargs) -> None:
        return None

    monkeypatch.setattr(
        "mirofish_backend.api.simulations.run_simulation_task_guarded",
        skip_run,
    )
    with TestClient(app) as c:
        yield c


def test_api_sampling_strategy_invalid_422(client_skip_sim: TestClient) -> None:
    r = client_skip_sim.post(
        "/simulations/run",
        json={
            "scenario_id": "psle_reform_mvp",
            "agent_limit": 2,
            "total_rounds": 1,
            "sampling_strategy": "magic_sample",
        },
    )
    assert r.status_code == 422


def test_api_config_snapshot_sampling_audit_full_census(client_skip_sim: TestClient) -> None:
    r = client_skip_sim.post(
        "/simulations/run",
        json={
            "scenario_id": "psle_reform_mvp",
            "agent_limit": 3,
            "total_rounds": 1,
            "sampling_strategy": "full_census",
        },
    )
    assert r.status_code == 200, r.text
    sim_id = r.json()["id"]
    r2 = client_skip_sim.get(f"/simulations/{sim_id}")
    snap = r2.json().get("config_snapshot") or {}
    assert snap.get("sampling_strategy") == "full_census"
    audit = snap.get("sampling_audit") or {}
    assert audit.get("sampling_strategy") == "full_census"
    tc = {int(k): v for k, v in (audit.get("tier_counts") or {}).items()}
    assert tc == {1: 3, 2: 0, 3: 0}
    assert len(audit.get("per_agent", [])) == 3
    assert all(a["tier"] == 1 for a in audit["per_agent"])


def test_capabilities_includes_sampling_strategies(client_skip_sim: TestClient) -> None:
    r = client_skip_sim.get("/capabilities")
    assert r.status_code == 200
    sr = r.json().get("simulation_run", {})
    assert set(sr.get("sampling_strategies", [])) == SAMPLING_STRATEGY_VALUES
    assert sr.get("fidelity_tiers", {}).get("min") == 1
    assert sr.get("fidelity_tiers", {}).get("max") == 3


def test_build_agent_instances_receives_fidelity_tiers() -> None:
    cfg = get_scenario("psle_reform_mvp")
    personas = cfg.personas[:3]
    agents = _build_agent_instances(cfg, personas, fidelity_tiers=[1, 2, 3])
    assert [a.fidelity_tier for a in agents] == [1, 2, 3]

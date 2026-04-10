"""Iteration 25 — network CSV, degree centrality, network_centrality strategy, ADR-002 visibility."""

from __future__ import annotations

import asyncio
import json

import pytest
from fastapi.testclient import TestClient

from pydantic import ValidationError

from mirofish_backend.api.simulations import SimulationRunRequest, wait_for_simulation_terminal
from mirofish_backend.db.schema import init_db
from mirofish_backend.main import app
from mirofish_backend.simulation.network import degree_centrality, parse_network_csv
from mirofish_backend.simulation.sampling_strategy import SAMPLING_STRATEGY_VALUES, compute_fidelity_tiers
from mirofish_backend.scenarios.registry import get_scenario


def test_parse_network_csv_warns_unknown_agents() -> None:
    known = frozenset({"p_000", "t_000"})
    text = (
        "source_agent_id,target_agent_id,influence_weight\n"
        "p_000,t_000,0.5\n"
        "p_000,ghost_000,1.0\n"
    )
    res = parse_network_csv(text, known_agent_ids=known)
    assert len(res.edges) == 1
    assert res.edges[0][:2] == ("p_000", "t_000")
    assert any("unknown" in w.lower() for w in res.warnings)


def test_degree_centrality_sums_incident_weights() -> None:
    agents = ["a", "b", "c"]
    edges = (("a", "b", 0.3), ("b", "c", 0.7))
    d = degree_centrality(agents, edges)
    assert d["a"] == pytest.approx(0.3)
    assert d["b"] == pytest.approx(1.0)
    assert d["c"] == pytest.approx(0.7)


def test_network_centrality_tier_assignment() -> None:
    cfg = get_scenario("psle_reform_mvp")
    personas = cfg.personas[:3]
    aids = [f"{personas[i].persona_id}_{i:03d}" for i in range(3)]
    cent = {aids[0]: 2.0, aids[1]: 1.0, aids[2]: 1.0}
    tiers, rats = compute_fidelity_tiers(
        sampling_strategy="network_centrality",
        scenario=cfg,
        personas_for_run=personas,
        roster_by_slot=None,
        agent_ids_in_order=aids,
        network_centrality_by_agent=cent,
    )
    assert tiers[0] == 1
    assert tiers[1] in (2, 3) and tiers[2] in (2, 3)
    assert any("network_centrality" in r for r in rats)


def test_network_centrality_requires_csv_via_request() -> None:
    with pytest.raises(ValidationError):
        SimulationRunRequest(
            scenario_id="psle_reform_mvp",
            sampling_strategy="network_centrality",
            network_csv=None,
        )


def test_capabilities_includes_network_centrality_and_visibility(client_skip: TestClient) -> None:
    r = client_skip.get("/capabilities")
    assert r.status_code == 200
    body = r.json()
    vis = set(body["interaction_policy"]["visibility_policies"])
    assert "network_bounded" in vis
    assert "round_participants_only" in vis
    assert "broadcast" in vis
    assert "full" not in vis
    assert "network_centrality" in set(body["simulation_run"]["sampling_strategies"])


@pytest.fixture
def client_skip(monkeypatch, tmp_path):
    db = tmp_path / "i25cap.sqlite"
    monkeypatch.setenv("SQLITE_PATH", str(db))

    async def _skip(**kwargs) -> None:
        return None

    monkeypatch.setattr(
        "mirofish_backend.api.simulations.run_simulation_task_guarded",
        _skip,
    )
    asyncio.run(init_db(str(db)))
    with TestClient(app) as c:
        yield c


def test_sampling_strategy_values_contains_network_centrality() -> None:
    assert "network_centrality" in SAMPLING_STRATEGY_VALUES


def test_network_queued_run_audit_sampling_report_and_node_count(monkeypatch, tmp_path) -> None:
    """Post-Iteration 25 hardening: queue run with network + centrality + network_bounded; audit + sampling-report."""
    db = tmp_path / "i25_e2e.sqlite"
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

    cfg = get_scenario("psle_reform_mvp")
    personas = cfg.personas[:3]
    aids = [f"{personas[i].persona_id}_{i:03d}" for i in range(3)]
    network_csv = (
        "source_agent_id,target_agent_id,influence_weight\n"
        f"{aids[0]},{aids[1]},0.6\n"
        f"{aids[1]},{aids[2]},0.4\n"
    )

    with TestClient(app) as client:
        r = client.post(
            "/simulations/run",
            json={
                "scenario_id": "psle_reform_mvp",
                "agent_limit": 3,
                "total_rounds": 1,
                "sampling_strategy": "network_centrality",
                "visibility_policy": "network_bounded",
                "network_csv": network_csv,
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
        assert snap.get("network_csv_applied") is True
        assert int(snap.get("network_edge_count") or 0) == 2
        assert int(snap.get("network_node_count") or 0) == 3
        ipol = snap.get("interaction_policy") or {}
        assert ipol.get("visibility_effective") == "network_bounded"
        audit = snap.get("sampling_audit") or {}
        assert audit.get("sampling_strategy") == "network_centrality"
        per = audit.get("per_agent") or []
        assert len(per) == 3
        assert all(float((e or {}).get("degree_centrality") or 0) > 0 for e in per)

        r3 = client.get(f"/simulations/{sim_id}/sampling-report")
        assert r3.status_code == 200, r3.text
        rep = r3.json()
        cent = rep.get("centrality")
        assert isinstance(cent, dict) and len(cent) == 3
        assert all(float(cent.get(aid, 0)) > 0 for aid in aids)

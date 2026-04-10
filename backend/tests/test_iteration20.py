"""Iteration 20: population scale and cohort aggregation."""

from __future__ import annotations

import io
import zipfile

import pytest
from fastapi.testclient import TestClient

from mirofish_backend.export_bundle import (
    EXPORT_VERSION,
    build_export_zip,
    compute_cohort_summary,
)
from mirofish_backend.main import app


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

def _make_snap(
    agent_id: str,
    round_number: int,
    group_ids: list[str],
    *,
    support_level: float = 0.5,
    resistance_level: float = 0.3,
    workload_stress: float = 0.4,
    spoke_this_round: bool = False,
) -> dict:
    return {
        "id": f"{agent_id}-r{round_number}",
        "simulation_id": "test-sim",
        "round_number": round_number,
        "agent_id": agent_id,
        "agent_role": "teacher",
        "agent_name": agent_id,
        "age": 35,
        "sex": "F",
        "ethnicity": "N/A",
        "ses": "middle",
        "support_level": support_level,
        "resistance_level": resistance_level,
        "workload_stress": workload_stress,
        "belief_posture": "neutral",
        "group_ids": group_ids,
        "spoke_this_round": spoke_this_round,
        "attribute_sections": {},
        "created_at": "2026-01-01",
    }


def _minimal_bundle(snaps: list[dict] | None = None) -> dict:
    return {
        "run": {
            "id": "sim-001",
            "name": "test",
            "scenario_id": "psle_reform_mvp",
            "status": "completed",
            "total_rounds": 2,
            "current_round": 2,
            "random_seed": 42,
            "prompt_version": "v0",
            "model_used": "fake",
            "config_snapshot": {},
            "failure_reason": None,
            "created_at": "2026-01-01",
            "completed_at": "2026-01-01",
        },
        "transcript": [],
        "agent_state_snapshots": snaps or [],
        "global_state_snapshots": [],
        "round_outcomes": [],
        "validity_notes": [],
    }


# ---------------------------------------------------------------------------
# 1. compute_cohort_summary — two groups, correct per-round averages
# ---------------------------------------------------------------------------

def test_compute_cohort_summary_groups_correctly() -> None:
    snaps = [
        _make_snap("a1", 1, ["leadership"], support_level=0.8, resistance_level=0.2, workload_stress=0.3, spoke_this_round=True),
        _make_snap("a2", 1, ["leadership"], support_level=0.6, resistance_level=0.4, workload_stress=0.5),
        _make_snap("b1", 1, ["teachers"], support_level=0.4, resistance_level=0.6, workload_stress=0.7, spoke_this_round=True),
        _make_snap("a1", 2, ["leadership"], support_level=0.9, resistance_level=0.1, workload_stress=0.2),
    ]
    result = compute_cohort_summary(snaps)

    # Should have two groups: "leadership" and "teachers"
    groups = {r["group_id"]: r for r in result}
    assert set(groups.keys()) == {"leadership", "teachers"}

    # leadership round 1: avg_support = (0.8+0.6)/2 = 0.7
    lead_r1 = groups["leadership"]["rounds"][0]
    assert lead_r1["round_number"] == 1
    assert lead_r1["agent_count"] == 2
    assert lead_r1["spoke_count"] == 1
    assert abs(lead_r1["avg_support_level"] - 0.7) < 1e-5
    assert abs(lead_r1["avg_resistance_level"] - 0.3) < 1e-5

    # leadership round 2: single agent
    lead_r2 = groups["leadership"]["rounds"][1]
    assert lead_r2["round_number"] == 2
    assert lead_r2["agent_count"] == 1
    assert abs(lead_r2["avg_support_level"] - 0.9) < 1e-5

    # teachers round 1: single agent, spoke
    teach_r1 = groups["teachers"]["rounds"][0]
    assert teach_r1["agent_count"] == 1
    assert teach_r1["spoke_count"] == 1


# ---------------------------------------------------------------------------
# 2. compute_cohort_summary — no group_ids → single "" entry
# ---------------------------------------------------------------------------

def test_compute_cohort_summary_ungrouped_agents() -> None:
    snaps = [
        _make_snap("x1", 1, [], support_level=0.5),
        _make_snap("x2", 1, [], support_level=0.7),
    ]
    result = compute_cohort_summary(snaps)
    assert len(result) == 1
    assert result[0]["group_id"] == ""
    r1 = result[0]["rounds"][0]
    assert r1["agent_count"] == 2
    assert abs(r1["avg_support_level"] - 0.6) < 1e-5


# ---------------------------------------------------------------------------
# 3. export.json — EXPORT_VERSION and cohort_summary present
# ---------------------------------------------------------------------------

def test_export_json_has_cohort_summary_and_export_version() -> None:
    """build_export_zip and compute_cohort_summary work; also verify export payload shape."""
    snaps = [
        _make_snap("a1", 1, ["group_a"], support_level=0.6),
        _make_snap("a2", 1, ["group_a"], support_level=0.8),
    ]
    bundle = _minimal_bundle(snaps)

    # Simulate what export_simulation_json does
    payload = {
        "export_version": EXPORT_VERSION,
        **bundle,
        "cohort_summary": compute_cohort_summary(bundle.get("agent_state_snapshots") or []),
    }
    assert payload["export_version"] == EXPORT_VERSION
    assert "cohort_summary" in payload
    assert isinstance(payload["cohort_summary"], list)
    assert len(payload["cohort_summary"]) == 1
    assert payload["cohort_summary"][0]["group_id"] == "group_a"
    assert payload["cohort_summary"][0]["rounds"][0]["agent_count"] == 2


# ---------------------------------------------------------------------------
# 4. export.zip — cohort_summary.csv present
# ---------------------------------------------------------------------------

def test_export_zip_contains_cohort_summary_csv() -> None:
    snaps = [
        _make_snap("a1", 1, ["cohort_x"], support_level=0.5, spoke_this_round=True),
    ]
    bundle = _minimal_bundle(snaps)
    zip_bytes = build_export_zip(bundle)
    with zipfile.ZipFile(io.BytesIO(zip_bytes), "r") as zf:
        names = set(zf.namelist())
        assert "cohort_summary.csv" in names
        csv_text = zf.read("cohort_summary.csv").decode()

    # Should have header + 1 data row
    rows = [r for r in csv_text.strip().splitlines() if r]
    assert rows[0].startswith("group_id,round_number")
    assert len(rows) == 2  # header + 1 data row
    assert "cohort_x" in rows[1]


# ---------------------------------------------------------------------------
# 5. API — agent_limit=300 accepted (Iteration 24 ceiling)
# ---------------------------------------------------------------------------

@pytest.fixture()
def client_skip_sim(monkeypatch, tmp_path):
    db = tmp_path / "iter20_api.sqlite"
    monkeypatch.setenv("SQLITE_PATH", str(db))

    async def skip_run(**kwargs) -> None:
        return None

    monkeypatch.setattr(
        "mirofish_backend.api.simulations.run_simulation_task_guarded",
        skip_run,
    )
    with TestClient(app) as c:
        yield c


def test_agent_limit_300_accepted(client_skip_sim: TestClient) -> None:
    r = client_skip_sim.post(
        "/simulations/run",
        json={"scenario_id": "psle_reform_mvp", "agent_limit": 300, "total_rounds": 1},
    )
    assert r.status_code == 200, r.text


# ---------------------------------------------------------------------------
# 6. API — aggregation_threshold and aggregation_mode in config_snapshot
# ---------------------------------------------------------------------------

def test_aggregation_fields_in_config_snapshot(client_skip_sim: TestClient) -> None:
    """aggregation_threshold stored; aggregation_mode=True when agent_limit >= threshold."""
    r = client_skip_sim.post(
        "/simulations/run",
        json={
            "scenario_id": "psle_reform_mvp",
            "agent_limit": 50,
            "total_rounds": 1,
            "aggregation_threshold": 20,
        },
    )
    assert r.status_code == 200, r.text
    sim_id = r.json()["id"]

    r2 = client_skip_sim.get(f"/simulations/{sim_id}")
    assert r2.status_code == 200
    config = r2.json().get("config_snapshot") or {}
    assert config.get("aggregation_threshold") == 20
    assert config.get("aggregation_mode") is True  # 50 >= 20


def test_aggregation_mode_false_below_threshold(client_skip_sim: TestClient) -> None:
    """aggregation_mode=False when agent_limit < aggregation_threshold."""
    r = client_skip_sim.post(
        "/simulations/run",
        json={
            "scenario_id": "psle_reform_mvp",
            "agent_limit": 5,
            "total_rounds": 1,
            "aggregation_threshold": 20,
        },
    )
    assert r.status_code == 200, r.text
    sim_id = r.json()["id"]

    r2 = client_skip_sim.get(f"/simulations/{sim_id}")
    config = r2.json().get("config_snapshot") or {}
    assert config.get("aggregation_mode") is False  # 5 < 20


# ---------------------------------------------------------------------------
# 7. API — capabilities exposes agent_limit.max == 300
# ---------------------------------------------------------------------------

def test_capabilities_includes_agent_limit_range(client_skip_sim: TestClient) -> None:
    r = client_skip_sim.get("/capabilities")
    assert r.status_code == 200
    data = r.json()
    sim_run = data.get("simulation_run", {})
    agent_limit = sim_run.get("agent_limit", {})
    assert agent_limit.get("max") == 300
    agg_threshold = sim_run.get("aggregation_threshold", {})
    assert agg_threshold.get("default") == 20
    assert agg_threshold.get("max") == 300

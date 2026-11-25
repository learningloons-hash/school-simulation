"""
M-ROSTER independent tester — preflight tests (spec §12 H, B4 via HTTP).

Pure-function and HTTP-client tests only.
Synthetic data only; no School-S or Ahn names.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from senna_backend.config import Settings
from senna_backend.llm.model_profiles import (
    LOCAL_LMSTUDIO_DEFAULT_ID,
    RunProfileResolution,
    resolve_run_profiles,
)
from senna_backend.main import app
from senna_backend.simulation.preflight import estimate_run_preflight


# ---------------------------------------------------------------------------
# Helpers — reusable pure-function kwargs
# ---------------------------------------------------------------------------

def _local_resolution() -> RunProfileResolution:
    return resolve_run_profiles(
        model_profile_id=LOCAL_LMSTUDIO_DEFAULT_ID,
        llm_provider="lmstudio",
        settings=Settings(),
    )


def _base_pf_kwargs(*, total_rounds: int = 4, agent_count: int = 4) -> dict:
    """Minimal estimate_run_preflight kwargs for lmstudio (zero cost)."""
    return dict(
        total_rounds=total_rounds,
        agent_count=agent_count,
        simulation_mode="full_round_robin",
        speakers_per_round=agent_count,
        fidelity_tiers=[1] * agent_count,
        llm_provider="lmstudio",
        profile_resolution=_local_resolution(),
        llm_max_tokens=256,
        round_summary_enabled=False,
        peer_context_max_chars=1200,
        working_memory_last_k=2,
    )


# ---------------------------------------------------------------------------
# §H1 — headline unchanged; active_window_adjusted correct
# ---------------------------------------------------------------------------

def test_preflight_headline_unchanged_with_windows() -> None:
    """
    §H1: estimated_cost_usd and llm_turns are unchanged by passing
    active_counts_per_round; the adjusted values live in active_window_adjusted.
    """
    kw = _base_pf_kwargs(total_rounds=4, agent_count=4)

    baseline = estimate_run_preflight(**kw)
    windowed = estimate_run_preflight(**kw, active_counts_per_round=[3, 3, 3, 3])

    # Headline unchanged
    assert baseline.estimated_cost_usd == windowed.estimated_cost_usd
    assert baseline.llm_turns == windowed.llm_turns

    # active_window_adjusted absent without windows, present with windows
    assert baseline.active_window_adjusted is None
    assert windowed.active_window_adjusted is not None

    adj = windowed.active_window_adjusted
    # speaking_turns = sum(min(per_round=4, active=3)) * 4 rounds = 12
    assert adj["speaking_turns"] == 12
    # No likert → likert_llm_turns = 0
    assert adj["likert_llm_turns"] == 0
    # llm_turns = speaking_turns (no likert, no importance, no reflection)
    assert adj["llm_turns"] == 12


def test_preflight_active_window_adjusted_with_likert() -> None:
    """
    §H1 (Likert): active_window_adjusted.likert_llm_turns = Σ active_counts
    when likert_self_report_enabled=True.
    """
    active = [3, 3, 2, 2]
    kw = _base_pf_kwargs(total_rounds=4, agent_count=4)

    est = estimate_run_preflight(**kw, active_counts_per_round=active, likert_self_report_enabled=True)

    adj = est.active_window_adjusted
    assert adj is not None
    # speaking_turns = Σ min(per_round=4, c) = 3+3+2+2 = 10
    assert adj["speaking_turns"] == 10
    # likert_llm_turns = Σ active_counts = 10
    assert adj["likert_llm_turns"] == sum(active)


def test_preflight_speaking_turns_active_window_adjusted_sum() -> None:
    """
    §H1: active_window_adjusted.speaking_turns = Σ active per round
    (each capped at per_round).
    """
    active = [4, 4, 2, 2]  # sum=12; per_round=4 for full_round_robin with 4 agents
    kw = _base_pf_kwargs(total_rounds=4, agent_count=4)

    est = estimate_run_preflight(**kw, active_counts_per_round=active)

    adj = est.active_window_adjusted
    assert adj is not None
    # sum(min(4, c) for c in [4,4,2,2]) = 4+4+2+2 = 12
    assert adj["speaking_turns"] == 12


# ---------------------------------------------------------------------------
# §H2 — active_window_adjusted key absent from to_snapshot() when None
# ---------------------------------------------------------------------------

def test_preflight_to_snapshot_no_active_window_adjusted_key() -> None:
    """§H2: to_snapshot() has no active_window_adjusted key when None."""
    kw = _base_pf_kwargs(total_rounds=2, agent_count=2)
    est = estimate_run_preflight(**kw)
    snap = est.to_snapshot()
    assert "active_window_adjusted" not in snap


def test_preflight_to_snapshot_active_window_adjusted_present_when_windowed() -> None:
    """§H2 (complement): to_snapshot() includes active_window_adjusted when not None."""
    kw = _base_pf_kwargs(total_rounds=2, agent_count=3)
    est = estimate_run_preflight(**kw, active_counts_per_round=[2, 2])
    snap = est.to_snapshot()
    assert "active_window_adjusted" in snap
    assert snap["active_window_adjusted"]["speaking_turns"] == 4  # 2+2


# ---------------------------------------------------------------------------
# HTTP client fixture
# ---------------------------------------------------------------------------

@pytest.fixture
def preflight_client(monkeypatch, tmp_path):
    db = tmp_path / "preflight_roster.sqlite"
    monkeypatch.setenv("SQLITE_PATH", str(db))
    with TestClient(app) as c:
        yield c


# ---------------------------------------------------------------------------
# §H3 — windows given only through roster CSV are seen by preflight
# ---------------------------------------------------------------------------

def test_preflight_http_active_window_adjusted_from_roster_csv(
    preflight_client: TestClient,
) -> None:
    """
    §H3: POST /simulations/preflight with roster_csv that has window columns
    → active_window_adjusted present in response.
    Slot 1: 1..2 (leaves after round 2)
    Slot 2: 1..4 (always active)
    Slot 3: 3..4 (joins at round 3)
    Slot 4: 1..4 (always active)
    Active per round: [3, 3, 3, 3] → speaking_turns = 12.
    """
    roster_csv = (
        "slot,active_from_round,active_until_round\n"
        "1,1,2\n"
        "2,1,4\n"
        "3,3,4\n"
        "4,1,4\n"
    )
    r = preflight_client.post(
        "/simulations/preflight",
        json={
            "scenario_id": "psle_reform_mvp",
            "total_rounds": 4,
            "agent_limit": 4,
            "model_profile_id": LOCAL_LMSTUDIO_DEFAULT_ID,
            "roster_csv": roster_csv,
        },
    )
    assert r.status_code == 200, r.text
    pf = r.json()["preflight"]

    assert "active_window_adjusted" in pf, (
        f"active_window_adjusted missing from preflight; keys: {list(pf.keys())}"
    )
    adj = pf["active_window_adjusted"]
    # active_agents_per_round = [3,3,3,3]; per_round = 4 → speaking_turns = 12
    assert adj["speaking_turns"] == 12


def test_preflight_http_no_active_window_adjusted_without_windows(
    preflight_client: TestClient,
) -> None:
    """§H2 (HTTP): Response has no active_window_adjusted when no windows given."""
    r = preflight_client.post(
        "/simulations/preflight",
        json={
            "scenario_id": "psle_reform_mvp",
            "total_rounds": 2,
            "agent_limit": 2,
            "model_profile_id": LOCAL_LMSTUDIO_DEFAULT_ID,
        },
    )
    assert r.status_code == 200, r.text
    pf = r.json()["preflight"]
    assert "active_window_adjusted" not in pf


# ---------------------------------------------------------------------------
# §B4 via HTTP — zero active agents → 422 at both endpoints
# ---------------------------------------------------------------------------

def test_preflight_http_zero_active_agents_returns_422(
    preflight_client: TestClient,
) -> None:
    """
    §B4 via /simulations/preflight: roster_csv with a gap (round 2 empty) → 422.
    Slot 1 active 1..1, Slot 2 active 3..4 → round 2 has no active agents.
    """
    roster_csv = (
        "slot,active_from_round,active_until_round\n"
        "1,1,1\n"
        "2,3,4\n"
    )
    r = preflight_client.post(
        "/simulations/preflight",
        json={
            "scenario_id": "psle_reform_mvp",
            "total_rounds": 4,
            "agent_limit": 2,
            "model_profile_id": LOCAL_LMSTUDIO_DEFAULT_ID,
            "roster_csv": roster_csv,
        },
    )
    assert r.status_code == 422, f"Expected 422, got {r.status_code}: {r.text}"


def test_run_http_zero_active_agents_returns_422(
    preflight_client: TestClient,
) -> None:
    """
    §B4 via /simulations/run: same zero-active-round roster_csv → 422
    (validation fires before any DB write or background task).
    """
    roster_csv = (
        "slot,active_from_round,active_until_round\n"
        "1,1,1\n"
        "2,3,4\n"
    )
    r = preflight_client.post(
        "/simulations/run",
        json={
            "scenario_id": "psle_reform_mvp",
            "total_rounds": 4,
            "agent_limit": 2,
            "model_profile_id": LOCAL_LMSTUDIO_DEFAULT_ID,
            "roster_csv": roster_csv,
        },
    )
    assert r.status_code == 422, f"Expected 422, got {r.status_code}: {r.text}"

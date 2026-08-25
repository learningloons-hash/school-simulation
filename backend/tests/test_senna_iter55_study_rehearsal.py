"""senna-iter-55 Part A — study rehearsal harness (stubbed CI path)."""

from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

import pytest

_REPO = Path(__file__).resolve().parents[2]
_SCRIPTS = _REPO / "scripts"
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

import run_arc12_study_rehearsal as rehearsal_script  # noqa: E402

from mirofish_backend.config import get_settings  # noqa: E402
from mirofish_backend.db.repo import get_simulation_export_bundle  # noqa: E402
from mirofish_backend.db.schema import init_db  # noqa: E402
from mirofish_backend.diagnostics.arc12_study_rehearsal import (  # noqa: E402
    build_expected_run_agent_ids,
    extract_mechanics_metrics,
    load_documented_network_csv,
)
from mirofish_backend.scenarios.registry import get_scenario  # noqa: E402
from mirofish_backend.simulation.network import parse_network_csv  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parent))
from simulation_helpers import fake_llm_state_block  # noqa: E402

FIXTURE_NETWORK = _REPO / "backend/tests/fixtures/iter55/documented_network_fsbb.csv"


def test_build_expected_run_agent_ids() -> None:
    ids = build_expected_run_agent_ids(persona_ids=["vice_principal_001", "teacher_001"])
    assert ids == ["vice_principal_001_000", "teacher_001_001"]


def test_load_documented_network_csv_validates_endpoints(tmp_path: Path) -> None:
    study = tmp_path / "study"
    rel_dir = study / "fixtures"
    rel_dir.mkdir(parents=True)
    rel = "fixtures/net.csv"
    (study / rel).write_text(FIXTURE_NETWORK.read_text(encoding="utf-8"), encoding="utf-8")
    expected = frozenset(
        build_expected_run_agent_ids(
            persona_ids=[p.persona_id for p in get_scenario("fsbb_comparator").personas[:3]],
        )
    )
    text, result = load_documented_network_csv(
        study_repo_path=study,
        rel_path=rel,
        expected_agent_ids=expected,
    )
    assert "principal_001_000" in text
    assert len(result.edges) == 3
    assert not result.warnings


def test_load_documented_network_csv_raises_on_unknown_agents(tmp_path: Path) -> None:
    study = tmp_path / "study"
    study.mkdir()
    bad = "source_agent_id,target_agent_id,influence_weight\nunknown_000,other_001,1.0\n"
    (study / "bad.csv").write_text(bad, encoding="utf-8")
    with pytest.raises(ValueError, match="no valid edges"):
        load_documented_network_csv(
            study_repo_path=study,
            rel_path="bad.csv",
            expected_agent_ids=frozenset(["principal_001_000"]),
        )


@pytest.mark.asyncio
async def test_rehearsal_run_applies_documented_network_csv(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "mirofish_backend.simulation.orchestrator.llm_complete",
        fake_llm_state_block,
    )

    cfg = get_scenario("fsbb_comparator")
    persona_ids = [p.persona_id for p in cfg.personas[:3]]
    expected = frozenset(build_expected_run_agent_ids(persona_ids=persona_ids))
    network_csv = FIXTURE_NETWORK.read_text(encoding="utf-8")
    assert parse_network_csv(network_csv, known_agent_ids=expected).edges

    profile = rehearsal_script.StudyRehearsalProfile(
        scenario_id="fsbb_comparator",
        agent_limit=3,
    )

    with tempfile.TemporaryDirectory() as tmp:
        db_path = os.path.join(tmp, "rehearsal.sqlite")
        await init_db(db_path)
        monkeypatch.setenv("SQLITE_PATH", db_path)
        settings = get_settings()

        rec = await rehearsal_script.run_rehearsal_via_api(
            settings=settings,
            profile=profile,
            label="CI-smoke",
            rounds=2,
            seed=42,
            network_csv=network_csv,
            llm_provider="lmstudio",
            rag_enabled=False,
        )

        assert rec.status == "completed"
        bundle = await get_simulation_export_bundle(db_path, simulation_id=rec.simulation_id)
        assert bundle is not None
        snap = (bundle.get("run") or {}).get("config_snapshot") or {}
        assert snap.get("network_csv_applied") is True
        assert int(snap.get("network_edge_count") or 0) >= 1
        assert snap.get("interaction_policy", {}).get("visibility_effective") == "network_bounded"

        mechanics = extract_mechanics_metrics(bundle=bundle, wall_clock_seconds=1.0)
        assert mechanics["network_csv_applied"] is True
        assert mechanics["llm_error_count"] == 0
        assert mechanics["token_totals_by_round"]

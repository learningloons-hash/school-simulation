"""sstrf-validity-v2 Part A — validity-trial simulation harness (stub LLM CI)."""

from __future__ import annotations

import json
import os
import sys
import tempfile
from dataclasses import replace
from pathlib import Path

import pytest

_REPO = Path(__file__).resolve().parents[2]
_SCRIPTS = _REPO / "scripts"
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

import run_sstrf_validity_trials as validity_script  # noqa: E402

from mirofish_backend.config import get_settings  # noqa: E402
from mirofish_backend.db.repo import get_simulation_export_bundle  # noqa: E402
from mirofish_backend.db.schema import init_db  # noqa: E402
from mirofish_backend.diagnostics.sstrf_validity_v2 import (  # noqa: E402
    PREREG_FROZEN_CONFIG,
    ValidityTrialProfile,
    assert_fixture_provenance_matches,
    assert_freeze_signed,
    build_validity_run_plan,
    default_manifest_path,
    is_production_validity_manifest,
    load_fixture_provenance,
    load_platform_freeze,
    load_study_seeds,
    profile_snapshot,
    resolve_validity_manifest_write_path,
)
from mirofish_backend.scenarios.registry import get_scenario  # noqa: E402
from mirofish_backend.simulation.network import parse_network_csv  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parent))
from simulation_helpers import fake_llm_state_block  # noqa: E402

FIXTURE_NETWORK = _REPO / "backend/tests/fixtures/iter55/documented_network_fsbb.csv"
_SEEDS_PATH = _REPO / "docs/diagnostics/ARC12_STUDY_SEEDS.json"
_FREEZE_PATH = _REPO / "docs/diagnostics/ARC12_PLATFORM_FREEZE.json"
_PROVENANCE_PATH = _REPO / "docs/diagnostics/ciepss_school_b_provenance.json"


def test_build_validity_run_plan_ten_trials() -> None:
    seeds_doc = load_study_seeds(path=_SEEDS_PATH)
    plan = build_validity_run_plan(seeds_doc=seeds_doc)
    assert len(plan) == 10
    assert plan[0] == ("trial-A", 500)
    assert plan[-1] == ("trial-J", 509)
    labels = [label for label, _seed in plan]
    assert labels == [f"trial-{chr(ord('A') + i)}" for i in range(10)]


def test_frozen_config_matches_prereg() -> None:
    profile = ValidityTrialProfile()
    snap = profile_snapshot(profile)
    assert snap["scenario_id"] == PREREG_FROZEN_CONFIG["scenario_id"]
    assert snap["agent_limit"] == PREREG_FROZEN_CONFIG["agent_limit"]
    assert snap["total_rounds"] == PREREG_FROZEN_CONFIG["total_rounds"]
    assert snap["model_profile_id"] == PREREG_FROZEN_CONFIG["model_profile_id"]
    assert snap["model_id"] == PREREG_FROZEN_CONFIG["model_id"]
    assert snap["visibility_policy"] == PREREG_FROZEN_CONFIG["visibility_policy"]
    assert snap["sampling_strategy"] == PREREG_FROZEN_CONFIG["sampling_strategy"]
    assert snap["turn_order_policy"] == PREREG_FROZEN_CONFIG["turn_order_policy"]
    assert snap["network_csv_rel_path"] == PREREG_FROZEN_CONFIG["network_csv_rel_path"]
    assert snap["rag_enabled"] is False
    assert snap["convergence_threshold"] is None
    for key in (
        "likert_self_report_enabled",
        "importance_scoring_enabled",
        "weighted_retrieval_enabled",
        "reflection_enabled",
    ):
        assert snap["mechanism_flags"][key] is False
        assert PREREG_FROZEN_CONFIG[key] is False


def test_assert_freeze_signed_requires_signature() -> None:
    assert_freeze_signed({"signature_status": "signed"})
    with pytest.raises(RuntimeError, match="not signed"):
        assert_freeze_signed({"signature_status": "unsigned"})


def test_assert_fixture_provenance_matches_repo_files() -> None:
    freeze = load_platform_freeze(path=_FREEZE_PATH)
    provenance = load_fixture_provenance(path=_PROVENANCE_PATH)
    assert_freeze_signed(freeze)
    assert_fixture_provenance_matches(freeze=freeze, provenance=provenance)


def test_resolve_validity_manifest_write_path_dry_run_skips_by_default() -> None:
    assert resolve_validity_manifest_write_path(mode="dry_run", manifest_out=None, root=_REPO) is None


def test_resolve_validity_manifest_write_path_dry_run_refuses_production(tmp_path: Path) -> None:
    production = default_manifest_path(root=_REPO)
    with pytest.raises(RuntimeError, match="refuses to write the production validity manifest"):
        resolve_validity_manifest_write_path(mode="dry_run", manifest_out=production, root=_REPO)
    scratch = tmp_path / "scratch_manifest.json"
    assert resolve_validity_manifest_write_path(mode="dry_run", manifest_out=scratch, root=_REPO) == scratch


def test_resolve_validity_manifest_write_path_execute_defaults_to_production() -> None:
    production = default_manifest_path(root=_REPO)
    assert (
        resolve_validity_manifest_write_path(mode="execute", manifest_out=None, root=_REPO) == production
    )


def test_is_production_validity_manifest() -> None:
    production = default_manifest_path(root=_REPO)
    assert is_production_validity_manifest(production, root=_REPO) is True


@pytest.mark.asyncio
async def test_dry_run_writes_manifest(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    cfg = get_scenario("fsbb_comparator")
    extended_cfg = replace(cfg, personas=list(cfg.personas) * 3)
    persona_ids = [p.persona_id for p in extended_cfg.personas[:8]]
    expected = frozenset(
        validity_script.build_expected_run_agent_ids(persona_ids=persona_ids),
    )
    network_csv = FIXTURE_NETWORK.read_text(encoding="utf-8")
    assert parse_network_csv(network_csv, known_agent_ids=expected).edges

    manifest_out = tmp_path / "sstrf_validity_v2_manifest.json"

    async def _fake_user_scenario_exists(_sqlite_path: str, *, scenario_id: str) -> bool:
        return scenario_id == "ciepss_school_b"

    async def _fake_load_scenario_for_run(_sqlite_path: str, scenario_id: str):
        assert scenario_id == "ciepss_school_b"
        return extended_cfg, "registry"

    monkeypatch.setattr(validity_script, "user_scenario_exists", _fake_user_scenario_exists)
    monkeypatch.setattr(validity_script, "load_scenario_for_run", _fake_load_scenario_for_run)

    with tempfile.TemporaryDirectory() as tmp:
        db_path = os.path.join(tmp, "validity.sqlite")
        await init_db(db_path)
        monkeypatch.setenv("SQLITE_PATH", db_path)

        args = validity_script.build_parser().parse_args(
            [
                "--dry-run",
                "--network-csv-text",
                network_csv,
                "--manifest-out",
                str(manifest_out),
                "--sqlite-path",
                db_path,
            ],
        )
        payload = await validity_script._main_async(args)

    assert payload["mode"] == "dry_run"
    assert len(payload["trials"]) == 10
    assert all(t["status"] == "planned" for t in payload["trials"])
    assert all(t["simulation_id"] is None for t in payload["trials"])
    assert manifest_out.is_file()
    on_disk = json.loads(manifest_out.read_text(encoding="utf-8"))
    assert on_disk["harness"] == "sstrf-validity-v2"
    assert on_disk["trials"][0]["trial_label"] == "trial-A"
    assert on_disk["trials"][0]["random_seed"] == 500


@pytest.mark.asyncio
async def test_dry_run_leaves_production_manifest_untouched(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    production_manifest = default_manifest_path(root=_REPO)
    if not production_manifest.is_file():
        pytest.skip("production validity manifest not present")
    before = production_manifest.read_bytes()

    cfg = get_scenario("fsbb_comparator")
    extended_cfg = replace(cfg, personas=list(cfg.personas) * 3)
    network_csv = FIXTURE_NETWORK.read_text(encoding="utf-8")

    async def _fake_user_scenario_exists(_sqlite_path: str, *, scenario_id: str) -> bool:
        return scenario_id == "ciepss_school_b"

    async def _fake_load_scenario_for_run(_sqlite_path: str, scenario_id: str):
        return extended_cfg, "registry"

    monkeypatch.setattr(validity_script, "user_scenario_exists", _fake_user_scenario_exists)
    monkeypatch.setattr(validity_script, "load_scenario_for_run", _fake_load_scenario_for_run)

    with tempfile.TemporaryDirectory() as tmp:
        db_path = os.path.join(tmp, "validity.sqlite")
        await init_db(db_path)
        monkeypatch.setenv("SQLITE_PATH", db_path)

        args = validity_script.build_parser().parse_args(
            [
                "--dry-run",
                "--network-csv-text",
                network_csv,
                "--sqlite-path",
                db_path,
            ],
        )
        payload = await validity_script._main_async(args)

    assert payload["mode"] == "dry_run"
    assert payload["artifacts"] == {}
    assert production_manifest.read_bytes() == before


@pytest.mark.asyncio
async def test_stub_run_reaches_completed_for_one_trial(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "mirofish_backend.simulation.orchestrator.llm_complete",
        fake_llm_state_block,
    )

    cfg = get_scenario("fsbb_comparator")
    network_csv = FIXTURE_NETWORK.read_text(encoding="utf-8")
    profile = ValidityTrialProfile(
        scenario_id="fsbb_comparator",
        agent_limit=3,
        total_rounds=2,
    )

    with tempfile.TemporaryDirectory() as tmp:
        db_path = os.path.join(tmp, "validity_stub.sqlite")
        await init_db(db_path)
        monkeypatch.setenv("SQLITE_PATH", db_path)
        settings = get_settings()

        rec = await validity_script.run_validity_trial_via_api(
            settings=settings,
            profile=profile,
            trial_label="trial-A",
            seed=500,
            network_csv=network_csv,
            llm_provider="lmstudio",
        )

        assert rec.status == "completed"
        assert rec.simulation_id
        assert rec.economics_summary is not None
        bundle = await get_simulation_export_bundle(db_path, simulation_id=rec.simulation_id)
        assert bundle is not None
        snap = (bundle.get("run") or {}).get("config_snapshot") or {}
        assert snap.get("network_csv_applied") is True
        interaction = snap.get("interaction_policy") or {}
        assert interaction.get("turn_order_policy") == "hierarchical"

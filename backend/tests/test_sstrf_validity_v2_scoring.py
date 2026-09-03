"""sstrf-validity-v2 Part D — scoring pipeline wired to validity manifest."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

_REPO = Path(__file__).resolve().parents[2]
_SCRIPTS = _REPO / "scripts"
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

from sstrf_elicitation_instruments import validate_instruments  # noqa: E402
from sstrf_scoring_evidence import (  # noqa: E402
    VALIDITY_V2_MANIFEST_PATH,
    build_validity_v2_trial_mapping,
    load_validity_v2_manifest,
    trial_record_from_validity_label,
)

import run_sstrf_validity_scoring as scoring_script  # noqa: E402


def test_build_validity_v2_trial_mapping_ten_labels() -> None:
    if not VALIDITY_V2_MANIFEST_PATH.is_file():
        pytest.skip("validity manifest not present")
    manifest = load_validity_v2_manifest()
    mapping = build_validity_v2_trial_mapping(manifest)
    assert len(mapping) == 10
    assert mapping["trial-A"]["seed"] == 500
    assert mapping["trial-J"]["seed"] == 509


def test_trial_record_from_validity_label_loads_elicitation() -> None:
    if not VALIDITY_V2_MANIFEST_PATH.is_file():
        pytest.skip("validity manifest not present")
    manifest = load_validity_v2_manifest()
    record = trial_record_from_validity_label("trial-A", manifest)
    assert record.trial_label == "trial-A"
    assert record.seed == 500
    assert record.simulation_id
    assert len(record.elicitation_manifest.get("agents") or []) == 8


@pytest.mark.asyncio
async def test_validity_scoring_dry_run_one_trial() -> None:
    if not VALIDITY_V2_MANIFEST_PATH.is_file():
        pytest.skip("validity manifest not present")
    from mirofish_backend.config import get_settings

    args = scoring_script.build_parser().parse_args(
        [
            "--dry-run",
            "--trial-label",
            "trial-A",
            "--sqlite",
            get_settings().sqlite_path,
        ],
    )
    rc = await scoring_script.cmd_dry_run(args)
    assert rc == 0


def test_calibration_instruments_still_pass() -> None:
    report = validate_instruments()
    assert report["passed"] is True


def test_finalize_human_requires_all_cells(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from sstrf_scoring_cells import all_trial_cell_ids

    scoring_dir = tmp_path / "scoring"
    scoring_dir.mkdir()
    monkeypatch.setattr(scoring_script, "VALIDITY_V2_SCORING_DIR", scoring_dir)
    monkeypatch.setattr(
        scoring_script,
        "VALIDITY_V2_SCORING_MANIFEST",
        scoring_dir / "validity_v2_scoring_manifest.json",
    )
    monkeypatch.setattr(scoring_script, "SCORING_STATE", scoring_dir / "scoring_state.json")

    state = {
        "mode": "human_only",
        "human_scores_imported_at": "2026-08-26T00:00:00Z",
        "trials": {
            "trial-A": {
                "adjudicated": {cell_id: 1 for cell_id in all_trial_cell_ids()},
            },
        },
    }
    scoring_script._save_scoring_state(state)

    if not VALIDITY_V2_MANIFEST_PATH.is_file():
        pytest.skip("validity manifest not present")

    args = scoring_script.build_parser().parse_args(["--finalize-human"])
    with pytest.raises(RuntimeError, match="missing"):
        scoring_script.cmd_finalize_human(args)


def test_finalize_human_one_trial_subset(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Smoke: human finalize writes manifest when one trial fully scored (mapping mocked)."""
    from sstrf_scoring_cells import all_trial_cell_ids

    scoring_dir = tmp_path / "scoring"
    scoring_dir.mkdir()
    manifest_path = tmp_path / "manifest.json"
    monkeypatch.setattr(scoring_script, "VALIDITY_V2_SCORING_DIR", scoring_dir)
    monkeypatch.setattr(
        scoring_script,
        "VALIDITY_V2_SCORING_MANIFEST",
        scoring_dir / "validity_v2_scoring_manifest.json",
    )
    monkeypatch.setattr(scoring_script, "SCORING_STATE", scoring_dir / "scoring_state.json")
    monkeypatch.setattr(scoring_script, "VALIDITY_V2_MANIFEST_PATH", manifest_path)

    fake_mapping = {"trial-A": {"seed": 500, "simulation_id": "sim-a"}}
    monkeypatch.setattr(scoring_script, "build_validity_v2_trial_mapping", lambda _m: fake_mapping)
    monkeypatch.setattr(
        scoring_script,
        "load_validity_v2_manifest",
        lambda _p=None: {"trials": []},
    )
    monkeypatch.setattr(scoring_script, "attach_scoring_to_validity_manifest", lambda **_: None)
    monkeypatch.setattr(scoring_script, "save_validity_manifest_with_scoring", lambda **_: None)

    state = {
        "mode": "human_only",
        "human_scores_imported_at": "2026-08-26T00:00:00Z",
        "trials": {
            "trial-A": {
                "adjudicated": {cell_id: 2 for cell_id in all_trial_cell_ids()},
            },
        },
    }
    scoring_script._save_scoring_state(state)

    args = scoring_script.build_parser().parse_args(["--finalize-human", "--manifest", str(manifest_path)])
    rc = scoring_script.cmd_finalize_human(args)
    assert rc == 0
    out = json.loads((scoring_dir / "validity_v2_scoring_manifest.json").read_text())
    assert out["scoring_mode"] == "human_only"
    assert out["trials"][0]["rater"] == "Mark"
    assert out["drift_check"]["skipped"] is True

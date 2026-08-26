"""sstrf-validity-v2 Part D — scoring pipeline wired to validity manifest."""

from __future__ import annotations

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

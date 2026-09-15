"""sstrf-validity-v2 Part C — post-trial elicitation harness."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

_REPO = Path(__file__).resolve().parents[2]
_SCRIPTS = _REPO / "scripts"
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

import run_sstrf_validity_elicitation as elic_script  # noqa: E402

from mirofish_backend.config import get_settings  # noqa: E402
from mirofish_backend.diagnostics.sstrf_validity_v2 import default_manifest_path  # noqa: E402
from mirofish_backend.diagnostics.sstrf_validity_v2_elicitation import (  # noqa: E402
    completed_validity_trials,
    load_validity_manifest,
    trial_elicitation_dir,
)
from sstrf_elicitation_instruments import (  # noqa: E402
    CIEPSS_EXPECTED_PERSONA_IDS,
    validate_instruments,
)

_MANIFEST = default_manifest_path(root=_REPO)


def test_validate_instruments_passes_for_ciepss() -> None:
    report = validate_instruments()
    assert report["passed"] is True
    assert len(report["instruments"]) == len(CIEPSS_EXPECTED_PERSONA_IDS)
    assert all(entry["contamination_hits"] == [] for entry in report["instruments"])


def test_completed_validity_trials_from_manifest() -> None:
    if not _MANIFEST.is_file():
        pytest.skip("validity manifest not present (Part B not run locally)")
    manifest = load_validity_manifest(path=_MANIFEST, root=_REPO)
    trials = completed_validity_trials(manifest)
    assert len(trials) == 10
    assert trials[0]["trial_label"] == "trial-A"
    assert trials[0]["simulation_id"]


@pytest.mark.asyncio
async def test_dry_run_elicitation_for_trial_a(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    if not _MANIFEST.is_file():
        pytest.skip("validity manifest not present (Part B not run locally)")
    manifest = load_validity_manifest(path=_MANIFEST, root=_REPO)
    trial = next(t for t in completed_validity_trials(manifest) if t["trial_label"] == "trial-A")
    settings = get_settings()
    out_root = tmp_path / "elicitation"

    monkeypatch.setattr(
        elic_script,
        "trial_elicitation_dir",
        lambda *, trial_label, root=None: out_root / trial_label,
    )

    elic_manifest = await elic_script.run_trial_elicitation(
        simulation_id=str(trial["simulation_id"]),
        trial_label="trial-A",
        sqlite_path=settings.sqlite_path,
        execute=False,
        max_tokens=256,
        output_dir=out_root / "trial-A",
    )

    assert elic_manifest["agent_count"] == len(CIEPSS_EXPECTED_PERSONA_IDS)
    assert elic_manifest["execute"] is False
    agent_files = list((out_root / "trial-A").glob("*.json"))
    assert len(agent_files) == len(CIEPSS_EXPECTED_PERSONA_IDS) + 1  # agents + manifest
    sample = json.loads(agent_files[0].read_text(encoding="utf-8"))
    assert sample["dry_run"] is True
    assert sample["raw_response"] is None


@pytest.mark.asyncio
async def test_batch_dry_run_updates_validity_manifest(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    if not _MANIFEST.is_file():
        pytest.skip("validity manifest not present (Part B not run locally)")
    manifest_copy = tmp_path / "manifest.json"
    manifest_copy.write_text(_MANIFEST.read_text(encoding="utf-8"), encoding="utf-8")
    out_root = tmp_path / "elicitation"
    settings = get_settings()

    monkeypatch.setattr(
        elic_script,
        "default_elicitation_root",
        lambda *, root=None: out_root,
    )
    monkeypatch.setattr(
        elic_script,
        "trial_elicitation_dir",
        lambda *, trial_label, root=None: out_root / trial_label,
    )

    args = elic_script.build_parser().parse_args(
        [
            "--dry-run",
            "--manifest",
            str(manifest_copy),
            "--sqlite-path",
            settings.sqlite_path,
            "--trial-label",
            "trial-A",
        ],
    )
    payload = await elic_script._main_async(args)
    assert payload["status"] == "ok"
    assert payload["trial_count"] == 1
    assert payload["manifest_written"] is True

    updated = json.loads(manifest_copy.read_text(encoding="utf-8"))
    trial_a = next(t for t in updated["trials"] if t["trial_label"] == "trial-A")
    assert "elicitation" in trial_a
    assert trial_a["elicitation"]["agent_count"] == len(CIEPSS_EXPECTED_PERSONA_IDS)
    assert updated.get("elicitation_harness", {}).get("mode") == "dry_run"


@pytest.mark.asyncio
async def test_batch_dry_run_leaves_production_manifest_untouched(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    if not _MANIFEST.is_file():
        pytest.skip("validity manifest not present (Part B not run locally)")
    before = _MANIFEST.read_bytes()
    out_root = tmp_path / "elicitation"
    settings = get_settings()

    monkeypatch.setattr(
        elic_script,
        "default_elicitation_root",
        lambda *, root=None: out_root,
    )
    monkeypatch.setattr(
        elic_script,
        "trial_elicitation_dir",
        lambda *, trial_label, root=None: out_root / trial_label,
    )

    args = elic_script.build_parser().parse_args(
        [
            "--dry-run",
            "--sqlite-path",
            settings.sqlite_path,
            "--trial-label",
            "trial-A",
        ],
    )
    payload = await elic_script._main_async(args)
    assert payload["status"] == "ok"
    assert payload["manifest_written"] is False
    assert _MANIFEST.read_bytes() == before

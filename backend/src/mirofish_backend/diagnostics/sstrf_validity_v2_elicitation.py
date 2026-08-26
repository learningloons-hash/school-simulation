"""SSTRF validity-v2 post-trial elicitation helpers (Part C)."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from mirofish_backend.diagnostics.sstrf_validity_v2 import (
    DEFAULT_MODEL_ID,
    DEFAULT_SCENARIO_ID,
    default_manifest_path,
    repo_root,
    write_manifest,
)

VALIDITY_ELICITATION_ROOT = (
    "docs/research/runs/ciepss_school_b/validity_v2/elicitation"
)
VALIDITY_PINNED_MODEL = DEFAULT_MODEL_ID


def default_elicitation_root(*, root: Path | None = None) -> Path:
    return (root or repo_root()) / VALIDITY_ELICITATION_ROOT


def trial_elicitation_dir(*, trial_label: str, root: Path | None = None) -> Path:
    return default_elicitation_root(root=root) / trial_label


def load_validity_manifest(*, path: Path | None = None, root: Path | None = None) -> dict[str, Any]:
    manifest_path = path or default_manifest_path(root=root)
    return json.loads(manifest_path.read_text(encoding="utf-8"))


def completed_validity_trials(manifest: dict[str, Any]) -> list[dict[str, Any]]:
    trials = manifest.get("trials") or []
    out = [t for t in trials if str(t.get("status") or "") == "completed" and t.get("simulation_id")]
    if not out:
        raise RuntimeError("validity manifest has no completed trials with simulation_id")
    return out


def rel_path_from_repo(path: Path, *, root: Path | None = None) -> str:
    base = root or repo_root()
    try:
        return str(path.relative_to(base))
    except ValueError:
        return str(path)


def attach_elicitation_to_trial(
    *,
    manifest: dict[str, Any],
    trial_label: str,
    elicitation_manifest: dict[str, Any],
    elicitation_manifest_path: Path,
    root: Path | None = None,
) -> None:
    rel = rel_path_from_repo(elicitation_manifest_path, root=root)
    block = {
        "manifest_path": rel,
        "agent_count": elicitation_manifest.get("agent_count"),
        "execute": elicitation_manifest.get("execute"),
        "model_id": elicitation_manifest.get("model_id"),
        "timestamp": elicitation_manifest.get("timestamp"),
    }
    for trial in manifest.get("trials") or []:
        if str(trial.get("trial_label") or "") == trial_label:
            trial["elicitation"] = block
            return
    raise KeyError(f"trial_label {trial_label!r} not found in validity manifest")


def finalize_validity_elicitation_manifest(
    *,
    manifest: dict[str, Any],
    mode: str,
    command: str,
    output_root: Path,
    root: Path | None = None,
) -> None:
    manifest["elicitation_harness"] = {
        "harness": "sstrf-validity-v2-elicitation",
        "mode": mode,
        "output_root": rel_path_from_repo(output_root, root=root),
        "scenario_id": DEFAULT_SCENARIO_ID,
        "pinned_model": VALIDITY_PINNED_MODEL,
        "command": command,
        "drafted_at": datetime.now(tz=UTC).isoformat(),
    }


def save_validity_manifest(*, manifest: dict[str, Any], path: Path | None = None, root: Path | None = None) -> Path:
    out = path or default_manifest_path(root=root)
    write_manifest(path=out, payload=manifest)
    return out

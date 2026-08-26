"""SSTRF validity-v2 scoring manifest helpers (Part D)."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from mirofish_backend.diagnostics.sstrf_validity_v2 import default_manifest_path, write_manifest


def attach_scoring_to_validity_manifest(
    *,
    manifest: dict[str, Any],
    scoring_manifest_path: Path,
    mode: str,
    command: str,
    root: Path | None = None,
) -> None:
    base = root or default_manifest_path().parents[2]
    try:
        rel = str(scoring_manifest_path.relative_to(base))
    except ValueError:
        rel = str(scoring_manifest_path)
    manifest["scoring_harness"] = {
        "harness": "sstrf-validity-v2-scoring",
        "mode": mode,
        "scoring_manifest_path": rel,
        "command": command,
        "drafted_at": datetime.now(tz=UTC).isoformat(),
    }


def save_validity_manifest_with_scoring(
    *,
    manifest: dict[str, Any],
    path: Path | None = None,
    root: Path | None = None,
) -> Path:
    out = path or default_manifest_path(root=root)
    write_manifest(path=out, payload=manifest)
    return out

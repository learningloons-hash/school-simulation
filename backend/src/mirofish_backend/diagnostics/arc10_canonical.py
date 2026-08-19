"""Committed Arc 10 canonical baseline inputs (senna-iter-49 blocker B6)."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

_REPO_ROOT = Path(__file__).resolve().parents[4]
DEFAULT_CANONICAL_BUNDLE = (
    _REPO_ROOT / "backend/tests/fixtures/arc10/canonical_baseline_inputs.json"
)


def fixture_dir_hashes(fixtures_dir: Path) -> dict[str, str]:
    out: dict[str, str] = {}
    for path in sorted(fixtures_dir.glob("*.json")):
        digest = hashlib.sha256(path.read_bytes()).hexdigest()[:16]
        out[path.name] = digest
    return out


def load_canonical_bundle(path: Path | None = None) -> dict[str, Any]:
    bundle_path = path or DEFAULT_CANONICAL_BUNDLE
    return json.loads(bundle_path.read_text(encoding="utf-8"))


def summary_from_canonical_bundle(bundle: dict[str, Any]) -> dict[str, Any]:
    """Build the combined summary dict used by ``generate_baseline_markdown``."""
    summary = dict(bundle.get("summary") or {})
    provenance = bundle.get("provenance") or {}
    summary.setdefault("inputs", {})
    summary["inputs"] = {
        **summary.get("inputs", {}),
        **{k: v for k, v in provenance.items() if k not in ("summary", "provenance", "bundle_version")},
    }
    return summary


def build_canonical_bundle(
    *,
    summary: dict[str, Any],
    provenance: dict[str, Any],
    bundle_version: int = 1,
) -> dict[str, Any]:
    return {
        "bundle_version": bundle_version,
        "provenance": provenance,
        "summary": summary,
    }

"""Committed Arc 10 canonical baseline inputs (senna-iter-49 blocker B6)."""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path
from typing import Any

_REPO_ROOT = Path(__file__).resolve().parents[4]
_DEFAULT_FIXTURES = _REPO_ROOT / "backend/tests/fixtures/membench"
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


def _scripts_path() -> Path:
    return _REPO_ROOT / "scripts"


def _import_membench():
    scripts = str(_scripts_path())
    if scripts not in sys.path:
        sys.path.insert(0, scripts)
    from membench_adapter import run_membench_suite

    return run_membench_suite


def _resolve_fixtures_dir(raw: str | Path | None) -> Path:
    if not raw:
        return _DEFAULT_FIXTURES
    path = Path(raw)
    if not path.is_absolute():
        path = _REPO_ROOT / path
    return path.resolve()


def verify_fixture_hashes(fixtures_dir: Path, expected: dict[str, str]) -> None:
    if not expected:
        return
    actual = fixture_dir_hashes(fixtures_dir)
    mismatches = {
        name: (expected.get(name), actual.get(name))
        for name in sorted(set(expected) | set(actual))
        if expected.get(name) != actual.get(name)
    }
    if mismatches:
        raise ValueError(f"MemBench fixture hash mismatch: {mismatches}")


def recompute_summary_from_canonical_bundle(bundle: dict[str, Any]) -> dict[str, Any]:
    """
    Recompute the combined Arc 10 summary from committed inputs.

    Runs MemBench via the adapter, assembles the interview section from stored
    response/score rows, and merges the memory-context fragment — never pass-through
    of a pre-baked ``summary`` blob.
    """
    from mirofish_backend.diagnostics.arc10_baseline import build_combined_arc10_summary
    from mirofish_backend.diagnostics.architectural_interview import (
        summarize_interview_results,
        validate_interview_completeness,
    )

    provenance = bundle.get("provenance") or {}
    inputs = bundle.get("inputs") or {}

    membench_cfg = inputs.get("membench") or {}
    fixtures_dir = _resolve_fixtures_dir(membench_cfg.get("fixtures_dir"))
    seed = int(membench_cfg.get("seed", provenance.get("membench_seed", 42)))
    answer_mode = str(
        membench_cfg.get("answer_mode", provenance.get("membench_answer_mode", "memory_match"))
    )
    verify_fixture_hashes(fixtures_dir, provenance.get("membench_fixture_hashes") or {})

    run_membench_suite = _import_membench()
    membench = run_membench_suite(
        fixtures_dir=fixtures_dir,
        seed=seed,
        answer_mode=answer_mode,
    )

    interview_inputs = inputs.get("architectural_interview") or {}
    responses = list(interview_inputs.get("responses") or [])
    scores = list(interview_inputs.get("scores") or [])
    expected_agents = list(interview_inputs.get("expected_agents") or [])
    validate_interview_completeness(
        responses,
        scores,
        expected_agent_ids=expected_agents,
    )
    interview_section = summarize_interview_results(responses, scores)
    interview_section["responses"] = responses
    interview_section["scores"] = scores

    memory_context = dict(inputs.get("memory_context") or {})
    simulation_id = str(inputs.get("simulation_id") or "arc10-canonical-baseline")
    runner_inputs = {
        "membench_seed": seed,
        "membench_answer_mode": answer_mode,
        "fixtures_dir": str(fixtures_dir.relative_to(_REPO_ROOT))
        if fixtures_dir.is_relative_to(_REPO_ROOT)
        else str(fixtures_dir),
        "execute_interview": False,
        "source": "canonical_recompute",
    }
    if provenance.get("code_revision"):
        runner_inputs["code_revision"] = provenance["code_revision"]

    return build_combined_arc10_summary(
        simulation_id=simulation_id,
        memory_context_summary=memory_context,
        membench=membench,
        architectural_interview=interview_section,
        inputs=runner_inputs,
    )


def summary_from_canonical_bundle(bundle: dict[str, Any]) -> dict[str, Any]:
    """Build the combined summary dict used by ``generate_baseline_markdown``."""
    if bundle.get("inputs"):
        return recompute_summary_from_canonical_bundle(bundle)

    # Legacy v1 bundles stored a pre-baked summary — recompute when possible.
    legacy_summary = bundle.get("summary")
    if legacy_summary:
        return dict(legacy_summary)
    raise ValueError("canonical bundle missing inputs and summary")


def build_canonical_bundle(
    *,
    inputs: dict[str, Any],
    provenance: dict[str, Any],
    bundle_version: int = 2,
) -> dict[str, Any]:
    return {
        "bundle_version": bundle_version,
        "provenance": provenance,
        "inputs": inputs,
    }

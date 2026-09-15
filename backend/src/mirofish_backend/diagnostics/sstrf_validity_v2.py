"""SSTRF RQ1 validity-trial simulation harness (sstrf-validity-v2 Part A)."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from mirofish_backend.diagnostics.arc12_study_rehearsal import (
    build_expected_run_agent_ids,
    count_context_length_failures,
    count_llm_errors,
    extract_mechanics_metrics,
    load_documented_network_csv,
)
from mirofish_backend.llm.model_profiles import ANTHROPIC_DEFAULT_ID

HARNESS_ID = "sstrf-validity-v2"
MANIFEST_SCHEMA_VERSION = 1

DEFAULT_SCENARIO_ID = "ciepss_school_b"
DEFAULT_AGENT_LIMIT = 8
DEFAULT_TOTAL_ROUNDS = 20
DEFAULT_MODEL_ID = "claude-haiku-4-5-20251001"
DEFAULT_MODEL_PROFILE_ID = ANTHROPIC_DEFAULT_ID
DEFAULT_VISIBILITY_POLICY = "network_bounded"
DEFAULT_SAMPLING_STRATEGY = "full_census"
DEFAULT_TURN_ORDER_POLICY = "hierarchical"
DEFAULT_NETWORK_CSV_REL = "docs/research/fixtures/ciepss_school_b_network.csv"

FROZEN_MECHANISM_FLAGS: dict[str, bool] = {
    "likert_self_report_enabled": False,
    "importance_scoring_enabled": False,
    "weighted_retrieval_enabled": False,
    "reflection_enabled": False,
}

# Binding fields from PREREG_SSTRF_RQ1_V2.md §4 — used by CI assertions.
PREREG_FROZEN_CONFIG: dict[str, Any] = {
    "scenario_id": DEFAULT_SCENARIO_ID,
    "agent_limit": DEFAULT_AGENT_LIMIT,
    "total_rounds": DEFAULT_TOTAL_ROUNDS,
    "model_profile_id": DEFAULT_MODEL_PROFILE_ID,
    "model_id": DEFAULT_MODEL_ID,
    "visibility_policy": DEFAULT_VISIBILITY_POLICY,
    "sampling_strategy": DEFAULT_SAMPLING_STRATEGY,
    "turn_order_policy": DEFAULT_TURN_ORDER_POLICY,
    "network_csv_rel_path": DEFAULT_NETWORK_CSV_REL,
    "rag_enabled": False,
    "convergence_threshold": None,
    **FROZEN_MECHANISM_FLAGS,
}


def repo_root() -> Path:
    return Path(__file__).resolve().parents[4]


def default_seeds_path(*, root: Path | None = None) -> Path:
    return (root or repo_root()) / "docs/diagnostics/ARC12_STUDY_SEEDS.json"


def default_freeze_path(*, root: Path | None = None) -> Path:
    return (root or repo_root()) / "docs/diagnostics/ARC12_PLATFORM_FREEZE.json"


def default_provenance_path(*, root: Path | None = None) -> Path:
    return (root or repo_root()) / "docs/diagnostics/ciepss_school_b_provenance.json"


def default_manifest_path(*, root: Path | None = None) -> Path:
    return (root or repo_root()) / "docs/diagnostics/sstrf_validity_v2_manifest.json"


@dataclass(frozen=True)
class ValidityTrialProfile:
    scenario_id: str = DEFAULT_SCENARIO_ID
    agent_limit: int = DEFAULT_AGENT_LIMIT
    total_rounds: int = DEFAULT_TOTAL_ROUNDS
    visibility_policy: str = DEFAULT_VISIBILITY_POLICY
    sampling_strategy: str = DEFAULT_SAMPLING_STRATEGY
    turn_order_policy: str = DEFAULT_TURN_ORDER_POLICY
    model_profile_id: str = DEFAULT_MODEL_PROFILE_ID
    model_id: str = DEFAULT_MODEL_ID
    rag_enabled: bool = False
    network_csv_rel_path: str = DEFAULT_NETWORK_CSV_REL


@dataclass
class ValidityTrialRecord:
    trial_label: str
    random_seed: int
    simulation_id: str | None
    status: str
    total_rounds: int
    economics_summary: dict[str, Any] | None = field(default_factory=dict)


def load_study_seeds(*, path: Path | None = None, root: Path | None = None) -> dict[str, Any]:
    seeds_path = path or default_seeds_path(root=root)
    return json.loads(seeds_path.read_text(encoding="utf-8"))


def load_platform_freeze(*, path: Path | None = None, root: Path | None = None) -> dict[str, Any]:
    freeze_path = path or default_freeze_path(root=root)
    return json.loads(freeze_path.read_text(encoding="utf-8"))


def load_fixture_provenance(*, path: Path | None = None, root: Path | None = None) -> dict[str, Any]:
    provenance_path = path or default_provenance_path(root=root)
    return json.loads(provenance_path.read_text(encoding="utf-8"))


def build_validity_run_plan(*, seeds_doc: dict[str, Any]) -> list[tuple[str, int]]:
    """Return (trial_label, random_seed) tuples in seed-file order."""
    trials = seeds_doc.get("trials") or []
    plan: list[tuple[str, int]] = []
    for row in trials:
        label = str(row.get("trial_label") or "")
        seed = int(row.get("random_seed") or 0)
        if not label or seed <= 0:
            raise ValueError(f"invalid trial row in study seeds: {row!r}")
        plan.append((label, seed))
    if not plan:
        raise ValueError("study seeds file contains no trials")
    return plan


def assert_freeze_signed(freeze: dict[str, Any]) -> None:
    status = str(freeze.get("signature_status") or "")
    if status != "signed":
        raise RuntimeError(
            "platform freeze is not signed — live validity trials require Mark's signature "
            f"(signature_status={status!r}; see docs/diagnostics/ARC12_PLATFORM_FREEZE.json)."
        )


def assert_fixture_provenance_matches(*, freeze: dict[str, Any], provenance: dict[str, Any]) -> None:
    fp = freeze.get("fixture_provenance") or {}
    keys = ("scenario_id", "source_repo", "source_commit", "yaml_rel_path", "dirty")
    mismatches: list[str] = []
    for key in keys:
        freeze_val = fp.get(key)
        prov_val = provenance.get(key)
        if freeze_val != prov_val:
            mismatches.append(f"{key}: freeze={freeze_val!r} provenance={prov_val!r}")
    network_rel = fp.get("network_csv_rel_path")
    if network_rel != DEFAULT_NETWORK_CSV_REL:
        mismatches.append(
            f"network_csv_rel_path: freeze={network_rel!r} expected={DEFAULT_NETWORK_CSV_REL!r}",
        )
    if mismatches:
        raise RuntimeError(
            "fixture provenance does not match platform freeze:\n  "
            + "\n  ".join(mismatches),
        )


def profile_snapshot(profile: ValidityTrialProfile) -> dict[str, Any]:
    return {
        "scenario_id": profile.scenario_id,
        "agent_limit": profile.agent_limit,
        "total_rounds": profile.total_rounds,
        "model_profile_id": profile.model_profile_id,
        "model_id": profile.model_id,
        "visibility_policy": profile.visibility_policy,
        "sampling_strategy": profile.sampling_strategy,
        "turn_order_policy": profile.turn_order_policy,
        "network_csv_rel_path": profile.network_csv_rel_path,
        "rag_enabled": profile.rag_enabled,
        "convergence_threshold": None,
        "mechanism_flags": dict(FROZEN_MECHANISM_FLAGS),
    }


def extract_economics_summary(*, bundle: dict[str, Any], wall_clock_seconds: float) -> dict[str, Any]:
    """Economics-only summary for manifest (no transcript content)."""
    mechanics = extract_mechanics_metrics(bundle=bundle, wall_clock_seconds=wall_clock_seconds)
    return {
        "wall_clock_seconds": mechanics.get("wall_clock_seconds"),
        "total_input_tokens": mechanics.get("total_input_tokens"),
        "total_output_tokens": mechanics.get("total_output_tokens"),
        "estimated_cost_usd": mechanics.get("estimated_cost_usd"),
    }


def check_transcript_qa(bundle: dict[str, Any], *, simulation_id: str, trial_label: str, seed: int) -> None:
    transcript = bundle.get("transcript") or []
    llm_err = count_llm_errors(transcript)
    if llm_err:
        raise RuntimeError(
            f"[validity] {llm_err} LLM error turns in {simulation_id} "
            f"(trial={trial_label!r}, seed={seed}) — run not usable.",
        )
    ctx_err = count_context_length_failures(transcript)
    if ctx_err:
        raise RuntimeError(
            f"[validity] {ctx_err} context-length failures in {simulation_id} "
            f"(trial={trial_label!r}, seed={seed}) — run not usable.",
        )


def build_planned_trial_records(
    *,
    plan: list[tuple[str, int]],
    total_rounds: int,
) -> list[ValidityTrialRecord]:
    return [
        ValidityTrialRecord(
            trial_label=label,
            random_seed=seed,
            simulation_id=None,
            status="planned",
            total_rounds=total_rounds,
            economics_summary=None,
        )
        for label, seed in plan
    ]


def build_manifest_payload(
    *,
    profile: ValidityTrialProfile,
    records: list[ValidityTrialRecord],
    command: str,
    mode: str,
    freeze: dict[str, Any],
    pre_reg_path: str,
    freeze_path: str,
) -> dict[str, Any]:
    return {
        "schema_version": MANIFEST_SCHEMA_VERSION,
        "harness": HARNESS_ID,
        "pre_reg_path": pre_reg_path,
        "freeze_path": freeze_path,
        "platform_code_commit": freeze.get("platform_code_commit"),
        "profile": profile_snapshot(profile),
        "command": command,
        "drafted_at": datetime.now(tz=UTC).isoformat(),
        "mode": mode,
        "trials": [
            {
                "trial_label": r.trial_label,
                "random_seed": r.random_seed,
                "simulation_id": r.simulation_id,
                "status": r.status,
                "total_rounds": r.total_rounds,
                "economics_summary": r.economics_summary,
            }
            for r in records
        ],
    }


def write_manifest(*, path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def is_production_validity_manifest(path: Path, *, root: Path | None = None) -> bool:
    """True when ``path`` resolves to the committed validity-trial manifest."""
    production = default_manifest_path(root=root)
    try:
        return path.resolve() == production.resolve()
    except OSError:
        return False


def resolve_validity_manifest_write_path(
    *,
    mode: str,
    manifest_out: Path | None,
    root: Path | None = None,
) -> Path | None:
    """
    Study-artefact rule: dry-run never writes the production manifest by default.

    - ``dry_run`` + no ``manifest_out`` → skip write (``None``).
    - ``dry_run`` + production ``manifest_out`` → refuse (explicit path still blocked).
    - ``dry_run`` + scratch ``manifest_out`` → write there (tests / local preview).
    - ``execute`` + no ``manifest_out`` → production manifest (live harness default).
    """
    production = default_manifest_path(root=root)
    if mode == "dry_run":
        if manifest_out is None:
            return None
        if is_production_validity_manifest(manifest_out, root=root):
            raise RuntimeError(
                f"--dry-run refuses to write the production validity manifest ({production}). "
                "Omit --manifest-out to skip writing, or pass a scratch path."
            )
        return manifest_out
    return manifest_out or production


__all__ = [
    "HARNESS_ID",
    "DEFAULT_NETWORK_CSV_REL",
    "FROZEN_MECHANISM_FLAGS",
    "PREREG_FROZEN_CONFIG",
    "ValidityTrialProfile",
    "ValidityTrialRecord",
    "assert_fixture_provenance_matches",
    "assert_freeze_signed",
    "build_expected_run_agent_ids",
    "build_manifest_payload",
    "build_planned_trial_records",
    "build_validity_run_plan",
    "check_transcript_qa",
    "default_manifest_path",
    "extract_economics_summary",
    "is_production_validity_manifest",
    "load_documented_network_csv",
    "load_fixture_provenance",
    "load_platform_freeze",
    "load_study_seeds",
    "profile_snapshot",
    "repo_root",
    "resolve_validity_manifest_write_path",
    "write_manifest",
]

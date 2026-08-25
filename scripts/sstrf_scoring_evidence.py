"""Assemble and redact scoreable evidence for SSTRF RQ1 judging (GM-F v2)."""

from __future__ import annotations

import json
import random
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from sstrf_elicitation_transcript import _strip_state_block
from sstrf_scoring_cells import SCORED_STAFF_AGENTS

ROOT = Path(__file__).resolve().parents[1]
PHASE_V_MANIFEST = ROOT / "docs/research/runs/ciepss_school_b/phase_v_manifest.json"
ELICITATION_DIR = ROOT / "docs/research/runs/ciepss_school_b/elicitation"
SCORING_DIR = ROOT / "docs/research/runs/ciepss_school_b/scoring"
TRIAL_LABEL_MAP = SCORING_DIR / "trial_label_map.json"
SCORING_MANIFEST = SCORING_DIR / "phase_v_scoring_manifest.json"
CALIBRATION_SET = ROOT / "docs/research/SSTRF_RATER_CALIBRATION_SET.md"
DEFAULT_SQLITE = ROOT / "backend/data/sstrf_phase_v.sqlite"
FALLBACK_SQLITE = ROOT / "backend/data/sstrf_calibration.sqlite"

FORBIDDEN_RATER_KEYS = frozenset(
    {
        "config_snapshot",
        "economics",
        "agent_state_snapshots",
        "random_seed",
        "simulation_id",
        "seed",
        "scenario_yaml",
        "preflight",
        "run_id",
        "condition",
        "condition_label",
        "trial_number",
    }
)

TRIAL_LABELS = [f"trial-{chr(ord('A') + i)}" for i in range(10)]

_REDACT_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"\b[0-9a-f]{32}\b", re.I), "[redacted-id]"),
    (re.compile(r"phase_v_seed\d+", re.I), "[redacted-label]"),
    (re.compile(r"\bseed[_\s:=]+\d+\b", re.I), "[redacted-seed]"),
    (re.compile(r"\btrial-[A-J]\b", re.I), "[redacted-label]"),
    (re.compile(r"\bcondition[_\s:=]+[\w-]+\b", re.I), "[redacted-condition]"),
    (re.compile(r"\brun[_\s:=]+\d+\b", re.I), "[redacted-run]"),
    (
        re.compile(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})?"),
        "[redacted-time]",
    ),
]


@dataclass
class TrialEvidence:
    trial_label: str
    elicitation: list[dict[str, Any]]
    transcript: list[dict[str, Any]]


@dataclass
class TrialRecord:
    trial_label: str
    seed: int
    simulation_id: str
    elicitation_manifest: dict[str, Any]


def load_phase_v_manifest(path: Path | None = None) -> dict[str, Any]:
    manifest_path = path or PHASE_V_MANIFEST
    return json.loads(manifest_path.read_text(encoding="utf-8"))


def get_accepted_attempt(trial: dict[str, Any]) -> dict[str, Any]:
    attempts = list(trial.get("attempts") or [])
    passed = [a for a in attempts if a.get("full_gate_passed")]
    if not passed:
        raise ValueError(f"seed {trial.get('seed')} has no full_gate_passed attempt")
    return max(passed, key=lambda a: int(a.get("attempt_number") or 0))


def accepted_trials(manifest: dict[str, Any]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for trial in manifest.get("trials") or []:
        try:
            get_accepted_attempt(trial)
        except ValueError:
            continue
        out.append(trial)
    return sorted(out, key=lambda t: int(t["seed"]))


def _redact_text(text: str) -> str:
    out = str(text or "")
    for pattern, repl in _REDACT_PATTERNS:
        out = pattern.sub(repl, out)
    return out


def load_elicitation_responses(
    *,
    elicitation_manifest: dict[str, Any],
    repo_root: Path | None = None,
) -> list[dict[str, Any]]:
    base = repo_root or ROOT
    rows: list[dict[str, Any]] = []
    for agent in elicitation_manifest.get("agents") or []:
        rel = str(agent.get("output_path") or "").strip()
        if not rel:
            raise RuntimeError("elicitation agent missing output_path")
        path = Path(rel)
        if not path.is_absolute():
            path = base / rel
        payload = json.loads(path.read_text(encoding="utf-8"))
        raw = str(payload.get("raw_response") or "")
        rows.append(
            {
                "persona_id": str(agent.get("persona_id") or payload.get("persona_id") or ""),
                "role": str(agent.get("role") or payload.get("role") or ""),
                "agent_name": str(agent.get("agent_name") or payload.get("agent_name") or ""),
                "raw_response": _redact_text(_strip_state_block(raw)),
            }
        )
    return rows


def build_full_transcript(bundle: dict[str, Any]) -> list[dict[str, Any]]:
    turns: list[dict[str, Any]] = []
    for turn in bundle.get("transcript") or []:
        raw = _strip_state_block(str(turn.get("raw_response") or ""))
        turns.append(
            {
                "round_number": int(turn.get("round_number") or 0),
                "turn_index": int(turn.get("turn_index") or 0),
                "agent_id": str(turn.get("agent_id") or ""),
                "agent_name": str(turn.get("agent_name") or ""),
                "agent_role": str(turn.get("agent_role") or ""),
                "raw_response": _redact_text(raw),
            }
        )
    return turns


def assert_rater_payload_clean(payload: Any, *, label: str = "payload") -> None:
    if isinstance(payload, dict):
        for key in payload:
            if key in FORBIDDEN_RATER_KEYS:
                raise ValueError(f"{label} contains forbidden key {key!r}")
        for value in payload.values():
            assert_rater_payload_clean(value, label=label)
    elif isinstance(payload, list):
        for item in payload:
            assert_rater_payload_clean(item, label=label)
    elif isinstance(payload, str):
        lowered = payload.lower()
        forbidden_substrings = (
            "config_snapshot",
            "economics",
            "random_seed",
            "simulation_id",
            "condition_label",
            "phase_v_seed",
        )
        if any(token in lowered for token in forbidden_substrings):
            raise ValueError(f"{label} contains forbidden substring in text")


def staff_elicitation_rows(elicitation: list[dict[str, Any]]) -> list[dict[str, Any]]:
    staff = set(SCORED_STAFF_AGENTS)
    return [row for row in elicitation if str(row.get("persona_id") or "") in staff]


def build_rater_payload(evidence: TrialEvidence) -> dict[str, Any]:
    payload = {
        "elicitation": staff_elicitation_rows(evidence.elicitation),
        "transcript": evidence.transcript,
    }
    assert_rater_payload_clean(payload)
    return payload


def build_elicitation_only_rater_payload(evidence: TrialEvidence) -> dict[str, Any]:
    """Tier 2 drift-check packet: elicitation answers only (no transcript)."""
    payload = {
        "elicitation": staff_elicitation_rows(evidence.elicitation),
    }
    assert_rater_payload_clean(payload)
    return payload


def build_tier2_elicitation_packet(record: TrialRecord) -> dict[str, Any]:
    elicitation = load_elicitation_responses(elicitation_manifest=record.elicitation_manifest)
    evidence = TrialEvidence(
        trial_label=record.trial_label,
        elicitation=elicitation,
        transcript=[],
    )
    return build_elicitation_only_rater_payload(evidence)


def build_tier2_drift_packets(
    trial_labels: list[str],
    *,
    mapping: dict[str, dict[str, Any]],
    manifest: dict[str, Any],
) -> dict[str, Any]:
    packets: dict[str, Any] = {}
    for label in sorted(trial_labels):
        record = trial_record_from_label(label, mapping, manifest)
        packets[label] = build_tier2_elicitation_packet(record)
    return {
        "design": "tier2_elicitation_only_v1_5",
        "evidence_scope": "elicitation_only",
        "sampled_trials": sorted(trial_labels),
        "packets": packets,
    }


async def build_stage1_escalation_packets(
    disputed_cells: list[dict[str, str]],
    *,
    mapping: dict[str, dict[str, Any]],
    manifest: dict[str, Any],
    sqlite_path: Path,
    get_bundle=None,
) -> dict[str, Any]:
    """Stage 1 escalation: add full transcript for disputed cells only (pre-reg v1.5 §7.2)."""
    if not disputed_cells:
        return {
            "design": "stage1_escalation_v1_5",
            "evidence_scope": "elicitation_plus_transcript",
            "disputed_cells": [],
            "packets": {},
        }
    trials_needed = sorted({str(c["trial_label"]) for c in disputed_cells})
    packets: dict[str, Any] = {}
    for label in trials_needed:
        record = trial_record_from_label(label, mapping, manifest)
        evidence = await assemble_trial_evidence(
            record=record,
            sqlite_path=sqlite_path,
            get_bundle=get_bundle,
        )
        propositions = sorted(
            {
                str(c["proposition"])
                for c in disputed_cells
                if str(c["trial_label"]) == label
            }
        )
        packets[label] = {
            "trial_label": label,
            "propositions_to_rescore": propositions,
            "elicitation": evidence.elicitation,
            "transcript": evidence.transcript,
        }
    return {
        "design": "stage1_escalation_v1_5",
        "evidence_scope": "elicitation_plus_transcript",
        "disputed_cells": disputed_cells,
        "packets": packets,
    }


def assign_trial_labels(
    trials: list[dict[str, Any]],
    *,
    assignment_seed: int = 42,
) -> dict[str, dict[str, Any]]:
    rng = random.Random(assignment_seed)
    labels = TRIAL_LABELS[: len(trials)]
    shuffled = trials.copy()
    rng.shuffle(shuffled)
    mapping: dict[str, dict[str, Any]] = {}
    for label, trial in zip(labels, shuffled, strict=True):
        attempt = get_accepted_attempt(trial)
        mapping[label] = {
            "seed": int(trial["seed"]),
            "simulation_id": str(attempt["simulation_id"]),
        }
    return mapping


def load_trial_label_map(path: Path | None = None) -> dict[str, dict[str, Any]]:
    p = path or TRIAL_LABEL_MAP
    if not p.exists():
        return {}
    return json.loads(p.read_text(encoding="utf-8"))


def save_trial_label_map(mapping: dict[str, dict[str, Any]], path: Path | None = None) -> None:
    p = path or TRIAL_LABEL_MAP
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(mapping, indent=2), encoding="utf-8")


def trial_record_from_label(
    label: str,
    mapping: dict[str, dict[str, Any]],
    manifest: dict[str, Any],
) -> TrialRecord:
    meta = mapping[label]
    seed = int(meta["seed"])
    simulation_id = str(meta["simulation_id"])
    for trial in manifest.get("trials") or []:
        if int(trial.get("seed")) != seed:
            continue
        attempt = get_accepted_attempt(trial)
        if str(attempt.get("simulation_id")) != simulation_id:
            continue
        elic = attempt.get("elicitation") or {}
        if not elic.get("agents"):
            raise KeyError(f"seed {seed} missing elicitation agents")
        return TrialRecord(
            trial_label=label,
            seed=seed,
            simulation_id=simulation_id,
            elicitation_manifest=elic,
        )
    raise KeyError(f"no manifest trial for label {label!r}")


async def assemble_trial_evidence(
    *,
    record: TrialRecord,
    sqlite_path: Path,
    get_bundle,
) -> TrialEvidence:
    from mirofish_backend.db.repo import get_simulation_export_bundle

    bundle_fn = get_bundle or get_simulation_export_bundle
    bundle = None
    for db_path in (sqlite_path, FALLBACK_SQLITE):
        if db_path != sqlite_path and not db_path.exists():
            continue
        bundle = await bundle_fn(str(db_path), simulation_id=record.simulation_id)
        if bundle is not None:
            break
    if bundle is None:
        raise RuntimeError(f"simulation {record.simulation_id!r} not found")

    elicitation = load_elicitation_responses(elicitation_manifest=record.elicitation_manifest)
    transcript = build_full_transcript(bundle)
    evidence = TrialEvidence(
        trial_label=record.trial_label,
        elicitation=elicitation,
        transcript=transcript,
    )
    assert_rater_payload_clean(build_rater_payload(evidence))
    return evidence


def _calibration_status_line(text: str) -> str | None:
    for line in text.splitlines()[:20]:
        stripped = line.strip()
        lower = stripped.lower()
        if lower.startswith("**status:") or lower.startswith("status:"):
            return stripped
    return None


def assert_calibration_set_signed() -> None:
    text = CALIBRATION_SET.read_text(encoding="utf-8")
    status = _calibration_status_line(text)
    if status is None:
        raise RuntimeError(
            "Calibration set missing Status line — GM-F sign-off required (§0)"
        )
    if re.search(r"^\*\*Status:\s*DRAFT\b", status, re.I) or re.search(
        r"^Status:\s*DRAFT\b", status, re.I
    ):
        raise RuntimeError("Calibration set still DRAFT — GM-F sign-off required (§0)")
    if not re.search(r"\bCOMPLETE\b|\bSIGNED\b", status, re.I):
        raise RuntimeError(
            "Calibration set Status is not COMPLETE/SIGNED — GM-F sign-off required (§0)"
        )


def assert_no_secret(payload: Any, secret: str) -> None:
    if secret and secret in json.dumps(payload, ensure_ascii=False):
        raise RuntimeError("secret material detected in output payload; refusing to save")

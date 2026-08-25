"""Shared cell identifiers for SSTRF RQ1 per-agent scoring (GM-F v2)."""

from __future__ import annotations

PROPOSITION_IDS = [f"P{i}" for i in range(1, 6)]

SCORED_STAFF_AGENTS: tuple[str, ...] = (
    "vice_principal_001",
    "hod_english_001",
    "senior_teacher_001",
    "teacher_001",
)
PER_AGENT_PROPOSITIONS: tuple[str, ...] = ("P1", "P3", "P4", "P5")
JUDGEMENTS_PER_TRIAL = len(PER_AGENT_PROPOSITIONS) * len(SCORED_STAFF_AGENTS) + 1  # 17


def trial_cell_id(proposition: str, agent_id: str | None = None) -> str:
    if proposition == "P2":
        return "P2"
    if agent_id is None:
        raise ValueError(f"agent_id required for {proposition}")
    return f"{proposition}:{agent_id}"


def all_trial_cell_ids() -> list[str]:
    cells = [trial_cell_id(p, a) for p in PER_AGENT_PROPOSITIONS for a in SCORED_STAFF_AGENTS]
    cells.append("P2")
    return cells


def proposition_for_cell(cell_id: str) -> str:
    return cell_id.split(":", 1)[0]

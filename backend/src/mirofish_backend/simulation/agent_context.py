"""
Per-agent runtime context (Iteration 10 + 13).

Versioned bundle consumed by interaction planning and prompts. Iteration 13 adds
survey-like **sections** (identity, attitudes, personal_history) as shallow dicts
merged from scenario YAML and optional population CSV overlays.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

# Bump when adding/removing top-level fields (record in config_snapshot).
AGENT_CONTEXT_VERSION = "2"


@dataclass(frozen=True)
class AgentContextV1:
    """
    Agent context contract (ADR-001; version **2** in Iteration 13).

    - ``slot_index``: 0-based position in the run roster (maps to roster CSV 1-based slot).
    - ``demographics``: age, sex, ethnicity, ses (Iteration 10–11 population alignment).
    - ``group_ids``: cohort membership from persona (Iteration 9).
    - ``identity``, ``attitudes``, ``personal_history``: optional structured attributes (Iteration 13).
    """

    version: str
    slot_index: int
    demographics: dict[str, Any]
    group_ids: tuple[str, ...]
    identity: dict[str, Any]
    attitudes: dict[str, Any]
    personal_history: dict[str, Any]

    def to_prompt_demographics(self) -> dict[str, Any]:
        """Flatten for system prompt (backward-compatible with pre-v1 prompts).

        Group membership is rendered separately via ``group_affiliations`` in
        ``build_system_prompt``; avoid duplicating here.
        """
        return dict(self.demographics)


def build_agent_context_v1(
    *,
    slot_index: int,
    demographics: dict[str, Any],
    group_ids: tuple[str, ...],
    identity: dict[str, Any] | None = None,
    attitudes: dict[str, Any] | None = None,
    personal_history: dict[str, Any] | None = None,
) -> AgentContextV1:
    return AgentContextV1(
        version=AGENT_CONTEXT_VERSION,
        slot_index=slot_index,
        demographics=dict(demographics),
        group_ids=group_ids,
        identity=dict(identity or {}),
        attitudes=dict(attitudes or {}),
        personal_history=dict(personal_history or {}),
    )


def attribute_sections_for_snapshot(ctx: AgentContextV1) -> dict[str, dict[str, Any]]:
    """JSON-serializable bundle for DB / export (Iteration 13)."""
    return {
        "identity": dict(ctx.identity),
        "attitudes": dict(ctx.attitudes),
        "personal_history": dict(ctx.personal_history),
    }

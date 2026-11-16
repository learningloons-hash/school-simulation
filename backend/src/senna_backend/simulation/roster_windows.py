"""Per-actor activity windows for roster join/leave (M-ROSTER). Pure functions only."""

from __future__ import annotations

import string
from dataclasses import dataclass
from typing import Any, Literal

from senna_backend.scenarios.registry import PersonaTemplate, RosterWindowsConfig

ALLOWED_HANDOVER_PLACEHOLDERS = frozenset(
    {"name", "role", "join_round", "total_rounds", "join_policy_event"}
)
ABSENCE_NOTICE_SCOPES = frozenset({"all_inactive", "departed_only", "none"})


@dataclass(frozen=True)
class ActivityWindow:
    agent_id: str
    active_from_round: int
    active_until_round: int
    absence_reason: str
    window_basis: str


def validate_handover_template(template: str) -> list[str]:
    """Return error messages for unknown placeholders (empty if OK)."""
    errors: list[str] = []
    for _literal, field_name, _format_spec, _conversion in string.Formatter().parse(template):
        if field_name is None:
            continue
        if field_name not in ALLOWED_HANDOVER_PLACEHOLDERS:
            errors.append(f"roster_windows.handover_template: unknown placeholder {{{field_name}}}")
    return errors


def _resolved_from_until(
    persona: PersonaTemplate,
    *,
    agent_id: str,
    total_rounds: int,
    warnings: list[str],
) -> tuple[int, int]:
    raw_from = persona.active_from_round
    raw_until = persona.active_until_round
    if raw_from is not None and not isinstance(raw_from, int):
        raise ValueError(f"activity window for {agent_id}: active_from_round must be an integer")
    if raw_until is not None and not isinstance(raw_until, int):
        raise ValueError(f"activity window for {agent_id}: active_until_round must be an integer")
    from_r = 1 if raw_from is None else int(raw_from)
    until_r = total_rounds if raw_until is None else int(raw_until)
    if from_r < 1:
        raise ValueError(f"activity window for {agent_id}: active_from_round must be >= 1")
    if until_r < 1:
        raise ValueError(f"activity window for {agent_id}: active_until_round must be >= 1")
    if from_r > until_r:
        raise ValueError(f"activity window for {agent_id}: active_from_round > active_until_round")
    if from_r > total_rounds:
        raise ValueError(
            f"activity window for {agent_id} starts after total_rounds={total_rounds}",
        )
    if until_r > total_rounds:
        warnings.append(
            f"activity window for {agent_id} clipped to total_rounds={total_rounds}",
        )
        until_r = total_rounds
    return from_r, until_r


def resolve_activity_windows(
    agent_ids: list[str],
    personas: list[PersonaTemplate],
    total_rounds: int,
) -> tuple[dict[str, ActivityWindow], list[str]]:
    if len(agent_ids) != len(personas):
        raise ValueError("agent_ids and personas length mismatch")
    warnings: list[str] = []
    windows: dict[str, ActivityWindow] = {}
    rounds = max(1, int(total_rounds))
    for aid, persona in zip(agent_ids, personas):
        from_r, until_r = _resolved_from_until(persona, agent_id=aid, total_rounds=rounds, warnings=warnings)
        reason = str(persona.absence_reason or "").strip()
        basis = str(persona.window_basis or "").strip()
        windows[aid] = ActivityWindow(
            agent_id=aid,
            active_from_round=from_r,
            active_until_round=until_r,
            absence_reason=reason,
            window_basis=basis,
        )
        if reason:
            ever_inactive = any(
                not is_active(windows[aid], r) for r in range(1, rounds + 1)
            )
            if not ever_inactive:
                warnings.append(
                    f"activity window for {aid}: absence_reason set but actor is active every round",
                )
    for r in range(1, rounds + 1):
        if not any(is_active(w, r) for w in windows.values()):
            raise ValueError(f"round {r} has no active agents")
    return windows, warnings


def windowing_active(windows: dict[str, ActivityWindow], total_rounds: int) -> bool:
    rounds = max(1, int(total_rounds))
    for w in windows.values():
        for r in range(1, rounds + 1):
            if not is_active(w, r):
                return True
    return False


def is_active(window: ActivityWindow, round_number: int) -> bool:
    return window.active_from_round <= round_number <= window.active_until_round


def active_agent_ids_for_round(
    windows: dict[str, ActivityWindow],
    ordered_agent_ids: list[str],
    round_number: int,
) -> list[str]:
    return [aid for aid in ordered_agent_ids if aid in windows and is_active(windows[aid], round_number)]


def join_round(window: ActivityWindow) -> int | None:
    if window.active_from_round > 1:
        return window.active_from_round
    return None


def render_handover_note(
    template: str,
    *,
    name: str,
    role: str,
    join_round: int,
    total_rounds: int,
    join_policy_event: str,
) -> str:
    return template.format(
        name=name,
        role=role,
        join_round=join_round,
        total_rounds=total_rounds,
        join_policy_event=join_policy_event,
    )


def absence_notice_for_round(
    windows: dict[str, ActivityWindow],
    agents_by_id: dict[str, tuple[str, str]],
    ordered_agent_ids: list[str],
    round_number: int,
    scope: str,
) -> str | None:
    sc = (scope or "all_inactive").strip().lower()
    if sc == "none":
        return None
    entries: list[str] = []
    for aid in ordered_agent_ids:
        w = windows.get(aid)
        if w is None or is_active(w, round_number):
            continue
        if sc == "departed_only" and w.active_until_round >= round_number:
            continue
        name = agents_by_id.get(aid, (aid, ""))[0]
        if w.absence_reason:
            entries.append(f"{name} ({w.absence_reason})")
        else:
            entries.append(name)
    if not entries:
        return None
    joined = ", ".join(entries)
    return f"Not present this round: {joined}."


def active_agents_per_round_rows(
    windows: dict[str, ActivityWindow],
    ordered_agent_ids: list[str],
    total_rounds: int,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for r in range(1, max(1, int(total_rounds)) + 1):
        active_ids = active_agent_ids_for_round(windows, ordered_agent_ids, r)
        inactive_ids = [aid for aid in ordered_agent_ids if aid not in active_ids]
        joined = [
            aid
            for aid in active_ids
            if windows[aid].active_from_round == r
        ]
        left: list[str] = []
        if r > 1:
            prev_active = set(active_agent_ids_for_round(windows, ordered_agent_ids, r - 1))
            curr_active = set(active_ids)
            left = [aid for aid in prev_active if aid not in curr_active]
        rows.append(
            {
                "round_number": r,
                "active_count": len(active_ids),
                "active_agent_ids": list(active_ids),
                "joined_agent_ids": joined,
                "left_agent_ids": left,
                "inactive_agent_ids": inactive_ids,
            }
        )
    return rows


def roster_windows_config_snapshot(
    *,
    agents: list[Any],
    windows: dict[str, ActivityWindow],
    roster_cfg: RosterWindowsConfig | None,
    handover_notes: dict[str, str],
    total_rounds: int,
) -> dict[str, Any]:
    scope = "all_inactive"
    template: str | None = None
    if roster_cfg is not None:
        scope = roster_cfg.absence_notice_scope or "all_inactive"
        template = roster_cfg.handover_template
    ordered_ids = [a.agent_id for a in agents]
    window_rows = [
        {
            "agent_id": aid,
            "name": next((a.name for a in agents if a.agent_id == aid), aid),
            "active_from_round": windows[aid].active_from_round,
            "active_until_round": windows[aid].active_until_round,
            "absence_reason": windows[aid].absence_reason,
            "window_basis": windows[aid].window_basis,
        }
        for aid in ordered_ids
        if aid in windows
    ]
    per_round = [
        {
            "round_number": row["round_number"],
            "active_count": row["active_count"],
            "active_agent_ids": row["active_agent_ids"],
        }
        for row in active_agents_per_round_rows(windows, ordered_ids, total_rounds)
    ]
    return {
        "schema_version": "v1",
        "windows": window_rows,
        "absence_notice_scope": scope,
        "absence_notice_format": "Not present this round: {entries}.",
        "handover_template": template,
        "handover_notes": dict(handover_notes),
        "active_agents_per_round": per_round,
    }


def filter_turns_min_round(turns: list[dict[str, Any]], min_round: int) -> list[dict[str, Any]]:
    return [t for t in turns if int(t.get("round_number") or 0) >= min_round]


def agents_active_both_rounds(
    agents: list[Any],
    windows: dict[str, ActivityWindow],
    round_number: int,
) -> list[Any]:
    if round_number <= 1:
        return []
    prev_r = round_number - 1
    return [
        a
        for a in agents
        if is_active(windows[a.agent_id], prev_r) and is_active(windows[a.agent_id], round_number)
    ]
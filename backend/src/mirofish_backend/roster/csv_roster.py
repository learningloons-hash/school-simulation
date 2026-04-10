from __future__ import annotations

import csv
import io
import json
from dataclasses import dataclass
from typing import Any

from mirofish_backend.scenarios.registry import PersonaTemplate, ScenarioConfig


@dataclass(frozen=True)
class ParsedRosterRow:
    """One CSV row; 1-based slot index. Empty CSV cells become None (inherit from scenario persona).

    Iteration 14: optional ``identity_json``, ``attitudes_json``, ``personal_history_json``
    columns accept JSON-object cells and are shallowly merged over the scenario persona's
    corresponding section (same merge semantics as population CSV v2).
    """

    slot: int
    persona_id: str | None = None
    role: str | None = None
    name: str | None = None
    role_level: int | None = None
    style_cues: str | None = None
    beliefs: dict[str, Any] | None = None
    groups: tuple[str, ...] | None = None
    identity: dict[str, Any] | None = None
    attitudes: dict[str, Any] | None = None
    personal_history: dict[str, Any] | None = None
    # Iteration 22: overrides sampling_strategy tier assignment (1–3).
    fidelity_tier: int | None = None
    # Iteration 26: optional opaque posture label (posture_maxvar sampling).
    implementation_posture: str | None = None


@dataclass(frozen=True)
class RosterParseResult:
    by_slot: dict[int, ParsedRosterRow]
    unknown_group_ids: tuple[str, ...]


def _cell(d: dict[str, str], key: str) -> str | None:
    v = d.get(key)
    if v is None:
        return None
    s = str(v).strip()
    return s if s else None


def _parse_json_object_cell(raw: str | None, *, line_no: int, column: str) -> dict[str, Any] | None:
    if raw is None or not str(raw).strip():
        return None
    try:
        j = json.loads(str(raw).strip())
    except json.JSONDecodeError as e:
        raise ValueError(f"roster_csv: line {line_no}: invalid JSON in {column}") from e
    if not isinstance(j, dict):
        raise ValueError(f"roster_csv: line {line_no}: {column} must be a JSON object")
    return dict(j)


def parse_roster_csv(text: str, *, agent_limit: int, scenario: ScenarioConfig) -> RosterParseResult:
    """
    Parse roster CSV. Header required. Slot column is **1-based** in [1, agent_limit].
    Returns map slot -> row (last row wins if duplicate slot).
    Raises ValueError on parse/validation errors.
    """
    if not text.strip():
        return RosterParseResult(by_slot={}, unknown_group_ids=())
    f = io.StringIO(text.strip())
    reader = csv.DictReader(f)
    if not reader.fieldnames:
        raise ValueError("roster_csv: missing header row")
    fields = {h.strip().lower(): h for h in reader.fieldnames if h}
    if "slot" not in fields:
        raise ValueError("roster_csv: required column 'slot' missing")

    known_groups = {g.group_id for g in scenario.groups}
    unknown: set[str] = set()
    by_slot: dict[int, ParsedRosterRow] = {}
    for i, row in enumerate(reader, start=2):
        if not row or all(not (v or "").strip() for v in row.values()):
            continue
        slot_raw = _cell({k.lower(): v for k, v in row.items()}, "slot")
        if not slot_raw:
            raise ValueError(f"roster_csv: line {i}: empty slot")
        if slot_raw.lstrip().startswith("#"):
            continue
        try:
            slot = int(slot_raw)
        except ValueError as e:
            raise ValueError(f"roster_csv: line {i}: invalid slot {slot_raw!r}") from e
        if slot < 1 or slot > agent_limit:
            raise ValueError(f"roster_csv: line {i}: slot {slot} out of range 1..{agent_limit}")

        rd = {k.lower().strip(): (v or "").strip() for k, v in row.items()}

        persona_id = _cell(rd, "persona_id")
        role = _cell(rd, "role")
        name = _cell(rd, "name")
        style_cues = _cell(rd, "style_cues")
        rl = _cell(rd, "role_level")
        role_level = int(rl) if rl is not None else None

        beliefs: dict[str, Any] | None = None
        bj = _cell(rd, "beliefs_json")
        if bj is not None:
            try:
                parsed = json.loads(bj)
            except json.JSONDecodeError as e:
                raise ValueError(f"roster_csv: line {i}: invalid beliefs_json") from e
            if not isinstance(parsed, dict):
                raise ValueError(f"roster_csv: line {i}: beliefs_json must be a JSON object")
            beliefs = dict(parsed)

        groups: tuple[str, ...] | None = None
        gs = _cell(rd, "groups")
        if gs is not None:
            parts = tuple(p.strip() for p in gs.split("|") if p.strip())
            groups = parts
            for g in parts:
                if g not in known_groups:
                    unknown.add(g)

        identity = _parse_json_object_cell(_cell(rd, "identity_json"), line_no=i, column="identity_json")
        attitudes = _parse_json_object_cell(_cell(rd, "attitudes_json"), line_no=i, column="attitudes_json")
        personal_history = _parse_json_object_cell(
            _cell(rd, "personal_history_json"), line_no=i, column="personal_history_json"
        )

        impl_post = _cell(rd, "implementation_posture")

        ft_raw = _cell(rd, "fidelity_tier")
        fidelity_tier: int | None = None
        if ft_raw is not None:
            try:
                fidelity_tier = int(ft_raw)
            except ValueError as e:
                raise ValueError(f"roster_csv: line {i}: invalid fidelity_tier {ft_raw!r}") from e
            if fidelity_tier not in (1, 2, 3):
                raise ValueError(f"roster_csv: line {i}: fidelity_tier must be 1, 2, or 3")

        by_slot[slot] = ParsedRosterRow(
            slot=slot,
            persona_id=persona_id,
            role=role,
            name=name,
            role_level=role_level,
            style_cues=style_cues,
            beliefs=beliefs,
            groups=groups,
            identity=identity,
            attitudes=attitudes,
            personal_history=personal_history,
            fidelity_tier=fidelity_tier,
            implementation_posture=impl_post,
        )

    return RosterParseResult(by_slot=by_slot, unknown_group_ids=tuple(sorted(unknown)))


def merge_persona_for_slot(base: PersonaTemplate, row: ParsedRosterRow | None) -> PersonaTemplate:
    if row is None:
        return base
    beliefs = dict(base.beliefs)
    if row.beliefs is not None:
        beliefs = {**beliefs, **row.beliefs}
    groups = base.groups
    if row.groups is not None:
        groups = row.groups
    identity = dict(base.identity)
    if row.identity is not None:
        identity.update(row.identity)
    attitudes = dict(base.attitudes)
    if row.attitudes is not None:
        attitudes.update(row.attitudes)
    personal_history = dict(base.personal_history)
    if row.personal_history is not None:
        personal_history.update(row.personal_history)
    impl_post = base.implementation_posture
    if row.implementation_posture is not None:
        s = str(row.implementation_posture).strip()
        if s:
            impl_post = s
    return PersonaTemplate(
        persona_id=row.persona_id or base.persona_id,
        role=row.role or base.role,
        name=row.name or base.name,
        role_level=row.role_level if row.role_level is not None else base.role_level,
        style_cues=row.style_cues or base.style_cues,
        beliefs=beliefs,
        psychological_profile=dict(base.psychological_profile),
        implementation_profile=dict(base.implementation_profile),
        identity=identity,
        attitudes=attitudes,
        personal_history=personal_history,
        groups=groups,
        initial_state=dict(base.initial_state),
        implementation_posture=impl_post,
    )


def personas_for_run(
    scenario: ScenarioConfig,
    agent_limit: int,
    roster_by_slot: dict[int, ParsedRosterRow] | None,
) -> list[PersonaTemplate]:
    out: list[PersonaTemplate] = []
    for idx in range(agent_limit):
        base = scenario.personas[idx] if idx < len(scenario.personas) else scenario.personas[-1]
        row = roster_by_slot.get(idx + 1) if roster_by_slot else None
        out.append(merge_persona_for_slot(base, row))
    return out

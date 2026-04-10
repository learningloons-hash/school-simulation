"""
Iteration 11–13 — single population-table contract (ADR-001).

CSV rows form a **pool**; we draw ``agent_limit`` rows without replacement using
``random_seed`` and ``population_sample_mode`` (weighted | stratified).

**Precedence** (when multiple sources are used):
1. Scenario YAML personas are the template catalog (``persona_id`` must match).
2. Population draw selects rows and sets persona + demographic overrides per slot.
3. Optional ``roster_csv`` merges **on top** per 1-based slot (roster wins on conflicts).
"""

from __future__ import annotations

import csv
import io
import json
import random
from collections import defaultdict
from dataclasses import dataclass
from typing import Any, Literal

from mirofish_backend.roster.csv_roster import merge_persona_for_slot
from mirofish_backend.scenarios.registry import PersonaTemplate, ScenarioConfig

POPULATION_SCHEMA_VERSION = "2"

PopulationSampleMode = Literal["weighted", "stratified"]


@dataclass(frozen=True)
class PopulationRow:
    """One data row from the population CSV.

    ``csv_row_index`` — 0-based index among **parsed** pool rows (stable draw id).
    ``source_file_line`` — 1-based physical line number in the CSV file (header = line 1).
    """

    csv_row_index: int
    source_file_line: int
    persona_id: str
    sampling_weight: float
    stratum: str
    age: int | None
    sex: str | None
    ethnicity: str | None
    ses: str | None
    name: str | None
    groups: tuple[str, ...] | None
    # Iteration 13: optional JSON object cells (merge over scenario persona sections).
    identity: dict[str, Any] | None
    attitudes: dict[str, Any] | None
    personal_history: dict[str, Any] | None
    # Iteration 26: optional posture label merged onto persona (posture_maxvar).
    implementation_posture: str | None = None


@dataclass(frozen=True)
class PopulationParseResult:
    rows: tuple[PopulationRow, ...]
    unknown_group_ids: tuple[str, ...]


@dataclass(frozen=True)
class PopulationDrawTraceEntry:
    slot_index: int
    source_file_line: int
    csv_row_index: int
    persona_id: str
    stratum: str
    sampling_weight: float


def _cell(rd: dict[str, str], key: str) -> str | None:
    v = rd.get(key)
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
        raise ValueError(f"population_csv: line {line_no}: invalid JSON in {column}") from e
    if not isinstance(j, dict):
        raise ValueError(f"population_csv: line {line_no}: {column} must be a JSON object")
    return dict(j)


def parse_population_csv(text: str, *, scenario: ScenarioConfig) -> PopulationParseResult:
    """
    Parse population pool CSV. Header required.

    Columns:
    - ``persona_id`` (required) — must match a ``persona_id`` on the scenario.
    - ``sampling_weight`` (optional, default 1.0) — must be > 0 if present.
    - ``stratum`` (optional) — for ``stratified`` mode; empty string if omitted.
    - ``age``, ``sex``, ``ethnicity``, ``ses`` (optional) — override synthetic demographics.
    - ``name`` (optional) — display name override.
    - ``groups`` (optional) — pipe ``|`` separated group ids (must exist on scenario).
    - ``identity_json``, ``attitudes_json``, ``personal_history_json`` (optional, schema v2) —
      JSON objects merged into agent context sections (Iteration 13).
    - ``implementation_posture`` (optional, Iteration 26) — opaque label merged onto drawn persona.
    """
    if not text.strip():
        return PopulationParseResult(rows=(), unknown_group_ids=())
    f = io.StringIO(text.strip())
    reader = csv.DictReader(f)
    if not reader.fieldnames:
        raise ValueError("population_csv: missing header row")
    fields = {h.strip().lower(): h for h in reader.fieldnames if h}
    if "persona_id" not in fields:
        raise ValueError("population_csv: required column 'persona_id' missing")

    known_personas = {p.persona_id for p in scenario.personas}
    known_groups = {g.group_id for g in scenario.groups}
    unknown_groups: set[str] = set()
    rows: list[PopulationRow] = []

    for line_no, row in enumerate(reader, start=2):
        if not row or all(not (v or "").strip() for v in row.values()):
            continue
        rd = {k.lower().strip(): (v or "").strip() for k, v in row.items()}
        pid = _cell(rd, "persona_id")
        if not pid:
            continue
        if pid.startswith("#"):
            continue
        if pid not in known_personas:
            raise ValueError(f"population_csv: line {line_no}: unknown persona_id {pid!r}")

        sw = _cell(rd, "sampling_weight")
        if sw is None:
            weight = 1.0
        else:
            try:
                weight = float(sw)
            except ValueError as e:
                raise ValueError(f"population_csv: line {line_no}: invalid sampling_weight") from e
            if weight <= 0:
                raise ValueError(f"population_csv: line {line_no}: sampling_weight must be > 0")

        stratum = _cell(rd, "stratum") or ""

        age: int | None = None
        ag = _cell(rd, "age")
        if ag is not None:
            try:
                age = int(ag)
            except ValueError as e:
                raise ValueError(f"population_csv: line {line_no}: invalid age") from e

        groups: tuple[str, ...] | None = None
        gs = _cell(rd, "groups")
        if gs is not None:
            parts = tuple(p.strip() for p in gs.split("|") if p.strip())
            groups = parts
            for g in parts:
                if g not in known_groups:
                    unknown_groups.add(g)

        id_json = _parse_json_object_cell(_cell(rd, "identity_json"), line_no=line_no, column="identity_json")
        att_json = _parse_json_object_cell(_cell(rd, "attitudes_json"), line_no=line_no, column="attitudes_json")
        hist_json = _parse_json_object_cell(
            _cell(rd, "personal_history_json"), line_no=line_no, column="personal_history_json"
        )
        impl_post = _cell(rd, "implementation_posture")

        csv_row_index = len(rows)
        rows.append(
            PopulationRow(
                csv_row_index=csv_row_index,
                source_file_line=line_no,
                persona_id=pid,
                sampling_weight=weight,
                stratum=stratum,
                age=age,
                sex=_cell(rd, "sex"),
                ethnicity=_cell(rd, "ethnicity"),
                ses=_cell(rd, "ses"),
                name=_cell(rd, "name"),
                groups=groups,
                identity=id_json,
                attitudes=att_json,
                personal_history=hist_json,
                implementation_posture=impl_post,
            )
        )

    return PopulationParseResult(rows=tuple(rows), unknown_group_ids=tuple(sorted(unknown_groups)))


def _persona_template_for_id(scenario: ScenarioConfig, persona_id: str) -> PersonaTemplate:
    for p in scenario.personas:
        if p.persona_id == persona_id:
            return p
    raise ValueError(f"persona_id {persona_id!r} not found in scenario")


def _weighted_sample_without_replacement(
    pool: list[tuple[int, float]],
    k: int,
    rng: random.Random,
) -> list[int]:
    """pool entries are (row_index, weight). Return k distinct row indices."""
    if k > len(pool):
        raise ValueError(f"population draw: need at least {k} pool rows, got {len(pool)}")
    work = list(pool)
    out: list[int] = []
    for _ in range(k):
        total = sum(w for _, w in work)
        if total <= 0:
            raise ValueError("population draw: non-positive total weight")
        r = rng.random() * total
        acc = 0.0
        chosen_j = 0
        for j, (_, w) in enumerate(work):
            acc += w
            if r < acc or j == len(work) - 1:
                chosen_j = j
                break
        idx, _w = work.pop(chosen_j)
        out.append(idx)
    return out


def _quota_per_stratum(stratum_sizes: dict[str, int], k: int) -> dict[str, int]:
    """Largest-remainder allocation so quotas sum to k."""
    if not stratum_sizes:
        return {}
    total_rows = sum(stratum_sizes.values())
    if total_rows == 0:
        return {}
    quotas: dict[str, int] = {}
    remainders: list[tuple[float, str]] = []
    assigned = 0
    for s, sz in sorted(stratum_sizes.items()):
        raw = k * sz / total_rows
        q = int(raw)
        quotas[s] = q
        assigned += q
        remainders.append((raw - q, s))
    remainders.sort(key=lambda x: -x[0])
    i = 0
    while assigned < k and remainders:
        _, s = remainders[i % len(remainders)]
        quotas[s] = quotas.get(s, 0) + 1
        assigned += 1
        i += 1
    return quotas


def select_population_draw(
    rows: tuple[PopulationRow, ...],
    *,
    agent_limit: int,
    mode: PopulationSampleMode,
    random_seed: int,
) -> tuple[list[int], list[PopulationDrawTraceEntry]]:
    """
    Return ordered row indices (length ``agent_limit``) and trace entries for config_snapshot.

    Uses ``random.Random(random_seed & 0xFFFFFFFF)`` isolated from other RNG use.
    """
    n = len(rows)
    if n == 0:
        raise ValueError("population_csv: pool is empty")
    if agent_limit > n:
        raise ValueError(f"population_csv: pool has {n} rows but agent_limit is {agent_limit}")
    rng = random.Random(random_seed & 0xFFFFFFFF)

    if mode == "weighted":
        # O(k * n) per draw step; fine for pools up to low thousands — revisit for 10k+ (e.g. alias / heap).
        pool = [(r.csv_row_index, r.sampling_weight) for r in rows]
        idxs = _weighted_sample_without_replacement(pool, agent_limit, rng)
    else:
        by_stratum: dict[str, list[tuple[int, float]]] = defaultdict(list)
        for r in rows:
            by_stratum[r.stratum].append((r.csv_row_index, r.sampling_weight))
        sizes = {s: len(lst) for s, lst in by_stratum.items()}
        quotas = _quota_per_stratum(sizes, agent_limit)
        idxs = []
        for s in sorted(by_stratum.keys()):
            q = quotas.get(s, 0)
            if q == 0:
                continue
            sub = by_stratum[s]
            if q > len(sub):
                raise ValueError(
                    f"population_csv stratified: stratum {s!r} needs {q} draws but only has {len(sub)} rows"
                )
            picked = _weighted_sample_without_replacement(sub, q, rng)
            idxs.extend(picked)
        if len(idxs) != agent_limit:
            raise ValueError(
                f"population_csv stratified: internal quota error (got {len(idxs)} picks, need {agent_limit})"
            )

    trace: list[PopulationDrawTraceEntry] = []
    for slot, row_idx in enumerate(idxs):
        r = next(x for x in rows if x.csv_row_index == row_idx)
        trace.append(
            PopulationDrawTraceEntry(
                slot_index=slot,
                source_file_line=r.source_file_line,
                csv_row_index=r.csv_row_index,
                persona_id=r.persona_id,
                stratum=r.stratum,
                sampling_weight=r.sampling_weight,
            )
        )
    return idxs, trace


def _row_to_dummy_roster_row(r: PopulationRow) -> Any:
    """Adapt PopulationRow fields for merge_persona_for_slot."""
    from mirofish_backend.roster.csv_roster import ParsedRosterRow

    return ParsedRosterRow(
        slot=0,
        persona_id=r.persona_id,
        role=None,
        name=r.name,
        role_level=None,
        style_cues=None,
        beliefs=None,
        groups=r.groups,
        implementation_posture=r.implementation_posture,
    )


def build_personas_and_slot_overrides(
    scenario: ScenarioConfig,
    rows: tuple[PopulationRow, ...],
    ordered_row_indices: list[int],
) -> tuple[list[PersonaTemplate], list[dict[str, Any]]]:
    """
    Build ``agent_limit`` personas and parallel **slot** override dicts per drawn row.

    Each dict may include **demographics** keys (``age``, ``sex``, ``ethnicity``, ``ses``) and/or
    **Iteration 13** keys ``identity``, ``attitudes``, ``personal_history`` (each a ``dict`` merged
    shallowly over the scenario persona YAML for that slot — CSV/population values **override**
    overlapping keys only).
    """
    personas: list[PersonaTemplate] = []
    slot_overrides: list[dict[str, Any]] = []
    for slot_idx, ri in enumerate(ordered_row_indices):
        row = next(r for r in rows if r.csv_row_index == ri)
        base = _persona_template_for_id(scenario, row.persona_id)
        merged = merge_persona_for_slot(base, _row_to_dummy_roster_row(row))
        personas.append(merged)
        dem: dict[str, Any] = {}
        if row.age is not None:
            dem["age"] = row.age
        if row.sex is not None:
            dem["sex"] = row.sex
        if row.ethnicity is not None:
            dem["ethnicity"] = row.ethnicity
        if row.ses is not None:
            dem["ses"] = row.ses
        if row.identity is not None:
            dem["identity"] = row.identity
        if row.attitudes is not None:
            dem["attitudes"] = row.attitudes
        if row.personal_history is not None:
            dem["personal_history"] = row.personal_history
        slot_overrides.append(dem)
    return personas, slot_overrides


# Backward-compatible name (pre–Iteration 13); prefer ``build_personas_and_slot_overrides``.
build_personas_and_demographic_overrides = build_personas_and_slot_overrides

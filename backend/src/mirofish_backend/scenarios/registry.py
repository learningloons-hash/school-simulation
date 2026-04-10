from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml


def _mapping_dict(raw: Any) -> dict[str, Any]:
    if not isinstance(raw, dict):
        return {}
    return dict(raw)


@dataclass(frozen=True)
class GroupDef:
    group_id: str
    name: str
    description: str = ""


@dataclass(frozen=True)
class PersonaTemplate:
    persona_id: str
    role: str  # free-form organisational role (scenario-defined)
    name: str
    role_level: int  # 1 = highest authority in scenario; higher integers = lower authority
    style_cues: str
    beliefs: dict[str, Any]
    # Optional richer YAML (Iteration 7); omitted in older scenarios → empty dicts.
    psychological_profile: dict[str, Any] = field(default_factory=dict)
    implementation_profile: dict[str, Any] = field(default_factory=dict)
    # Survey-like sections (Iteration 13); shallow string-key maps for prompts / export.
    identity: dict[str, Any] = field(default_factory=dict)
    attitudes: dict[str, Any] = field(default_factory=dict)
    personal_history: dict[str, Any] = field(default_factory=dict)
    # Cohort / faction ids declared on the scenario (Iteration 9).
    groups: tuple[str, ...] = ()
    # Initial simulation state (Iteration 21). Empty dict → orchestrator neutral defaults.
    initial_state: dict[str, Any] = field(default_factory=dict)
    # Opaque implementation archetype label for sampling (Iteration 26), e.g. active_sense_maker.
    implementation_posture: str = ""


@dataclass(frozen=True)
class ScenarioConfig:
    scenario_id: str
    name: str
    # Round number -> policy event text
    policy_events: dict[int, str]
    personas: list[PersonaTemplate]
    # Named groups for roster CSV and exports (Iteration 9).
    groups: tuple[GroupDef, ...] = ()
    # RAG scaffold: when True (and run resolves rag_effective), corpus paths are under scenarios/data/.
    rag_enabled: bool = False
    rag_corpus_paths: tuple[str, ...] = ()
    # Iteration 15: IAD overlay flag. "school_trinidad" activates Trinidad's authority-based channel defaults.
    interaction_overlay: str = "none"


_DATA_DIR = Path(__file__).resolve().parent / "data"

# Used only if no YAML files are present (e.g. broken install).
# School-specific demo scenario. Engine is domain-agnostic; create scenario YAML for other domains.
_SCENARIOS_FALLBACK: dict[str, ScenarioConfig] = {
    "psle_reform_mvp": ScenarioConfig(
        scenario_id="psle_reform_mvp",
        name="PSLE Reform (MVP)",
        policy_events={
            1: "MOE briefing: PSLE changes will focus on reduced over-emphasis on single examinations.",
        },
        rag_enabled=False,
        rag_corpus_paths=(),
        personas=[
            PersonaTemplate(
                persona_id="principal_001",
                role="principal",
                name="Principal",
                role_level=1,
                style_cues="Formal, strategic, concise.",
                beliefs={"trust_in_moe_policy": 0.55},
                groups=(),
                implementation_posture="active_sense_maker",
                initial_state={
                    "support_level": 0.62,
                    "resistance_level": 0.30,
                    "workload_stress": 0.40,
                    "belief_posture": "strategic_support",
                },
            ),
        ],
    ),
    # Same as scenarios/data/fsbb_comparator.yaml — embedded so installs without package-data still resolve the id.
    "fsbb_comparator": ScenarioConfig(
        scenario_id="fsbb_comparator",
        name="FSBB Comparator (MVP)",
        policy_events={
            1: "MOE circular: schools transition to Full Subject-Based Banding; S1 posting uses AL scores with subject-level G1/G2/G3 bands.",
            3: "Town hall: parents and teachers discuss mixed-form classes, communication load, and fairness of subject band movement.",
            5: "Review week: HODs report timetable constraints and whether early support reduces stigma around band labels.",
        },
        rag_enabled=True,
        rag_corpus_paths=("corpus/fsbb_comparator/brief.txt",),
        personas=[
            PersonaTemplate(
                persona_id="principal_001",
                role="principal",
                name="Principal",
                role_level=1,
                style_cues="Strategic, balances policy compliance with school reputation and community trust.",
                beliefs={
                    "trust_in_moe_policy": 0.58,
                    "risk_aversion": 0.5,
                    "priority": "coherent_posting_messaging",
                },
                groups=(),
                implementation_posture="active_sense_maker",
                initial_state={
                    "support_level": 0.62,
                    "resistance_level": 0.30,
                    "workload_stress": 0.40,
                    "belief_posture": "strategic_support",
                },
            ),
            PersonaTemplate(
                persona_id="middle_manager_001",
                role="middle_manager",
                name="HOD / Middle Manager",
                role_level=2,
                style_cues="Operational; focuses on timetabling, teacher capacity, and cross-level coordination.",
                beliefs={
                    "workload_sensitivity": 0.72,
                    "implementation_focus": "subject_level_bands",
                },
                groups=(),
                implementation_posture="compliant_implementer",
                initial_state={
                    "support_level": 0.55,
                    "resistance_level": 0.35,
                    "workload_stress": 0.52,
                    "belief_posture": "operational_balancing",
                },
            ),
            PersonaTemplate(
                persona_id="teacher_001",
                role="teacher",
                name="Teacher",
                role_level=3,
                style_cues="Classroom-grounded; discusses student affect, differentiation, and day-to-day band transitions.",
                beliefs={
                    "student_wellbeing_priority": 0.75,
                    "stigma_awareness": 0.65,
                },
                groups=(),
                implementation_posture="selective_adopter",
                initial_state={
                    "support_level": 0.50,
                    "resistance_level": 0.38,
                    "workload_stress": 0.58,
                    "belief_posture": "classroom_caution",
                },
            ),
        ],
    ),
}

_MERGED: dict[str, ScenarioConfig] | None = None


def _groups_tuple_from_persona(raw: Any) -> tuple[str, ...]:
    if raw is None:
        return ()
    if isinstance(raw, list):
        return tuple(str(x) for x in raw)
    raise ValueError("persona.groups must be a list of group_id strings when present")


def _persona_from_mapping(p: dict[str, Any]) -> PersonaTemplate:
    groups_raw = p.get("groups")
    groups = _groups_tuple_from_persona(groups_raw) if groups_raw is not None else ()
    return PersonaTemplate(
        persona_id=str(p["persona_id"]),
        role=str(p["role"]),
        name=str(p["name"]),
        role_level=int(p["role_level"]),
        style_cues=str(p["style_cues"]),
        beliefs=dict(p.get("beliefs") or {}),
        psychological_profile=_mapping_dict(p.get("psychological_profile")),
        implementation_profile=_mapping_dict(p.get("implementation_profile")),
        identity=_mapping_dict(p.get("identity")),
        attitudes=_mapping_dict(p.get("attitudes")),
        personal_history=_mapping_dict(p.get("personal_history")),
        groups=groups,
        initial_state=_mapping_dict(p.get("initial_state")),
        implementation_posture=str(p.get("implementation_posture") or "").strip(),
    )


def _groups_from_scenario(raw: Any) -> tuple[GroupDef, ...]:
    if raw is None:
        return ()
    if not isinstance(raw, list):
        raise ValueError("scenario.groups must be a list of objects with group_id and name")
    out: list[GroupDef] = []
    for item in raw:
        if not isinstance(item, dict):
            raise ValueError("each scenario.groups entry must be a mapping")
        out.append(
            GroupDef(
                group_id=str(item["group_id"]),
                name=str(item["name"]),
                description=str(item.get("description") or ""),
            )
        )
    return tuple(out)


def _scenario_from_mapping(raw: dict[str, Any]) -> ScenarioConfig:
    pe_raw = raw.get("policy_events") or {}
    policy_events: dict[int, str] = {int(k): str(v) for k, v in pe_raw.items()}
    personas_raw = raw.get("personas") or []
    personas = [_persona_from_mapping(dict(x)) for x in personas_raw]
    rag_enabled = bool(raw.get("rag_enabled", False))
    rc = raw.get("rag_corpus_paths")
    if isinstance(rc, list):
        rag_corpus_paths = tuple(str(x) for x in rc)
    else:
        rag_corpus_paths = ()
    groups = _groups_from_scenario(raw.get("groups"))
    interaction_overlay = str(raw.get("interaction_overlay") or "none").strip().lower()
    return ScenarioConfig(
        scenario_id=str(raw["scenario_id"]),
        name=str(raw["name"]),
        policy_events=policy_events,
        personas=personas,
        groups=groups,
        rag_enabled=rag_enabled,
        rag_corpus_paths=rag_corpus_paths,
        interaction_overlay=interaction_overlay,
    )


def _load_yaml_dir() -> dict[str, ScenarioConfig]:
    if not _DATA_DIR.is_dir():
        return {}
    out: dict[str, ScenarioConfig] = {}
    for path in sorted(_DATA_DIR.glob("*.yaml")):
        raw = yaml.safe_load(path.read_text(encoding="utf-8"))
        if not isinstance(raw, dict):
            continue
        cfg = _scenario_from_mapping(raw)
        out[cfg.scenario_id] = cfg
    return out


def _merged_registry() -> dict[str, ScenarioConfig]:
    global _MERGED
    if _MERGED is None:
        disk = _load_yaml_dir()
        _MERGED = {**_SCENARIOS_FALLBACK, **disk}
    return _MERGED


def get_scenario(scenario_id: str) -> ScenarioConfig:
    reg = _merged_registry()
    if scenario_id not in reg:
        raise KeyError(f"Unknown scenario_id: {scenario_id}")
    return reg[scenario_id]


def scenario_from_mapping(raw: dict[str, Any]) -> ScenarioConfig:
    """Public parser for YAML/JSON-shaped scenario documents (user scenarios, imports)."""
    return _scenario_from_mapping(raw)


def list_builtin_scenario_catalog() -> list[dict[str, Any]]:
    """Minimal metadata for GET /scenarios (builtin branch)."""
    out: list[dict[str, Any]] = []
    for sid, cfg in sorted(_merged_registry().items()):
        out.append(
            {
                "id": sid,
                "name": cfg.name,
                "rag_enabled": cfg.rag_enabled,
                "source": "builtin",
            }
        )
    return out


def is_builtin_scenario_id(scenario_id: str) -> bool:
    return scenario_id in _merged_registry()

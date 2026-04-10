import asyncio
import json
import logging
import re
import time
from typing import Any, Literal, cast

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import JSONResponse, PlainTextResponse, Response
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from mirofish_backend.config import Settings, get_settings
from mirofish_backend.population.csv_population import (
    POPULATION_SCHEMA_VERSION,
    build_personas_and_slot_overrides,
    parse_population_csv,
    select_population_draw,
)
from mirofish_backend.roster.csv_roster import (
    merge_persona_for_slot,
    parse_roster_csv,
    personas_for_run as build_personas_from_roster,
)
from mirofish_backend.scenarios.loader import load_scenario_for_run
from mirofish_backend.db.repo import (
    create_simulation_run,
    get_simulation_export_bundle,
    get_simulation_run_status_only,
    get_simulation_status_and_config_snapshot,
    get_simulation_status_with_transcript,
    get_simulation_total_rounds,
    get_user_scenario_row,
    insert_validity_note,
    list_simulation_runs,
    set_simulation_status,
    simulation_exists,
)
from mirofish_backend.export_bundle import (
    EXPORT_VERSION,
    build_export_zip,
    compute_cohort_summary,
)
from mirofish_backend.llm.router import llm_complete
from mirofish_backend.simulation.interaction_policy import VisibilityPolicy
from mirofish_backend.simulation.network import (
    degree_centrality,
    parse_network_csv,
    undirected_neighbor_map,
)
from mirofish_backend.simulation.orchestrator import run_simulation_task
from mirofish_backend.simulation.remainder import build_synthetic_remainder_personas
from mirofish_backend.simulation.sampling_report import build_sampling_report_json
from mirofish_backend.simulation.sampling_strategy import (
    SAMPLING_STRATEGY_VALUES,
    build_sampling_audit_extended,
    compute_fidelity_tiers,
)

logger = logging.getLogger("mirofish_backend.api.simulations")

VISIBILITY_POLICY_VALUES: frozenset[str] = frozenset(v.value for v in VisibilityPolicy)

router = APIRouter()

# POST /simulations/{id}/analyze — two-stage shrink for LLM context. Keep these constants together.
# Stage 1: `_clip_transcript_for_analysis` (max turns + per-turn raw_response cap).
# Stage 2: if json.dumps(payload) still exceeds budget, reclips transcript (40+40) or shortens each response.
ANALYZE_LLM_JSON_CHAR_BUDGET = 180_000
ANALYZE_TRANSCRIPT_MAX_TURNS_FIRST_PASS = 100
ANALYZE_RAW_RESPONSE_MAX_CHARS_FIRST_PASS = 3000
ANALYZE_TRANSCRIPT_COUNT_FOR_SECOND_RECLIP = 80
ANALYZE_TRANSCRIPT_KEEP_HEAD_TAIL = 40
ANALYZE_RAW_RESPONSE_MAX_CHARS_SECOND_PASS = 1200

# Single source for run API validation and GET /capabilities (Iteration 16).
SIMULATION_MODE_VALUES: frozenset[str] = frozenset({"full_round_robin", "sample_k_per_round"})
POPULATION_SAMPLE_MODE_VALUES: frozenset[str] = frozenset({"weighted", "stratified"})
LLM_PROVIDER_VALUES: frozenset[str] = frozenset({"lmstudio", "anthropic", "hybrid"})


def speakers_per_round_for_config_snapshot(simulation_mode: str, speakers_per_round: int) -> int | None:
    """Persist null for full_round_robin so analysts are not misled by an unused K default."""
    m = (simulation_mode or "full_round_robin").strip().lower()
    return None if m == "full_round_robin" else speakers_per_round

ROSTER_CSV_TEMPLATE = (
    "slot,persona_id,role,name,role_level,style_cues,beliefs_json,groups,fidelity_tier,implementation_posture,"
    "identity_json,attitudes_json,personal_history_json\n"
    "1,,,,,,,,,,,,\n"
    "# fidelity_tier: optional 1|2|3 overrides sampling_strategy tier for that slot (Iter 22)\n"
    "# implementation_posture: optional opaque label for posture_maxvar sampling (Iter 26).\n"
    "#   Empty or whitespace-only cell does NOT clear YAML posture — only a non-empty cell overrides.\n"
    "# identity_json/attitudes_json/personal_history_json accept JSON objects; merged shallowly over scenario persona (Iter 14)\n"
)

POPULATION_CSV_TEMPLATE = (
    "# population_schema_version 2 (optional JSON columns backward-compatible with v1-only rows).\n"
    "# Merge: identity_json / attitudes_json / personal_history_json are JSON *objects* shallow-merged\n"
    "# over scenario YAML for that persona; overlapping keys are replaced by the CSV value (other YAML keys kept).\n"
    "persona_id,sampling_weight,stratum,age,sex,ethnicity,ses,name,groups,implementation_posture,"
    "identity_json,attitudes_json,personal_history_json\n"
    "principal_001,1.0,senior_leadership,52,female,Chinese,high,,,,,,\n"
    "teacher_001,1.5,instructional,34,male,Indian,middle,,,,,,\n"
    "teacher_001,1.0,instructional,,female,Malay,,Teacher B,,,,,\n"
)


class GaussianDistParams(BaseModel):
    """Normal draw for synthetic remainder initial numeric state (clamped to [0,1] after draw)."""

    model_config = ConfigDict(extra="forbid")
    mean: float = Field(default=0.52, ge=-2.0, le=2.0)
    std: float = Field(default=0.1, ge=0.0, le=1.0)


class RemainderConfigParams(BaseModel):
    """Optional synthetic remainder cohort + Tier-3 heuristic tuning (Iteration 24)."""

    model_config = ConfigDict(extra="forbid")
    remainder_count: int = Field(default=0, ge=0, le=299)
    tier_3_dampening: float = Field(default=0.6, ge=0.0, le=2.0)
    tier_3_noise_std: float = Field(default=0.02, ge=0.0, le=0.5)
    initial_support_distribution: GaussianDistParams = Field(default_factory=GaussianDistParams)
    initial_resistance_distribution: GaussianDistParams = Field(
        default_factory=lambda: GaussianDistParams(mean=0.35, std=0.1)
    )
    initial_workload_stress_distribution: GaussianDistParams = Field(
        default_factory=lambda: GaussianDistParams(mean=0.6, std=0.08)
    )


@router.get("/simulations/roster-csv-template", response_class=PlainTextResponse)
async def get_roster_csv_template() -> PlainTextResponse:
    return PlainTextResponse(ROSTER_CSV_TEMPLATE, media_type="text/plain; charset=utf-8")


@router.get("/simulations/population-csv-template", response_class=PlainTextResponse)
async def get_population_csv_template() -> PlainTextResponse:
    return PlainTextResponse(POPULATION_CSV_TEMPLATE, media_type="text/plain; charset=utf-8")


async def run_simulation_task_guarded(
    *,
    sqlite_path: str,
    simulation_id: str,
    scenario_id: str,
    total_rounds: int,
    agent_limit: int,
    random_seed: int,
    prompt_version: str,
    model_used: str,
    lmstudio_model: str,
    lmstudio_base_url: str,
    llm_temperature: float,
    llm_max_tokens: int,
    working_memory_last_k: int,
    llm_provider: str,
    anthropic_api_key: str,
    anthropic_model: str,
    peer_context_max_chars: int,
    rag_effective: bool,
    embedding_model: str,
    rag_top_k: int,
    rag_chunk_size: int,
    rag_chunk_overlap: int,
    rag_max_inject_chars: int,
    personas_for_run: list | None = None,
    slot_overrides: list[dict[str, Any]] | None = None,
    scenario_config: Any | None = None,
    simulation_mode: str = "full_round_robin",
    speakers_per_round: int = 2,
    turn_order_policy: str = "round_robin",
    visibility_policy: str = "full",
    interaction_overlay: str = "none",
    llm_concurrency_cap: int = 4,
    fidelity_tiers: list[int] | None = None,
    tier_3_dampening: float = 0.6,
    tier_3_noise_std: float = 0.02,
    network_neighbors: dict[str, frozenset[str]] | None = None,
    visibility_effective: str | None = None,
    convergence_threshold: float | None = None,
    convergence_patience: int = 2,
) -> None:
    """Run simulation and mark run failed with reason on uncaught errors (used by API and tests)."""
    try:
        await run_simulation_task(
            sqlite_path=sqlite_path,
            simulation_id=simulation_id,
            scenario_id=scenario_id,
            total_rounds=total_rounds,
            agent_limit=agent_limit,
            random_seed=random_seed,
            prompt_version=prompt_version,
            model_used=model_used,
            lmstudio_model=lmstudio_model,
            lmstudio_base_url=lmstudio_base_url,
            llm_temperature=llm_temperature,
            llm_max_tokens=llm_max_tokens,
            working_memory_last_k=working_memory_last_k,
            llm_provider=llm_provider,
            anthropic_api_key=anthropic_api_key,
            anthropic_model=anthropic_model,
            peer_context_max_chars=peer_context_max_chars,
            rag_effective=rag_effective,
            embedding_model=embedding_model,
            rag_top_k=rag_top_k,
            rag_chunk_size=rag_chunk_size,
            rag_chunk_overlap=rag_chunk_overlap,
            rag_max_inject_chars=rag_max_inject_chars,
            personas_for_run=personas_for_run,
            slot_overrides=slot_overrides,
            scenario_config=scenario_config,
            simulation_mode=simulation_mode,
            speakers_per_round=speakers_per_round,
            turn_order_policy=turn_order_policy,
            visibility_policy=visibility_policy,
            interaction_overlay=interaction_overlay,
            llm_concurrency_cap=llm_concurrency_cap,
            fidelity_tiers=fidelity_tiers,
            tier_3_dampening=tier_3_dampening,
            tier_3_noise_std=tier_3_noise_std,
            network_neighbors=network_neighbors,
            visibility_effective=visibility_effective,
            convergence_threshold=convergence_threshold,
            convergence_patience=convergence_patience,
        )
    except Exception as e:
        logger.exception("Simulation task failed for %s", simulation_id)
        await set_simulation_status(
            sqlite_path,
            simulation_id=simulation_id,
            status="failed",
            current_round=0,
            failure_reason=f"{type(e).__name__}: {e}",
        )


class SimulationRunRequest(BaseModel):
    scenario_id: str = Field(default="psle_reform_mvp")
    total_rounds: int = Field(default=4, ge=1, le=25)
    agent_limit: int = Field(default=3, ge=1, le=300)
    roster_csv: str | None = Field(
        default=None,
        max_length=500_000,
        description="Optional CSV roster; 1-based slot column merges onto scenario personas.",
    )
    population_csv: str | None = Field(
        default=None,
        max_length=500_000,
        description="Optional population pool CSV (Iteration 11). Draws rows without replacement (core slots only "
        "when remainder_config.remainder_count > 0: agent_limit - remainder_count); see GET /simulations/population-csv-template.",
    )
    population_sample_mode: str = Field(
        default="weighted",
        description="weighted | stratified — used only when population_csv is non-empty.",
    )
    random_seed: int = Field(default=42)
    max_tokens: int | None = Field(default=None, ge=64, le=8192)
    llm_provider: str | None = Field(
        default=None,
        description="lmstudio | anthropic | hybrid; defaults from server settings",
    )
    rag_enabled: bool | None = Field(
        default=None,
        description="If set, forces RAG on (True) or off (False); omit to use server flag OR scenario rag_enabled",
    )
    simulation_mode: str = Field(
        default="full_round_robin",
        description="full_round_robin | sample_k_per_round (Iteration 10)",
    )
    speakers_per_round: int = Field(
        default=2,
        ge=1,
        le=300,
        description="Used when simulation_mode=sample_k_per_round; ignored for full_round_robin. "
        "config_snapshot stores null for speakers_per_round in full_round_robin.",
    )
    turn_order_policy: str = Field(
        default="round_robin",
        description="round_robin | hierarchical (Iteration 15). "
        "hierarchical sorts agents by role_level each round (principal first). "
        "school_trinidad overlay automatically upgrades to hierarchical.",
    )
    visibility_policy: str = Field(
        default="full",
        description="full | broadcast | group_bounded | round_participants_only | network_bounded (Iter 15 + ADR-002). "
        "network_bounded needs network_csv or falls back to broadcast with a warning.",
    )
    interaction_overlay: str = Field(
        default="none",
        description="none | school_trinidad (Iteration 15). "
        "school_trinidad activates Trinidad's school sociology channel defaults.",
    )
    llm_concurrency_cap: int | None = Field(
        default=None,
        ge=1,
        le=16,
        description="Max concurrent LLM calls per round (Iteration 19). "
        "Defaults to server LLM_CONCURRENCY_CAP (default 4). Use 1 for sequential execution.",
    )
    aggregation_threshold: int = Field(
        default=20,
        ge=1,
        le=300,
        description="Agent count at or above which cohort_summary is included in exports (Iteration 20). "
        "aggregation_mode in config_snapshot is true when agent_limit >= aggregation_threshold.",
    )
    sampling_strategy: str = Field(
        default="full_census",
        description="full_census | role_stratified | hybrid_core_remainder | posture_maxvar | network_centrality (Iteration 22–25).",
    )
    remainder_config: RemainderConfigParams | None = Field(
        default=None,
        description="Synthetic remainder agents (Tier 3) + Tier-3 heuristic tuning (Iteration 24).",
    )
    network_csv: str | None = Field(
        default=None,
        max_length=500_000,
        description="Optional influence network CSV: source_agent_id,target_agent_id,influence_weight (0–1). "
        "Agent ids use the format persona_id_NNN (e.g. principal_001_000); check sampling_audit.per_agent[].agent_id "
        "for exact run ids. Required for sampling_strategy=network_centrality.",
    )
    convergence_threshold: float | None = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="If set, stop when population mean abs attitude change (support/resistance/workload) stays "
        "below this for convergence_patience consecutive rounds (Iteration 28). Omit to run full total_rounds.",
    )
    convergence_patience: int = Field(
        default=2,
        ge=1,
        le=25,
        description="Consecutive sub-threshold rounds required; only used when convergence_threshold is set.",
    )

    @model_validator(mode="after")
    def _remainder_fits_agent_limit(self) -> "SimulationRunRequest":
        rc = self.remainder_config
        if rc is not None and rc.remainder_count > 0:
            if rc.remainder_count >= self.agent_limit:
                raise ValueError("remainder_config.remainder_count must be less than agent_limit")
        if self.sampling_strategy == "network_centrality":
            if not self.network_csv or not str(self.network_csv).strip():
                raise ValueError("network_centrality requires non-empty network_csv")
        return self

    @field_validator("llm_provider")
    @classmethod
    def _normalize_provider(cls, v: str | None) -> str | None:
        if v is None:
            return None
        s = v.strip().lower()
        if s not in LLM_PROVIDER_VALUES:
            raise ValueError("llm_provider must be 'lmstudio', 'anthropic', or 'hybrid'")
        return s

    @field_validator("simulation_mode")
    @classmethod
    def _normalize_simulation_mode(cls, v: str) -> str:
        s = (v or "full_round_robin").strip().lower().replace("-", "_")
        if s not in SIMULATION_MODE_VALUES:
            raise ValueError("simulation_mode must be 'full_round_robin' or 'sample_k_per_round'")
        return s

    @field_validator("population_sample_mode")
    @classmethod
    def _normalize_population_sample_mode(cls, v: str) -> str:
        s = (v or "weighted").strip().lower().replace("-", "_")
        if s not in POPULATION_SAMPLE_MODE_VALUES:
            raise ValueError("population_sample_mode must be 'weighted' or 'stratified'")
        return s

    @field_validator("sampling_strategy")
    @classmethod
    def _normalize_sampling_strategy(cls, v: str) -> str:
        s = (v or "full_census").strip().lower().replace("-", "_")
        if s not in SAMPLING_STRATEGY_VALUES:
            raise ValueError(
                "sampling_strategy must be one of: full_census, role_stratified, hybrid_core_remainder, "
                "posture_maxvar, network_centrality"
            )
        return s

    @field_validator("visibility_policy")
    @classmethod
    def _normalize_visibility_policy(cls, v: str) -> str:
        s = (v or "full").strip().lower()
        if s not in VISIBILITY_POLICY_VALUES:
            raise ValueError(
                f"visibility_policy must be one of: {', '.join(sorted(VISIBILITY_POLICY_VALUES))}"
            )
        return s


class SimulationRunResponse(BaseModel):
    """Returned when a run is queued; `warnings` surfaces analyst-visible issues without reading config_snapshot."""

    id: str
    warnings: list[str] = Field(default_factory=list)


class SimulationListItem(BaseModel):
    id: str
    name: str
    scenario_id: str
    status: str
    current_round: int
    total_rounds: int
    created_at: str | None = None
    completed_at: str | None = None
    experiment_id: str | None = None

    model_config = {"extra": "ignore"}


class SimulationStatusResponse(BaseModel):
    id: str
    status: str
    current_round: int
    total_rounds: int
    failure_reason: str | None = None
    converged_at_round: int | None = None
    config_snapshot: dict[str, Any] | None = None
    transcript: list[dict[str, Any]] = Field(default_factory=list)
    state_timeline: list[dict[str, Any]] = Field(default_factory=list)
    outcome_indicators: list[dict[str, Any]] = Field(default_factory=list)
    validity_notes: list[dict[str, Any]] = Field(default_factory=list)
    economics: dict[str, Any] | None = None


class ValidityNoteCreate(BaseModel):
    """Manual validity coding: face / construct / predictive. Omit round_number for a run-level note."""

    round_number: int | None = Field(default=None, ge=1, le=25)
    rater_id: str | None = Field(default=None, max_length=256)
    face_score: float | None = None
    face_rubric: str | None = Field(default=None, max_length=8000)
    construct_score: float | None = None
    construct_rubric: str | None = Field(default=None, max_length=8000)
    predictive_score: float | None = None
    predictive_rubric: str | None = Field(default=None, max_length=8000)
    notes: str | None = Field(default=None, max_length=16000)

    @model_validator(mode="after")
    def _at_least_one_field(self) -> "ValidityNoteCreate":
        text_any = any(
            (x or "").strip()
            for x in (self.face_rubric, self.construct_rubric, self.predictive_rubric, self.notes)
        )
        score_any = any(
            s is not None for s in (self.face_score, self.construct_score, self.predictive_score)
        )
        if not text_any and not score_any:
            raise ValueError("Provide at least one score, rubric text, or notes field")
        return self


@router.get("/simulations", response_model=list[SimulationListItem])
async def list_simulations(limit: int = Query(default=50, ge=1, le=200)) -> list[SimulationListItem]:
    settings = get_settings()
    rows = await list_simulation_runs(settings.sqlite_path, limit=limit)
    return [SimulationListItem(**r) for r in rows]


async def queue_simulation_run(
    settings: Settings,
    _req: SimulationRunRequest,
    *,
    experiment_id: str | None = None,
    experiment_step_index: int | None = None,
    experiment_run_label: str | None = None,
    run_display_name: str | None = None,
) -> SimulationRunResponse:
    prompt_version = settings.prompt_version
    name = run_display_name if run_display_name else _req.scenario_id
    llm_max_tokens = _req.max_tokens if _req.max_tokens is not None else settings.llm_max_tokens
    llm_provider = _req.llm_provider if _req.llm_provider is not None else settings.llm_provider
    llm_concurrency_cap = (
        _req.llm_concurrency_cap if _req.llm_concurrency_cap is not None else settings.llm_concurrency_cap
    )

    if llm_provider == "anthropic":
        model_used = settings.anthropic_model
    elif llm_provider == "hybrid":
        model_used = f"hybrid:{settings.lmstudio_model}|{settings.anthropic_model}"
    else:
        model_used = settings.lmstudio_model
    try:
        scenario_cfg, scenario_source = await load_scenario_for_run(settings.sqlite_path, _req.scenario_id)
    except KeyError:
        raise HTTPException(status_code=404, detail=f"Unknown scenario_id: {_req.scenario_id}") from None

    remainder_cfg = _req.remainder_config
    remainder_count = int(remainder_cfg.remainder_count) if remainder_cfg else 0
    core_limit = _req.agent_limit - remainder_count if remainder_count > 0 else _req.agent_limit
    tier_3_dampening = float(remainder_cfg.tier_3_dampening) if remainder_cfg else 0.6
    tier_3_noise_std = float(remainder_cfg.tier_3_noise_std) if remainder_cfg else 0.02

    roster_parse = None
    personas_override = None
    slot_overrides: list[dict[str, Any]] | None = None
    population_parse_result = None
    population_draw_trace = None

    if _req.population_csv and _req.population_csv.strip():
        try:
            population_parse_result = parse_population_csv(
                _req.population_csv.strip(),
                scenario=scenario_cfg,
            )
        except ValueError as e:
            raise HTTPException(status_code=422, detail=str(e)) from e
        rows = population_parse_result.rows
        if not rows:
            raise HTTPException(status_code=422, detail="population_csv: pool is empty")
        try:
            draw_idxs, population_draw_trace = select_population_draw(
                rows,
                agent_limit=core_limit,
                mode=cast(Literal["weighted", "stratified"], _req.population_sample_mode),
                random_seed=_req.random_seed,
            )
        except ValueError as e:
            raise HTTPException(status_code=422, detail=str(e)) from e
        personas_override, slot_overrides = build_personas_and_slot_overrides(
            scenario_cfg,
            rows,
            draw_idxs,
        )

    if _req.roster_csv and _req.roster_csv.strip():
        try:
            roster_parse = parse_roster_csv(
                _req.roster_csv.strip(),
                agent_limit=_req.agent_limit,
                scenario=scenario_cfg,
            )
        except ValueError as e:
            raise HTTPException(status_code=422, detail=str(e)) from e
        if personas_override is not None:
            personas_override = [
                merge_persona_for_slot(personas_override[i], roster_parse.by_slot.get(i + 1))
                for i in range(len(personas_override))
            ]
        else:
            personas_override = build_personas_from_roster(
                scenario_cfg,
                core_limit,
                roster_parse.by_slot,
            )

    base_rag = settings.rag_enabled or scenario_cfg.rag_enabled
    if _req.rag_enabled is True:
        rag_effective = True
    elif _req.rag_enabled is False:
        rag_effective = False
    else:
        rag_effective = base_rag
    embedding_model_used = settings.embedding_model.strip() or settings.lmstudio_model
    scenario_doc_version: str | None = None
    if scenario_source == "user":
        ur = await get_user_scenario_row(settings.sqlite_path, scenario_id=_req.scenario_id)
        if ur:
            scenario_doc_version = str(ur["scenario_doc_version"])

    run_warnings: list[str] = []
    if roster_parse and roster_parse.unknown_group_ids:
        u = ", ".join(sorted(roster_parse.unknown_group_ids))
        run_warnings.append(f"roster_csv references group_ids not defined on this scenario: {u}")
    if population_parse_result and population_parse_result.unknown_group_ids:
        u = ", ".join(sorted(population_parse_result.unknown_group_ids))
        run_warnings.append(f"population_csv references group_ids not defined on this scenario: {u}")

    personas_final: list = (
        list(personas_override)
        if personas_override is not None
        else build_personas_from_roster(
            scenario_cfg,
            core_limit,
            roster_parse.by_slot if roster_parse else None,
        )
    )
    if remainder_count > 0:
        assert remainder_cfg is not None
        synth = build_synthetic_remainder_personas(
            scenario_cfg,
            remainder_count,
            random_seed=_req.random_seed,
            support_mean=remainder_cfg.initial_support_distribution.mean,
            support_std=remainder_cfg.initial_support_distribution.std,
            resistance_mean=remainder_cfg.initial_resistance_distribution.mean,
            resistance_std=remainder_cfg.initial_resistance_distribution.std,
            workload_mean=remainder_cfg.initial_workload_stress_distribution.mean,
            workload_std=remainder_cfg.initial_workload_stress_distribution.std,
        )
        personas_final = list(personas_final) + synth
        if slot_overrides is not None:
            slot_overrides = list(slot_overrides) + [{}] * remainder_count

    personas_for_task: list | None
    if remainder_count > 0 or personas_override is not None:
        personas_for_task = personas_final
    else:
        personas_for_task = None
    slot_for_task = slot_overrides if (remainder_count > 0 or personas_override is not None) else None

    agent_ids_for_audit = [f"{personas_final[i].persona_id}_{i:03d}" for i in range(len(personas_final))]
    known_agent_ids = frozenset(agent_ids_for_audit)

    net_parse = None
    neighbors_map: dict[str, frozenset[str]] | None = None
    degree_by_agent: dict[str, float] = {a: 0.0 for a in agent_ids_for_audit}
    if _req.network_csv and _req.network_csv.strip():
        try:
            net_parse = parse_network_csv(_req.network_csv.strip(), known_agent_ids=known_agent_ids)
        except ValueError as e:
            raise HTTPException(status_code=422, detail=str(e)) from e
        run_warnings.extend(list(net_parse.warnings))
        degree_by_agent = degree_centrality(agent_ids_for_audit, net_parse.edges)
        neighbors_map = undirected_neighbor_map(known_agent_ids, net_parse.edges)

    requested_vis = _req.visibility_policy.strip().lower()
    network_visibility_fallback = False
    visibility_effective_str = requested_vis
    try:
        req_vis_enum = VisibilityPolicy(requested_vis)
    except ValueError:
        req_vis_enum = VisibilityPolicy.BROADCAST
    if req_vis_enum == VisibilityPolicy.NETWORK_BOUNDED and not (
        _req.network_csv and _req.network_csv.strip()
    ):
        visibility_effective_str = "broadcast"
        network_visibility_fallback = True
        run_warnings.append(
            "visibility_policy network_bounded requires network_csv; fell back to broadcast (ADR-002)."
        )

    tier_list, tier_rationales = compute_fidelity_tiers(
        sampling_strategy=_req.sampling_strategy,
        scenario=scenario_cfg,
        personas_for_run=personas_final,
        roster_by_slot=roster_parse.by_slot if roster_parse else None,
        agent_ids_in_order=agent_ids_for_audit if _req.sampling_strategy == "network_centrality" else None,
        network_centrality_by_agent=degree_by_agent if _req.sampling_strategy == "network_centrality" else None,
    )
    sampling_audit = build_sampling_audit_extended(
        sampling_strategy=_req.sampling_strategy,
        tiers=tier_list,
        rationales=tier_rationales,
        agent_ids=agent_ids_for_audit,
        scenario=scenario_cfg,
        personas_for_run=personas_final,
    )
    for row in sampling_audit.get("per_agent", []):
        if isinstance(row, dict):
            aid = row.get("agent_id")
            if aid:
                row["degree_centrality"] = round(float(degree_by_agent.get(str(aid), 0.0)), 6)

    config_snapshot = {
        "scenario_id": _req.scenario_id,
        "scenario_source": scenario_source,
        "scenario_doc_version": scenario_doc_version,
        "total_rounds": _req.total_rounds,
        "agent_limit": _req.agent_limit,
        "random_seed": _req.random_seed,
        "prompt_version": prompt_version,
        "llm_provider": llm_provider,
        "model_used": model_used,
        "lmstudio_model": settings.lmstudio_model,
        "anthropic_model": settings.anthropic_model,
        "lmstudio_base_url": settings.lmstudio_base_url,
        "llm_temperature": settings.llm_temperature,
        "llm_max_tokens": llm_max_tokens,
        "working_memory_last_k": settings.working_memory_last_k,
        "peer_context_max_chars": settings.peer_context_max_chars,
        "rag_effective": rag_effective,
        "rag_request_override": _req.rag_enabled,
        "server_rag_enabled": settings.rag_enabled,
        "scenario_rag_enabled": scenario_cfg.rag_enabled,
        "embedding_model_id": embedding_model_used,
        "rag_top_k": settings.rag_top_k,
        "rag_chunk_size": settings.rag_chunk_size,
        "rag_chunk_overlap": settings.rag_chunk_overlap,
        "rag_max_inject_chars": settings.rag_max_inject_chars,
        "rag_corpus_paths": list(scenario_cfg.rag_corpus_paths),
        "state_audit_enabled": settings.state_audit_enabled,
        "hybrid_routing_policy": (
            "frontier_first_turn_of_round" if llm_provider == "hybrid" else None
        ),
        "scenario_groups": [
            {"group_id": g.group_id, "name": g.name, "description": g.description} for g in scenario_cfg.groups
        ],
        "scale_warning": _req.agent_limit > 20,
        "roster_csv_applied": roster_parse is not None,
        "roster_csv_row_count": len(roster_parse.by_slot) if roster_parse else 0,
        "roster_unknown_group_ids": list(roster_parse.unknown_group_ids) if roster_parse else [],
        "agent_context_version": "2",
        "simulation_mode": _req.simulation_mode,
        "speakers_per_round": speakers_per_round_for_config_snapshot(
            _req.simulation_mode,
            _req.speakers_per_round,
        ),
        "population_schema_version": POPULATION_SCHEMA_VERSION if population_parse_result else None,
        "population_csv_applied": population_parse_result is not None,
        "population_pool_row_count": len(population_parse_result.rows) if population_parse_result else 0,
        "population_sample_mode": _req.population_sample_mode if population_parse_result else None,
        "population_unknown_group_ids": (
            list(population_parse_result.unknown_group_ids) if population_parse_result else []
        ),
        "population_draw": (
            [
                {
                    "slot_index": e.slot_index,
                    "source_file_line": e.source_file_line,
                    "csv_row_index": e.csv_row_index,
                    "persona_id": e.persona_id,
                    "stratum": e.stratum,
                    "sampling_weight": e.sampling_weight,
                }
                for e in population_draw_trace
            ]
            if population_draw_trace
            else []
        ),
        "population_merge_order": (
            "population_draw_then_roster_overlay"
            if population_parse_result and roster_parse
            else ("population_draw_only" if population_parse_result else None)
        ),
        "population_data_provenance": (
            "user_uploaded_pool_v1" if population_parse_result else None
        ),
        "population_thesis_note": (
            "Pool is user-uploaded; representativeness and any site-specific overlay (e.g. Trinidad school context) "
            "are analyst claims, not engine guarantees. IAD-neutral core fields align to AgentContextV1."
            if population_parse_result
            else None
        ),
        # Iteration 15 + ADR-002: IAD interaction policy snapshot
        "interaction_policy": {
            "turn_order_policy": _req.turn_order_policy,
            "visibility_policy": requested_vis,
            "interaction_overlay": _req.interaction_overlay,
            "policy_version": "1",
            "interaction_visibility": requested_vis,
            "visibility_effective": visibility_effective_str,
            "network_visibility_fallback": network_visibility_fallback,
        },
        "network_csv_applied": net_parse is not None,
        "network_edge_count": len(net_parse.edges) if net_parse else 0,
        "network_node_count": (
            len({s for s, _, _ in net_parse.edges} | {t for _, t, _ in net_parse.edges})
            if net_parse
            else 0
        ),
        # Iteration 19: parallel LLM concurrency
        "llm_concurrency_cap": llm_concurrency_cap,
        # Iteration 20: population scale and cohort aggregation
        "aggregation_threshold": _req.aggregation_threshold,
        "aggregation_mode": _req.agent_limit >= _req.aggregation_threshold,
        # Iteration 22: sampling strategy metadata (tiers do not change LLM behavior until Iter 23)
        "sampling_strategy": _req.sampling_strategy,
        "sampling_audit": sampling_audit,
        # Iteration 24: synthetic remainder + Tier-3 heuristic parameters
        "remainder_config": remainder_cfg.model_dump() if remainder_cfg else None,
        "synthetic_remainder_count": remainder_count,
        "core_agent_limit": core_limit,
        "tier_3_heuristic": {
            "dampening": tier_3_dampening,
            "noise_std": tier_3_noise_std,
        },
    }
    if _req.convergence_threshold is not None:
        config_snapshot["convergence_threshold"] = _req.convergence_threshold
        config_snapshot["convergence_patience"] = _req.convergence_patience
        config_snapshot["converged_at_round"] = None

    if experiment_id is not None:
        config_snapshot["experiment"] = {
            "experiment_id": experiment_id,
            "step_index": experiment_step_index,
            "run_label": experiment_run_label,
        }

    sim_id = await create_simulation_run(
        settings.sqlite_path,
        name=name,
        scenario_id=_req.scenario_id,
        status="pending",
        total_rounds=_req.total_rounds,
        random_seed=_req.random_seed,
        prompt_version=prompt_version,
        model_used=model_used,
        config_snapshot=config_snapshot,
        experiment_id=experiment_id,
    )

    asyncio.create_task(
        run_simulation_task_guarded(
            sqlite_path=settings.sqlite_path,
            simulation_id=sim_id,
            scenario_id=_req.scenario_id,
            total_rounds=_req.total_rounds,
            agent_limit=_req.agent_limit,
            random_seed=_req.random_seed,
            prompt_version=prompt_version,
            model_used=model_used,
            lmstudio_model=settings.lmstudio_model,
            lmstudio_base_url=settings.lmstudio_base_url,
            llm_temperature=settings.llm_temperature,
            llm_max_tokens=llm_max_tokens,
            working_memory_last_k=settings.working_memory_last_k,
            llm_provider=llm_provider,
            anthropic_api_key=settings.anthropic_api_key,
            anthropic_model=settings.anthropic_model,
            peer_context_max_chars=settings.peer_context_max_chars,
            rag_effective=rag_effective,
            embedding_model=embedding_model_used,
            rag_top_k=settings.rag_top_k,
            rag_chunk_size=settings.rag_chunk_size,
            rag_chunk_overlap=settings.rag_chunk_overlap,
            rag_max_inject_chars=settings.rag_max_inject_chars,
            personas_for_run=personas_for_task,
            slot_overrides=slot_for_task,
            scenario_config=scenario_cfg,
            simulation_mode=_req.simulation_mode,
            speakers_per_round=_req.speakers_per_round,
            turn_order_policy=_req.turn_order_policy,
            visibility_policy=_req.visibility_policy,
            interaction_overlay=_req.interaction_overlay,
            llm_concurrency_cap=llm_concurrency_cap,
            fidelity_tiers=tier_list,
            tier_3_dampening=tier_3_dampening,
            tier_3_noise_std=tier_3_noise_std,
            network_neighbors=neighbors_map,
            visibility_effective=visibility_effective_str,
            convergence_threshold=_req.convergence_threshold,
            convergence_patience=_req.convergence_patience,
        )
    )

    return SimulationRunResponse(id=sim_id, warnings=run_warnings)


async def wait_for_simulation_terminal(
    *,
    sqlite_path: str,
    simulation_id: str,
    poll_interval: float = 0.4,
    timeout_seconds: float = 900.0,
) -> dict[str, Any]:
    """Poll until status is completed or failed, or raise TimeoutError."""
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        row = await get_simulation_run_status_only(sqlite_path, simulation_id=simulation_id)
        if row is None:
            raise RuntimeError(f"simulation {simulation_id} not found")
        st = str(row.get("status") or "")
        if st in ("completed", "failed"):
            return row
        await asyncio.sleep(poll_interval)
    raise TimeoutError(f"simulation {simulation_id} did not finish within {timeout_seconds}s")


@router.post("/simulations/run", response_model=SimulationRunResponse)
async def run_simulation(_req: SimulationRunRequest) -> SimulationRunResponse:
    settings = get_settings()
    return await queue_simulation_run(settings, _req)


@router.get("/simulations/{simulation_id}/sampling-report")
async def get_simulation_sampling_report(simulation_id: str) -> dict[str, Any]:
    """Researcher-readable view of ``config_snapshot.sampling_audit`` (Iteration 26)."""
    settings = get_settings()
    row = await get_simulation_status_and_config_snapshot(
        settings.sqlite_path, simulation_id=simulation_id
    )
    if row is None:
        raise HTTPException(status_code=404, detail="Simulation not found")
    st = row["status"]
    if st in ("pending", "running"):
        raise HTTPException(
            status_code=409,
            detail="Simulation not finished; sampling-report is available after the run completes or fails.",
        )
    try:
        return build_sampling_report_json(row.get("config_snapshot"))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.get("/simulations/{simulation_id}/export.json")
async def export_simulation_json(simulation_id: str) -> JSONResponse:
    settings = get_settings()
    bundle = await get_simulation_export_bundle(settings.sqlite_path, simulation_id=simulation_id)
    if bundle is None:
        raise HTTPException(status_code=404, detail="Simulation not found")
    payload = {
        "export_version": EXPORT_VERSION,
        **bundle,
        "cohort_summary": compute_cohort_summary(bundle.get("agent_state_snapshots") or []),
    }
    return JSONResponse(content=payload)


@router.get("/simulations/{simulation_id}/export.zip")
async def export_simulation_zip(simulation_id: str) -> Response:
    settings = get_settings()
    bundle = await get_simulation_export_bundle(settings.sqlite_path, simulation_id=simulation_id)
    if bundle is None:
        raise HTTPException(status_code=404, detail="Simulation not found")
    zip_bytes = build_export_zip(bundle)
    filename = f"mirofish_run_{simulation_id}.zip"
    return Response(
        content=zip_bytes,
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/simulations/{simulation_id}", response_model=SimulationStatusResponse)
async def get_simulation(simulation_id: str) -> SimulationStatusResponse:
    settings = get_settings()
    res = await get_simulation_status_with_transcript(
        settings.sqlite_path,
        simulation_id=simulation_id,
    )
    if res is None:
        raise HTTPException(status_code=404, detail="Simulation not found")
    return SimulationStatusResponse(
        id=res["id"],
        status=res["status"],
        current_round=res["current_round"],
        total_rounds=res["total_rounds"],
        failure_reason=res.get("failure_reason"),
        converged_at_round=res.get("converged_at_round"),
        config_snapshot=res.get("config_snapshot"),
        transcript=res["transcript"],
        state_timeline=res.get("state_timeline", []),
        outcome_indicators=res.get("outcome_indicators", []),
        validity_notes=res.get("validity_notes", []),
        economics=res.get("economics"),
    )


@router.post("/simulations/{simulation_id}/validity-notes", response_model=dict[str, str])
async def create_validity_note(simulation_id: str, body: ValidityNoteCreate) -> dict[str, str]:
    settings = get_settings()
    if not await simulation_exists(settings.sqlite_path, simulation_id):
        raise HTTPException(status_code=404, detail="Simulation not found")
    total = await get_simulation_total_rounds(settings.sqlite_path, simulation_id)
    if body.round_number is not None and total is not None:
        if body.round_number < 1 or body.round_number > total:
            raise HTTPException(
                status_code=400,
                detail=f"round_number must be between 1 and {total} for this run",
            )
    note_id = await insert_validity_note(
        settings.sqlite_path,
        simulation_id=simulation_id,
        round_number=body.round_number,
        rater_id=body.rater_id,
        face_score=body.face_score,
        face_rubric=body.face_rubric,
        construct_score=body.construct_score,
        construct_rubric=body.construct_rubric,
        predictive_score=body.predictive_score,
        predictive_rubric=body.predictive_rubric,
        notes=body.notes,
    )
    return {"id": note_id}


def _clip_transcript_for_analysis(
    transcript: list[dict[str, Any]],
    *,
    max_turns: int = ANALYZE_TRANSCRIPT_MAX_TURNS_FIRST_PASS,
    max_response_chars: int = ANALYZE_RAW_RESPONSE_MAX_CHARS_FIRST_PASS,
) -> tuple[list[dict[str, Any]], str | None]:
    note = None
    t = transcript
    if len(t) > max_turns:
        head = max_turns // 2
        tail = max_turns - head
        t = t[:head] + t[-tail:]
        note = f"transcript_clipped: first {head} + last {tail} of {len(transcript)} turns"
    out: list[dict[str, Any]] = []
    for row in t:
        rr = str(row.get("raw_response") or "")
        if len(rr) > max_response_chars:
            rr = rr[:max_response_chars] + "…[truncated]"
        out.append(
            {
                "round_number": row.get("round_number"),
                "turn_index": row.get("turn_index"),
                "agent_id": row.get("agent_id"),
                "agent_role": row.get("agent_role"),
                "agent_name": row.get("agent_name"),
                "interaction_type": row.get("interaction_type"),
                "target_scope": row.get("target_scope"),
                "intent_tag": row.get("intent_tag"),
                "raw_response": rr,
            }
        )
    return out, note


def _bundle_slice_for_analysis(bundle: dict[str, Any]) -> dict[str, Any]:
    run = bundle.get("run") or {}
    transcript, clip_note = _clip_transcript_for_analysis(bundle.get("transcript") or [])
    slim_run = {
        k: run[k]
        for k in (
            "id",
            "name",
            "scenario_id",
            "status",
            "total_rounds",
            "current_round",
            "random_seed",
            "prompt_version",
            "model_used",
            "created_at",
            "completed_at",
        )
        if k in run
    }
    slim_run["config_snapshot"] = run.get("config_snapshot")
    out: dict[str, Any] = {
        "run": slim_run,
        "transcript": transcript,
        "outcome_indicators": (bundle.get("outcome_indicators") or [])[-30:],
        "state_timeline": (bundle.get("state_timeline") or [])[-20:],
        "validity_notes": bundle.get("validity_notes") or [],
    }
    if clip_note:
        out["_bundle_notes"] = [clip_note]
    return out


class SimulationAnalyzeRequest(BaseModel):
    research_question: str = Field(..., min_length=4, max_length=8000)
    max_tokens: int | None = Field(default=None, ge=256, le=8192)


class SimulationAnalyzeResponse(BaseModel):
    key_findings: list[str] = Field(default_factory=list)
    per_agent_summary: dict[str, str] = Field(default_factory=dict)
    trajectory_narrative: str = ""
    suggested_follow_ups: list[str] = Field(default_factory=list)
    raw_llm_text: str = ""


_ANALYZE_SYSTEM = """You are a qualitative research assistant for policy simulation transcripts.
You receive a JSON export bundle (run metadata, clipped transcript, outcomes, timeline).
Answer the user's research question with structured insights.

Return ONLY valid JSON (no markdown fences) with this shape:
{
  "key_findings": ["string", ...],
  "per_agent_summary": {"agent_id_or_name": "short summary", ...},
  "trajectory_narrative": "single cohesive narrative string",
  "suggested_follow_ups": ["string", ...]
}
Use agent_id from the transcript when possible for per_agent_summary keys.
"""


@router.post("/simulations/{simulation_id}/analyze", response_model=SimulationAnalyzeResponse)
async def analyze_simulation_export(
    simulation_id: str,
    body: SimulationAnalyzeRequest,
) -> SimulationAnalyzeResponse:
    """
    Stateless LLM analysis over the export bundle + research_question (Iteration 16).
    Does not write to the database.

    When server ``llm_provider`` is ``hybrid``, this endpoint uses LM Studio (same as bulk
    simulation turns). Use ``anthropic`` in settings for frontier-only analysis.
    """
    settings = get_settings()
    bundle = await get_simulation_export_bundle(settings.sqlite_path, simulation_id=simulation_id)
    if bundle is None:
        raise HTTPException(status_code=404, detail="Simulation not found")
    run = bundle.get("run") or {}
    if str(run.get("status") or "") != "completed":
        raise HTTPException(
            status_code=409,
            detail="Analysis requires a completed simulation run",
        )

    payload = _bundle_slice_for_analysis(bundle)
    blob = json.dumps(payload, ensure_ascii=False)
    if len(blob) > ANALYZE_LLM_JSON_CHAR_BUDGET:
        tr = payload["transcript"]
        if len(tr) > ANALYZE_TRANSCRIPT_COUNT_FOR_SECOND_RECLIP:
            n = ANALYZE_TRANSCRIPT_KEEP_HEAD_TAIL
            payload["transcript"] = tr[:n] + tr[-n:]
            payload.setdefault("_bundle_notes", []).append("transcript_reclipped: hard char budget")
        else:
            cap2 = ANALYZE_RAW_RESPONSE_MAX_CHARS_SECOND_PASS
            for row in payload["transcript"]:
                rr = str(row.get("raw_response") or "")
                if len(rr) > cap2:
                    row["raw_response"] = rr[:cap2] + "…[truncated]"
            payload.setdefault("_bundle_notes", []).append("raw_response_shortened: hard char budget")
        blob = json.dumps(payload, ensure_ascii=False)

    user_prompt = (
        f"Research question:\n{body.research_question}\n\n"
        f"Export bundle (JSON):\n{blob}"
    )

    max_tok = body.max_tokens if body.max_tokens is not None else min(4096, settings.llm_max_tokens)
    provider = settings.llm_provider
    try:
        raw = (
            await llm_complete(
                provider=provider if provider in ("lmstudio", "anthropic") else "lmstudio",
                messages=[
                    {"role": "system", "content": _ANALYZE_SYSTEM},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0.4,
                max_tokens=max_tok,
                lmstudio_base_url=settings.lmstudio_base_url,
                lmstudio_model=settings.lmstudio_model,
                anthropic_api_key=settings.anthropic_api_key,
                anthropic_model=settings.anthropic_model,
            )
        ).text
    except Exception as e:
        logger.warning("analyze_simulation LLM failed for %s: %s", simulation_id, e)
        raise HTTPException(status_code=502, detail=f"LLM call failed: {e}") from e

    text = raw.strip()
    if text.startswith("```"):
        lines = text.splitlines()
        lines = [ln for ln in lines if not ln.strip().startswith("```")]
        text = "\n".join(lines).strip()

    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        m = re.search(r"\{.*\}", text, re.DOTALL)
        if m:
            try:
                parsed = json.loads(m.group(0))
            except json.JSONDecodeError:
                parsed = {}
        else:
            parsed = {}

    if not isinstance(parsed, dict):
        parsed = {}

    def _str_list(key: str) -> list[str]:
        v = parsed.get(key, [])
        if not isinstance(v, list):
            return []
        return [str(x) for x in v if str(x).strip()]

    def _agent_map(key: str) -> dict[str, str]:
        v = parsed.get(key, {})
        if not isinstance(v, dict):
            return {}
        return {str(k): str(val) for k, val in v.items() if str(val).strip()}

    return SimulationAnalyzeResponse(
        key_findings=_str_list("key_findings"),
        per_agent_summary=_agent_map("per_agent_summary"),
        trajectory_narrative=str(parsed.get("trajectory_narrative") or "")[:32000],
        suggested_follow_ups=_str_list("suggested_follow_ups"),
        raw_llm_text=raw[:4000],
    )


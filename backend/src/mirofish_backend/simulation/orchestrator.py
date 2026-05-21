import asyncio
import json
import logging
import random
import time
from dataclasses import dataclass
from typing import Any, NamedTuple

from mirofish_backend.roster.csv_roster import personas_for_run as build_personas_for_agent_limit
from mirofish_backend.scenarios.registry import PersonaTemplate, ScenarioConfig, get_scenario
from mirofish_backend.simulation.agent_context import (
    AgentContextV1,
    attribute_sections_for_snapshot,
    build_agent_context_v1,
)
from mirofish_backend.simulation.interaction_policy import (
    InteractionPolicy,
    ChannelType,
    VisibilityPolicy,
    apply_turn_order,
    build_interaction_policy,
    channel_for_turn,
    visible_turns_for_agent,
)
from mirofish_backend.llm.prompt_templates import build_system_prompt, build_user_prompt, simplified_persona_prompt
from mirofish_backend.llm.round_summary import build_round_summary
from mirofish_backend.llm.model_profiles import ANTHROPIC_DEFAULT_ID, LOCAL_LMSTUDIO_DEFAULT_ID
from mirofish_backend.llm.routing_policies import (
    llm_provider_to_routing_policy,
    resolve_effective_profile_id,
    HEURISTIC_PROFILE_SENTINEL,
)
from mirofish_backend.llm.router import effective_model_id, llm_complete, resolve_effective_provider
from mirofish_backend.llm.context_clip import clip_memory_lines, clip_recent_interactions
from mirofish_backend.llm.state_parse import resolve_state_from_response
from mirofish_backend.rag.retrieve import retrieve_top_k, snippets_for_prompt
from mirofish_backend.simulation.transcript_writer import (
    append_round_to_transcript,
    close_transcript,
    open_transcript,
)
from mirofish_backend.simulation.heuristic import (
    apply_tier3_heuristic_to_states,
    mean_deltas_tier12_for_round,
    tier3_heuristic_rng,
)
from mirofish_backend.db.repo import (
    get_recent_interactions,
    get_last_agent_responses,
    get_round_summaries,
    get_turns_for_round,
    insert_agent_state_snapshot,
    insert_agent_turn,
    insert_global_state_snapshot,
    insert_round_outcome,
    merge_simulation_config_snapshot,
    set_simulation_status,
    update_simulation_token_totals,
    upsert_round_summary,
)

logger = logging.getLogger("mirofish_backend.simulation.orchestrator")


class _TurnOutcome(NamedTuple):
    conflict: bool
    input_tokens: int | None
    output_tokens: int | None


@dataclass(frozen=True)
class AgentInstance:
    agent_id: str
    persona: PersonaTemplate
    role: str
    name: str
    context: AgentContextV1
    # Iteration 22: metadata for sampling_audit; Iteration 23+ may branch prompts/LLM by tier.
    fidelity_tier: int = 1

    @property
    def demographics(self) -> dict[str, Any]:
        return self.context.demographics


@dataclass(frozen=True)
class InteractionPlan:
    interaction_type: str
    target_scope: str
    target_agent_id: str | None
    target_agent_name: str | None
    intent_tag: str


@dataclass
class AgentState:
    support_level: float
    resistance_level: float
    workload_stress: float
    belief_posture: str


def _group_labels_for_persona(scenario: ScenarioConfig, persona: PersonaTemplate) -> tuple[str, ...]:
    id_to_name = {g.group_id: g.name for g in scenario.groups}
    return tuple(id_to_name.get(gid, gid) for gid in persona.groups)


def _merge_section_dict(base: dict[str, Any], overlay: dict[str, Any] | None) -> dict[str, Any]:
    out = dict(base)
    if overlay:
        out.update(overlay)
    return out


def _attribute_overlays_from_slot(ov: dict[str, Any] | None) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    if not ov:
        return {}, {}, {}

    def grab(key: str) -> dict[str, Any]:
        raw = ov.get(key)
        return dict(raw) if isinstance(raw, dict) else {}

    return grab("identity"), grab("attitudes"), grab("personal_history")


def _merge_demographics(
    *,
    role_level: int,
    idx: int,
    overrides: dict[str, Any] | None,
) -> dict[str, Any]:
    dem = _build_demographics(role_level=role_level, idx=idx)
    if overrides:
        for k in ("age", "sex", "ethnicity", "ses"):
            if k in overrides and overrides[k] is not None:
                dem[k] = overrides[k]
    return dem


def _build_agent_instances(
    scenario: ScenarioConfig,
    personas_for_run: list[PersonaTemplate],
    slot_overrides: list[dict[str, Any]] | None = None,
    fidelity_tiers: list[int] | None = None,
) -> list[AgentInstance]:
    base_personas = scenario.personas
    if not base_personas:
        raise ValueError(f"Scenario has no personas: {scenario.scenario_id}")
    if not personas_for_run:
        raise ValueError("personas_for_run is empty")
    if slot_overrides is not None and len(slot_overrides) != len(personas_for_run):
        raise ValueError("slot_overrides length must match personas_for_run")
    if fidelity_tiers is not None and len(fidelity_tiers) != len(personas_for_run):
        raise ValueError("fidelity_tiers length must match personas_for_run")

    instances: list[AgentInstance] = []
    for idx, persona in enumerate(personas_for_run):
        agent_id = f"{persona.persona_id}_{idx:03d}"
        if idx < len(base_personas):
            name = persona.name
        else:
            name = f"{persona.name} {idx + 1}"
        ov = slot_overrides[idx] if slot_overrides else None
        dem = _merge_demographics(role_level=persona.role_level, idx=idx, overrides=ov)
        io, ao, ho = _attribute_overlays_from_slot(ov)
        ctx = build_agent_context_v1(
            slot_index=idx,
            demographics=dem,
            group_ids=persona.groups,
            identity=_merge_section_dict(persona.identity, io),
            attitudes=_merge_section_dict(persona.attitudes, ao),
            personal_history=_merge_section_dict(persona.personal_history, ho),
        )
        ft = fidelity_tiers[idx] if fidelity_tiers is not None else 1
        instances.append(
            AgentInstance(
                agent_id=agent_id,
                persona=persona,
                role=persona.role,
                name=name,
                context=ctx,
                fidelity_tier=ft,
            )
        )
    return instances


def _agents_for_round(
    all_agents: list[AgentInstance],
    *,
    round_number: int,
    simulation_mode: str,
    speakers_per_round: int,
    random_seed: int,
) -> list[AgentInstance]:
    """
    Deterministic subset for ``sample_k_per_round``; full roster for ``full_round_robin``.
    Seed mix: reproducible per (random_seed, round_number, mode).
    """
    mode = (simulation_mode or "full_round_robin").strip().lower()
    if mode == "full_round_robin":
        return list(all_agents)
    if mode != "sample_k_per_round":
        raise ValueError(f"Unknown simulation_mode {simulation_mode!r}; use 'full_round_robin' or 'sample_k_per_round'")
    n = len(all_agents)
    if n == 0:
        return []
    k = max(1, min(speakers_per_round, n))
    # Local RNG so we do not rely on global random state ordering elsewhere.
    mix = (random_seed & 0xFFFFFFFF) ^ (round_number * 0x9E3779B9)
    r = random.Random(mix)
    idxs = list(range(n))
    r.shuffle(idxs)
    chosen = sorted(idxs[:k])
    return [all_agents[i] for i in chosen]


def _build_demographics(*, role_level: int, idx: int) -> dict[str, Any]:
    """Synthetic demographics when roster/population do not supply them.

    Domain-agnostic: age scales with ``role_level`` (lower number = higher authority → older baseline).
    No role-name strings.
    """
    sex_cycle = ["female", "male"]
    # Baseline ages matched legacy principal / middle / teacher spacing (8-year steps).
    # Cap spacing at six tiers and floor age so high role_level never goes negative (architect review).
    age = max(22, 49 - (min(max(1, role_level), 6) - 1) * 8 + (idx % 3))
    return {
        "age": age,
        "sex": sex_cycle[idx % len(sex_cycle)],
        "ethnicity": "unspecified",
        "ses": "unspecified",
    }


def _neutral_initial_state() -> AgentState:
    return AgentState(support_level=0.50, resistance_level=0.35, workload_stress=0.45, belief_posture="neutral")


def _initial_state_from_persona(persona: PersonaTemplate) -> AgentState:
    raw = persona.initial_state
    if not raw:
        return _neutral_initial_state()
    base = _neutral_initial_state()
    return AgentState(
        support_level=float(raw.get("support_level", base.support_level)),
        resistance_level=float(raw.get("resistance_level", base.resistance_level)),
        workload_stress=float(raw.get("workload_stress", base.workload_stress)),
        belief_posture=str(raw.get("belief_posture", base.belief_posture)),
    )


def _clamp(value: float, low: float = 0.0, high: float = 1.0) -> float:
    return max(low, min(high, value))


def _population_convergence_delta(
    agents: list[AgentInstance],
    agent_states: dict[str, AgentState],
    prev: dict[str, tuple[float, float, float]],
) -> float | None:
    """Mean over agents of mean abs Δ across support, resistance, workload vs prior round.

    Precondition: every ``agents`` entry should have a ``prev`` entry (same roster each round).
    Agents missing from ``prev`` are skipped defensively (e.g. future mid-run roster changes).
    """
    if not agents:
        return None
    acc = 0.0
    n = 0
    for ag in agents:
        if ag.agent_id not in prev:
            continue
        st = agent_states[ag.agent_id]
        ps, pr, pw = prev[ag.agent_id]
        acc += (
            abs(st.support_level - ps) + abs(st.resistance_level - pr) + abs(st.workload_stress - pw)
        ) / 3.0
        n += 1
    return acc / n if n else None


def _count_keywords(text: str, keywords: list[str]) -> int:
    lowered = text.lower()
    return sum(lowered.count(k) for k in keywords)


def _apply_state_from_response(state: AgentState, response: str) -> tuple[AgentState, bool, str]:
    parsed, source = resolve_state_from_response(
        response,
        support_level=state.support_level,
        resistance_level=state.resistance_level,
        workload_stress=state.workload_stress,
        belief_posture=state.belief_posture,
    )
    if parsed is not None:
        s, r, w, posture, conflict = parsed
        return (
            AgentState(
                support_level=_clamp(s),
                resistance_level=_clamp(r),
                workload_stress=_clamp(w),
                belief_posture=posture,
            ),
            conflict,
            source,
        )
    new_state, conflict = _apply_state_update_keyword(state, response)
    return new_state, conflict, "keyword_fallback"


def _apply_state_update_keyword(state: AgentState, response: str) -> tuple[AgentState, bool]:
    support_hits = _count_keywords(response, ["support", "align", "feasible", "improve", "ready"])
    resistance_hits = _count_keywords(response, ["concern", "resist", "risk", "unclear", "difficult"])
    workload_hits = _count_keywords(response, ["workload", "burden", "time", "resource", "capacity"])

    support_level = _clamp(state.support_level + (0.03 * support_hits) - (0.02 * resistance_hits))
    resistance_level = _clamp(state.resistance_level + (0.03 * resistance_hits) - (0.02 * support_hits))
    workload_stress = _clamp(state.workload_stress + (0.04 * workload_hits) - 0.01)

    if support_level - resistance_level >= 0.20:
        posture = "supportive"
    elif resistance_level - support_level >= 0.20:
        posture = "resistant"
    else:
        posture = "mixed"

    conflict_flag = resistance_hits > support_hits
    return (
        AgentState(
            support_level=support_level,
            resistance_level=resistance_level,
            workload_stress=workload_stress,
            belief_posture=posture,
        ),
        conflict_flag,
    )


def _policy_event_for_round(scenario: ScenarioConfig, round_number: int) -> str:
    if round_number in scenario.policy_events:
        return scenario.policy_events[round_number]
    return (
        f"Round {round_number}: No new external MOE bulletin this round; continue implementation "
        "discussion grounded in what stakeholders already said in prior rounds."
    )


def _build_interaction_plan(
    agents: list[AgentInstance],
    round_number: int,
    turn_index: int,
    policy: InteractionPolicy | None = None,
) -> InteractionPlan:
    """
    Deterministic interaction planning over the **current round's speaker list** (`agents`):
    - First turn of a round is a school-wide broadcast.
    - Middle turns reply to the previous agent (within this list).
    - Last turn records a meeting-style synthesis note.

    With `sample_k_per_round` and small K (e.g. 2), roles are only broadcast + meeting_note
    (no reply turns). At K >= 3, reply turns appear between them. The same physical agent may
    receive different interaction_type sequences across rounds depending on sampling order.

    Iteration 15: When an :class:`~mirofish_backend.simulation.interaction_policy.InteractionPolicy`
    is provided, ``channel_for_turn`` may override the default channel selection (e.g. Trinity
    overlay forces BROADCAST for principal regardless of position).
    """
    agent_role_level = agents[turn_index - 1].persona.role_level if agents else 3

    if policy is not None:
        channel = channel_for_turn(
            turn_index=turn_index,
            total_speakers=len(agents),
            agent_role_level=agent_role_level,
            policy=policy,
        )
    else:
        # Legacy: replicate pre-Iteration-15 logic
        if turn_index == 1:
            channel = ChannelType.BROADCAST
        elif turn_index == len(agents):
            channel = ChannelType.MEETING
        else:
            channel = ChannelType.DIRECT

    if channel == ChannelType.BROADCAST:
        return InteractionPlan(
            interaction_type=ChannelType.BROADCAST.value,
            target_scope="all",
            target_agent_id=None,
            target_agent_name=None,
            intent_tag="policy_update",
        )

    if channel == ChannelType.MEETING:
        return InteractionPlan(
            interaction_type="meeting_note",
            target_scope="all",
            target_agent_id=None,
            target_agent_name=None,
            intent_tag="coordination_summary",
        )

    # DIRECT / reply
    target_agent = agents[turn_index - 2]
    return InteractionPlan(
        interaction_type="reply",
        target_scope="agent",
        target_agent_id=target_agent.agent_id,
        target_agent_name=target_agent.name,
        intent_tag="peer_response",
    )


async def run_simulation_task(
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
    personas_for_run: list[PersonaTemplate] | None = None,
    slot_overrides: list[dict[str, Any]] | None = None,
    scenario_config: ScenarioConfig | None = None,
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
    round_summary_enabled: bool = True,
    transcript_dir: str = "./data/transcripts",
    routing_policy: str | None = None,
    routing_profile_local_id: str | None = None,
    routing_profile_frontier_id: str | None = None,
    openai_compatible_api_key: str = "",
) -> None:
    mode = (llm_provider or "lmstudio").strip().lower()
    if mode not in ("lmstudio", "anthropic", "hybrid"):
        raise ValueError(f"Unknown llm_provider {llm_provider!r}; expected 'lmstudio', 'anthropic', or 'hybrid'")

    policy = routing_policy or llm_provider_to_routing_policy(mode)
    local_profile_id = routing_profile_local_id or LOCAL_LMSTUDIO_DEFAULT_ID
    frontier_profile_id = routing_profile_frontier_id or ANTHROPIC_DEFAULT_ID

    random.seed(random_seed)
    scenario = scenario_config if scenario_config is not None else get_scenario(scenario_id)
    if scenario.scenario_id != scenario_id:
        raise ValueError(
            f"scenario_config.scenario_id {scenario.scenario_id!r} does not match request {scenario_id!r}"
        )
    personas = (
        personas_for_run
        if personas_for_run is not None
        else build_personas_for_agent_limit(scenario, agent_limit, None)
    )
    if len(personas) != agent_limit:
        raise ValueError(f"personas_for_run length {len(personas)} != agent_limit {agent_limit}")
    agents = _build_agent_instances(
        scenario, personas, slot_overrides=slot_overrides, fidelity_tiers=fidelity_tiers
    )
    agent_states = {agent.agent_id: _initial_state_from_persona(agent.persona) for agent in agents}
    previous_readiness = 0.0
    sim_mode = (simulation_mode or "full_round_robin").strip().lower()

    # Resolve interaction overlay from scenario if not explicitly passed
    effective_overlay = interaction_overlay or getattr(scenario, "interaction_overlay", "none") or "none"
    interaction_policy = build_interaction_policy(
        turn_order_policy=turn_order_policy,
        visibility_policy=visibility_policy,
        interaction_overlay=effective_overlay,
    )

    ve_raw = (visibility_effective or "").strip().lower()
    if ve_raw == "full":
        ve_raw = "broadcast"
    if ve_raw:
        effective_visibility = VisibilityPolicy(ve_raw)
    else:
        effective_visibility = interaction_policy.visibility_policy

    await set_simulation_status(sqlite_path, simulation_id=simulation_id, status="running", current_round=0)

    # Semaphore bounds concurrent LLM calls within a round (Iteration 19).
    # Cap=1 reproduces sequential behaviour; rounds are always sequential.
    sem = asyncio.Semaphore(llm_concurrency_cap)

    conv_streak = 0
    prev_agent_triples: dict[str, tuple[float, float, float]] | None = None
    patience = max(1, int(convergence_patience)) if convergence_threshold is not None else 0
    run_in_acc = 0
    run_out_acc = 0

    if round_summary_enabled:
        agent_roster = [(a.name, a.role) for a in agents]
        await open_transcript(
            transcript_dir,
            simulation_id=simulation_id,
            scenario_id=scenario_id,
            agent_names=agent_roster,
            total_rounds=total_rounds,
            model_used=model_used,
        )

    for round_number in range(1, total_rounds + 1):
        policy_event = _policy_event_for_round(scenario, round_number)
        round_agents = _agents_for_round(
            agents,
            round_number=round_number,
            simulation_mode=sim_mode,
            speakers_per_round=speakers_per_round,
            random_seed=random_seed,
        )

        # Apply IAD turn order policy (hierarchical sorts by role_level)
        round_agents = apply_turn_order(round_agents, interaction_policy)
        spoke_ids = frozenset(a.agent_id for a in round_agents)

        # Pre-assign turn indices BEFORE parallel dispatch so interaction plans are deterministic.
        turn_assignments: list[tuple[int, AgentInstance]] = list(enumerate(round_agents, start=1))
        round_start = time.perf_counter()

        states_before_t12: dict[str, tuple[float, float, float]] = {}
        for ag in round_agents:
            if ag.fidelity_tier in (1, 2):
                st0 = agent_states[ag.agent_id]
                states_before_t12[ag.agent_id] = (
                    st0.support_level,
                    st0.resistance_level,
                    st0.workload_stress,
                )

        async def _run_one_turn(turn_index: int, agent: AgentInstance) -> _TurnOutcome:
            """Execute one agent turn under the semaphore.

            Captures round_agents, round_number, policy_event, agent_states, and simulation
            parameters from the enclosing scope. Safe because asyncio.gather awaits all
            coroutines for the current round before the outer loop advances.

            Parallel turns in the same round see only prior-round context in the DB
            (correct by design — same-round turns are dispatched before any writes).
            """
            async with sem:
                turn_start = time.perf_counter()
                interaction_plan = _build_interaction_plan(
                    round_agents, round_number, turn_index, policy=interaction_policy
                )
                state = agent_states[agent.agent_id]
                tier_raw = agent.fidelity_tier or 1
                try:
                    tr = int(tier_raw)
                except (TypeError, ValueError):
                    tr = 1
                tier = tr if tr in (1, 2, 3) else 1

                # Iteration 23-24: Tier 3 — no LLM; transcript marker only; state unchanged (real heuristic in Iter 24).
                if tier == 3:
                    raw_response = "[Tier 3 — heuristic state update]"
                    raw_prompt = (
                        "[TIER 3] No LLM. State updated after the round via Tier-1/2 mean-delta heuristic.\n"
                        f"round={round_number} turn={turn_index} agent={agent.agent_id}"
                    )
                    await insert_agent_turn(
                        sqlite_path,
                        simulation_id=simulation_id,
                        round_number=round_number,
                        turn_index=turn_index,
                        agent_id=agent.agent_id,
                        agent_role=agent.role,
                        agent_name=agent.name,
                        interaction_type=interaction_plan.interaction_type,
                        target_scope=interaction_plan.target_scope,
                        target_agent_id=interaction_plan.target_agent_id,
                        target_agent_name=interaction_plan.target_agent_name,
                        intent_tag=interaction_plan.intent_tag,
                        raw_prompt=raw_prompt,
                        raw_response=raw_response,
                        latency_ms=0,
                        group_ids=agent.persona.groups,
                        effective_provider="heuristic",
                        effective_model="none",
                        effective_profile_id=HEURISTIC_PROFILE_SENTINEL,
                        fidelity_tier=3,
                        input_tokens=0,
                        output_tokens=0,
                    )
                    return _TurnOutcome(False, 0, 0)

                if turn_index == 1 and round_number > 1:
                    # Full round-robin: scale peer window with roster × prior rounds (capped).
                    # sample_k_per_round: tie window to speaking cohort (Iteration 12).
                    if sim_mode == "sample_k_per_round":
                        interaction_last_k = min(
                            12,
                            max(
                                working_memory_last_k * 2,
                                len(round_agents) * max(1, round_number - 1) * 3,
                            ),
                        )
                    else:
                        interaction_last_k = min(
                            12,
                            max(working_memory_last_k * 2, len(agents) * (round_number - 1)),
                        )
                else:
                    interaction_last_k = working_memory_last_k * 2

                # Tier 2: shorter peer / memory context (Iteration 23).
                peer_limit = max(1, peer_context_max_chars // 2) if tier == 2 else peer_context_max_chars

                prior_agent_memory = clip_memory_lines(
                    await get_last_agent_responses(
                        sqlite_path,
                        simulation_id=simulation_id,
                        agent_id=agent.agent_id,
                        last_k=working_memory_last_k,
                    ),
                    max_chars=peer_limit,
                )
                recent_raw = await get_recent_interactions(
                    sqlite_path,
                    simulation_id=simulation_id,
                    last_k=interaction_last_k,
                )
                recent_clipped = clip_recent_interactions(
                    recent_raw,
                    max_chars=peer_limit,
                )
                # ADR-002: visibility may fall back to broadcast when network_csv absent
                recent_visible = visible_turns_for_agent(
                    recent_clipped,
                    agent,
                    interaction_policy,
                    effective_visibility=effective_visibility,
                    network_neighbors=network_neighbors,
                    round_speaker_ids=spoke_ids,
                )
                recent_interactions = [r for r in recent_visible if r.get("agent_id") != agent.agent_id]

                prior_summaries: list[str] | None = None
                if round_summary_enabled and round_number > 1:
                    summary_rows = await get_round_summaries(
                        sqlite_path,
                        simulation_id=simulation_id,
                        up_to_round=round_number,
                    )
                    prior_summaries = [r["summary_text"] for r in summary_rows] if summary_rows else None

                context_snippets: list[dict[str, Any]] | None = None
                if rag_effective:
                    try:
                        q = f"{policy_event}\n{interaction_plan.intent_tag}"
                        snips = await retrieve_top_k(
                            query=q,
                            scenario_id=scenario.scenario_id,
                            rag_corpus_paths=scenario.rag_corpus_paths,
                            lmstudio_base_url=lmstudio_base_url,
                            embedding_model=embedding_model,
                            top_k=rag_top_k,
                            chunk_size=rag_chunk_size,
                            chunk_overlap=rag_chunk_overlap,
                            max_chars=rag_max_inject_chars,
                        )
                        context_snippets = snippets_for_prompt(snips) if snips else None
                    except Exception as rag_err:
                        logger.warning("RAG retrieval/embed failed: %s", rag_err)

                state_dict = {
                    "support_level": state.support_level,
                    "resistance_level": state.resistance_level,
                    "workload_stress": state.workload_stress,
                    "belief_posture": state.belief_posture,
                }
                if tier == 2:
                    system_prompt = simplified_persona_prompt(
                        scenario_id=scenario_id,
                        role=agent.role,
                        name=agent.name,
                        style_cues=agent.persona.style_cues,
                        beliefs=agent.persona.beliefs,
                        state=state_dict,
                        prompt_version=prompt_version,
                    )
                else:
                    system_prompt = build_system_prompt(
                        scenario_id=scenario_id,
                        role=agent.role,
                        name=agent.name,
                        style_cues=agent.persona.style_cues,
                        beliefs=agent.persona.beliefs,
                        demographics=agent.context.to_prompt_demographics(),
                        state=state_dict,
                        prompt_version=prompt_version,
                        psychological_profile=agent.persona.psychological_profile,
                        implementation_profile=agent.persona.implementation_profile,
                        group_affiliations=_group_labels_for_persona(scenario, agent.persona),
                        identity=agent.context.identity,
                        attitudes=agent.context.attitudes,
                        personal_history=agent.context.personal_history,
                    )
                user_prompt = build_user_prompt(
                    round_number=round_number,
                    policy_event=policy_event,
                    interaction_type=interaction_plan.interaction_type,
                    target_scope=interaction_plan.target_scope,
                    target_agent_name=interaction_plan.target_agent_name,
                    intent_tag=interaction_plan.intent_tag,
                    prior_agent_memory=prior_agent_memory,
                    recent_interactions=recent_interactions,
                    context_snippets=context_snippets,
                    round_summaries=prior_summaries,
                )
                raw_prompt = f"[SYSTEM]\n{system_prompt}\n\n[USER]\n{user_prompt}"
                effective = resolve_effective_provider(
                    routing_policy=policy,
                    round_number=round_number,
                    turn_index=turn_index,
                )
                effective_profile_id = resolve_effective_profile_id(
                    routing_policy=policy,
                    turn_index=turn_index,
                    local_profile_id=local_profile_id,
                    frontier_profile_id=frontier_profile_id,
                )
                logger.info(
                    "llm_turn simulation_id=%s round=%s turn=%s tier=%s routing_policy=%s effective_provider=%s profile=%s",
                    simulation_id[:12],
                    round_number,
                    turn_index,
                    tier,
                    policy,
                    effective,
                    effective_profile_id,
                )
                in_tok: int | None = None
                out_tok: int | None = None
                try:
                    completion = await llm_complete(
                        provider=effective,
                        messages=[
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": user_prompt},
                        ],
                        temperature=llm_temperature,
                        max_tokens=llm_max_tokens,
                        lmstudio_base_url=lmstudio_base_url,
                        lmstudio_model=lmstudio_model,
                        anthropic_api_key=anthropic_api_key,
                        anthropic_model=anthropic_model,
                        openai_compatible_api_key=openai_compatible_api_key,
                    )
                    raw_response = completion.text
                    in_tok, out_tok = completion.input_tokens, completion.output_tokens
                except Exception as llm_err:
                    raw_response = f"[LLM error] {type(llm_err).__name__}: {llm_err}"

                updated_state, conflict_flag, state_update_source = _apply_state_from_response(
                    state, raw_response
                )
                # Each agent has a unique key — no contention between parallel turns.
                agent_states[agent.agent_id] = updated_state

                latency_ms = int((time.perf_counter() - turn_start) * 1000)
                eff_model = effective_model_id(
                    provider=effective,
                    lmstudio_model=lmstudio_model,
                    anthropic_model=anthropic_model,
                )
                await insert_agent_turn(
                    sqlite_path,
                    simulation_id=simulation_id,
                    round_number=round_number,
                    turn_index=turn_index,
                    agent_id=agent.agent_id,
                    agent_role=agent.role,
                    agent_name=agent.name,
                    interaction_type=interaction_plan.interaction_type,
                    target_scope=interaction_plan.target_scope,
                    target_agent_id=interaction_plan.target_agent_id,
                    target_agent_name=interaction_plan.target_agent_name,
                    intent_tag=interaction_plan.intent_tag,
                    raw_prompt=raw_prompt,
                    raw_response=raw_response,
                    latency_ms=latency_ms,
                    group_ids=agent.persona.groups,
                    effective_provider=effective,
                    effective_model=eff_model,
                    effective_profile_id=effective_profile_id,
                    fidelity_tier=tier,
                    input_tokens=in_tok,
                    output_tokens=out_tok,
                    state_update_source=state_update_source,
                )
                return _TurnOutcome(conflict_flag, in_tok, out_tok)

        # Dispatch all turns for this round concurrently; collect results for round metrics.
        # return_exceptions=True isolates per-turn failures — one bad turn does not abort the round.
        results = await asyncio.gather(
            *(_run_one_turn(ti, ag) for ti, ag in turn_assignments),
            return_exceptions=True,
        )

        round_wall_ms = int((time.perf_counter() - round_start) * 1000)
        round_conflict_events = 0
        failed_turns = 0
        for i, result in enumerate(results):
            if isinstance(result, BaseException):
                ti, ag = turn_assignments[i]
                logger.error(
                    "turn_failed simulation_id=%s round=%s turn=%s agent=%s error=%s",
                    simulation_id[:12],
                    round_number,
                    ti,
                    ag.agent_id,
                    result,
                )
                failed_turns += 1
            else:
                turn_res: _TurnOutcome = result
                round_conflict_events += int(turn_res.conflict)
                if turn_res.input_tokens is not None:
                    run_in_acc += turn_res.input_tokens
                if turn_res.output_tokens is not None:
                    run_out_acc += turn_res.output_tokens

        await update_simulation_token_totals(
            sqlite_path,
            simulation_id=simulation_id,
            total_input_tokens=run_in_acc,
            total_output_tokens=run_out_acc,
        )
        logger.info(
            "round_complete simulation_id=%s round=%s turns=%d failed=%d wall_ms=%d",
            simulation_id[:12],
            round_number,
            len(turn_assignments),
            failed_turns,
            round_wall_ms,
        )

        # Iteration 24: shift Tier-3 agents toward mean Tier-1/2 state delta (+ noise).
        # Skip when no Tier-1/2 speakers this round (Tier-3-only runs stay stable; Iteration 23 test).
        tier3_ids = [a.agent_id for a in agents if a.fidelity_tier == 3]
        has_t12_speakers = any(a.fidelity_tier in (1, 2) for a in round_agents)
        if tier3_ids and has_t12_speakers:
            ds, dr, dw = mean_deltas_tier12_for_round(round_agents, states_before_t12, agent_states)
            h_rng = tier3_heuristic_rng(random_seed=random_seed, round_number=round_number)
            apply_tier3_heuristic_to_states(
                tier3_agent_ids=tier3_ids,
                agent_states=agent_states,
                delta_support=ds,
                delta_resistance=dr,
                delta_workload=dw,
                dampening=tier_3_dampening,
                noise_std=tier_3_noise_std,
                rng=h_rng,
            )

        state_values = list(agent_states.values())
        avg_support = sum(s.support_level for s in state_values) / len(state_values)
        avg_resistance = sum(s.resistance_level for s in state_values) / len(state_values)
        avg_workload = sum(s.workload_stress for s in state_values) / len(state_values)
        spread_support = max(s.support_level for s in state_values) - min(s.support_level for s in state_values)

        implementation_readiness = _clamp(avg_support - (0.5 * avg_resistance) + (0.3 * (1.0 - avg_workload)))
        alignment_index = _clamp(1.0 - spread_support)
        adoption_momentum = _clamp((implementation_readiness - previous_readiness) + 0.5)
        consistency_index = _clamp(alignment_index * (1.0 - (0.5 * avg_workload)))
        previous_readiness = implementation_readiness

        conv_delta: float | None = None
        if round_number > 1 and prev_agent_triples is not None:
            conv_delta = _population_convergence_delta(agents, agent_states, prev_agent_triples)

        await insert_global_state_snapshot(
            sqlite_path,
            simulation_id=simulation_id,
            round_number=round_number,
            implementation_readiness=implementation_readiness,
            alignment_index=alignment_index,
            convergence_delta=conv_delta,
        )
        await insert_round_outcome(
            sqlite_path,
            simulation_id=simulation_id,
            round_number=round_number,
            adoption_momentum=adoption_momentum,
            conflict_events=round_conflict_events,
            consistency_index=consistency_index,
        )

        for agent in agents:
            st = agent_states[agent.agent_id]
            sections = attribute_sections_for_snapshot(agent.context)
            await insert_agent_state_snapshot(
                sqlite_path,
                simulation_id=simulation_id,
                round_number=round_number,
                agent_id=agent.agent_id,
                agent_role=agent.role,
                agent_name=agent.name,
                age=agent.demographics.get("age"),
                sex=agent.demographics.get("sex"),
                ethnicity=agent.demographics.get("ethnicity"),
                ses=agent.demographics.get("ses"),
                support_level=st.support_level,
                resistance_level=st.resistance_level,
                workload_stress=st.workload_stress,
                belief_posture=st.belief_posture,
                group_ids=agent.persona.groups,
                spoke_this_round=agent.agent_id in spoke_ids,
                attribute_sections_json=json.dumps(sections, sort_keys=True),
            )

        if round_summary_enabled:
            round_turns = await get_turns_for_round(
                sqlite_path,
                simulation_id=simulation_id,
                round_number=round_number,
            )
            summary_text = build_round_summary(
                round_number=round_number,
                policy_event=policy_event,
                turns=round_turns,
            )
            await upsert_round_summary(
                sqlite_path,
                simulation_id=simulation_id,
                round_number=round_number,
                summary_text=summary_text,
            )
            await append_round_to_transcript(
                transcript_dir,
                simulation_id=simulation_id,
                round_number=round_number,
                policy_event=policy_event,
                turns=round_turns,
                round_summary=summary_text,
            )

        prev_agent_triples = {
            ag.agent_id: (
                agent_states[ag.agent_id].support_level,
                agent_states[ag.agent_id].resistance_level,
                agent_states[ag.agent_id].workload_stress,
            )
            for ag in agents
        }

        if convergence_threshold is not None and conv_delta is not None:
            thr = float(convergence_threshold)
            if conv_delta < thr:
                conv_streak += 1
            else:
                conv_streak = 0
            if conv_streak >= patience:
                await merge_simulation_config_snapshot(
                    sqlite_path,
                    simulation_id=simulation_id,
                    updates={"converged_at_round": round_number},
                )
                await set_simulation_status(
                    sqlite_path,
                    simulation_id=simulation_id,
                    status="completed",
                    current_round=round_number,
                    record_converged_at_round=True,
                    converged_at_round=round_number,
                )
                if round_summary_enabled:
                    await close_transcript(
                        transcript_dir,
                        simulation_id=simulation_id,
                        completed_rounds=round_number,
                        status="converged",
                    )
                return

        await set_simulation_status(
            sqlite_path,
            simulation_id=simulation_id,
            status="running",
            current_round=round_number,
        )

    if round_summary_enabled:
        await close_transcript(
            transcript_dir,
            simulation_id=simulation_id,
            completed_rounds=total_rounds,
            status="completed",
        )
    await set_simulation_status(
        sqlite_path,
        simulation_id=simulation_id,
        status="completed",
        current_round=total_rounds,
    )


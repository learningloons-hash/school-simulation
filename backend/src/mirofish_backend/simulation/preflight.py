"""Pre-run context and cost estimates (Senna Arc 8, iter-38)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from mirofish_backend.llm.model_profiles import ModelProfile, RunProfileResolution
from mirofish_backend.llm.routing_policies import (
    llm_provider_to_routing_policy,
    routing_policy_from_mode,
)
from mirofish_backend.simulation.economics import estimate_cost_usd

# Conservative per-LLM-turn token envelope (no tokenizer).
_DEFAULT_AVG_INPUT_TOKENS = 2500


@dataclass(frozen=True)
class PreflightEstimate:
    total_speaking_turns: int
    llm_turns: int
    heuristic_turns: int
    anthropic_llm_turns: int
    openai_compatible_llm_turns: int
    estimated_input_tokens: int
    estimated_output_tokens: int
    estimated_cost_usd: float
    context_window: int | None
    context_pressure_ratio: float | None
    warnings: tuple[str, ...]

    def to_snapshot(self) -> dict[str, Any]:
        return {
            "total_speaking_turns": self.total_speaking_turns,
            "llm_turns": self.llm_turns,
            "heuristic_turns": self.heuristic_turns,
            "anthropic_llm_turns": self.anthropic_llm_turns,
            "openai_compatible_llm_turns": self.openai_compatible_llm_turns,
            "estimated_input_tokens": self.estimated_input_tokens,
            "estimated_output_tokens": self.estimated_output_tokens,
            "estimated_cost_usd": self.estimated_cost_usd,
            "context_window": self.context_window,
            "context_pressure_ratio": self.context_pressure_ratio,
        }


def speakers_per_round_count(
    *,
    agent_count: int,
    simulation_mode: str,
    speakers_per_round: int,
) -> int:
    mode = (simulation_mode or "full_round_robin").strip().lower()
    n = max(0, agent_count)
    if mode == "sample_k_per_round":
        return max(0, min(max(1, speakers_per_round), n)) if n else 0
    return n


def estimate_run_preflight(
    *,
    total_rounds: int,
    agent_count: int,
    simulation_mode: str,
    speakers_per_round: int,
    fidelity_tiers: list[int],
    llm_provider: str,
    profile_resolution: RunProfileResolution,
    llm_max_tokens: int,
    round_summary_enabled: bool,
    peer_context_max_chars: int,
    working_memory_last_k: int,
) -> PreflightEstimate:
    """
    Pure preflight estimator: turn counts, rough token/cost envelope, context pressure warnings.
    """
    rounds = max(1, int(total_rounds))
    agents = max(0, int(agent_count))
    per_round = speakers_per_round_count(
        agent_count=agents,
        simulation_mode=simulation_mode,
        speakers_per_round=speakers_per_round,
    )
    total_speaking = rounds * per_round

    tiers = list(fidelity_tiers[:agents]) if fidelity_tiers else [1] * agents
    while len(tiers) < agents:
        tiers.append(1)

    llm_turns = 0
    heuristic_turns = 0
    for r in range(rounds):
        for ti in range(per_round):
            slot = ti if ti < len(tiers) else 1
            tier = tiers[slot] if slot < len(tiers) else 1
            if tier == 3:
                heuristic_turns += 1
            else:
                llm_turns += 1

    policy = routing_policy_from_mode(llm_provider_to_routing_policy(llm_provider))
    anthropic_llm = 0
    openai_compat_llm = 0
    if policy == "frontier_only":
        anthropic_llm = llm_turns
    elif policy == "hybrid_first_turn":
        # One frontier turn per round when first speaker uses LLM (turn_index == 1).
        first_slot_tier = tiers[0] if tiers else 1
        frontier_per_round = 1 if first_slot_tier in (1, 2) else 0
        anthropic_llm = rounds * frontier_per_round
        openai_compat_llm = max(0, llm_turns - anthropic_llm)
    else:
        openai_compat_llm = llm_turns

    avg_out = max(64, min(int(llm_max_tokens), 8192)) // 2
    avg_in = _DEFAULT_AVG_INPUT_TOKENS
    est_in = llm_turns * avg_in
    est_out = llm_turns * avg_out

    local_pricing = profile_resolution.local_profile.pricing_key
    cost = 0.0
    if anthropic_llm > 0:
        cost += anthropic_llm * estimate_cost_usd(
            input_tokens=avg_in,
            output_tokens=avg_out,
            provider_key="anthropic",
        )
    if openai_compat_llm > 0:
        cost += openai_compat_llm * estimate_cost_usd(
            input_tokens=avg_in,
            output_tokens=avg_out,
            provider_key=local_pricing,
        )
    cost = round(cost, 4)

    context_window = _effective_context_window(profile_resolution, llm_provider)
    pressure = _context_pressure_ratio(
        total_rounds=rounds,
        turns_per_round=per_round,
        context_window=context_window,
        round_summary_enabled=round_summary_enabled,
        peer_context_max_chars=peer_context_max_chars,
        working_memory_last_k=working_memory_last_k,
        llm_max_tokens=llm_max_tokens,
    )

    warnings = list(
        _build_warnings(
            profile_resolution=profile_resolution,
            llm_turns=llm_turns,
            context_window=context_window,
            context_pressure_ratio=pressure,
            estimated_cost_usd=cost,
            llm_provider=llm_provider,
        )
    )

    return PreflightEstimate(
        total_speaking_turns=total_speaking,
        llm_turns=llm_turns,
        heuristic_turns=heuristic_turns,
        anthropic_llm_turns=anthropic_llm,
        openai_compatible_llm_turns=openai_compat_llm,
        estimated_input_tokens=est_in,
        estimated_output_tokens=est_out,
        estimated_cost_usd=cost,
        context_window=context_window,
        context_pressure_ratio=pressure,
        warnings=tuple(warnings),
    )


def _effective_context_window(resolution: RunProfileResolution, llm_provider: str) -> int | None:
    mode = (llm_provider or "lmstudio").strip().lower()
    if mode == "hybrid":
        windows = [
            resolution.local_profile.context_window,
            resolution.frontier_profile.context_window,
        ]
        known = [w for w in windows if w is not None]
        return min(known) if known else None
    if mode == "anthropic":
        return resolution.frontier_profile.context_window
    return resolution.local_profile.context_window


def _context_pressure_ratio(
    *,
    total_rounds: int,
    turns_per_round: int,
    context_window: int | None,
    round_summary_enabled: bool,
    peer_context_max_chars: int,
    working_memory_last_k: int,
    llm_max_tokens: int,
) -> float | None:
    if context_window is None or context_window <= 0:
        return None
    base = 900 + (working_memory_last_k * max(200, peer_context_max_chars // 3))
    if round_summary_enabled:
        base += 400
    growth_per_prior_turn = max(150, peer_context_max_chars // 6)
    prior_turns = max(0, (total_rounds - 1) * turns_per_round)
    peak_estimate = base + prior_turns * growth_per_prior_turn + min(llm_max_tokens, 2048)
    return round(peak_estimate / float(context_window), 4)


def _build_warnings(
    *,
    profile_resolution: RunProfileResolution,
    llm_turns: int,
    context_window: int | None,
    context_pressure_ratio: float | None,
    estimated_cost_usd: float,
    llm_provider: str,
) -> list[str]:
    warnings: list[str] = []
    primary: ModelProfile = profile_resolution.primary_profile

    if llm_turns > 0 and context_window is None:
        warnings.append(
            "preflight: model context window is unknown — context pressure cannot be estimated; "
            "use a profile with a known window or fewer rounds if outputs truncate."
        )

    if context_pressure_ratio is not None and context_pressure_ratio >= 0.75:
        pct = int(round(context_pressure_ratio * 100))
        warnings.append(
            f"preflight: estimated context pressure is high (~{pct}% of model window) — "
            "consider fewer rounds, fewer speakers per round, or a larger-context model."
        )

    if llm_turns > 0 and not primary.capabilities.supports_usage:
        warnings.append(
            "preflight: selected profile may not report token usage — cost and economics totals may be incomplete."
        )

    if estimated_cost_usd > 0:
        warnings.append(
            f"preflight: estimated run cost envelope ~${estimated_cost_usd:.2f} "
            f"({llm_provider} routing; list-price defaults, not a hard cap)."
        )
    elif llm_turns > 0 and (llm_provider or "").strip().lower() == "lmstudio":
        pass  # local-only $0 is expected

    return warnings

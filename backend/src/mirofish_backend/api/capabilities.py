"""Runtime capability surface for agents and tools (Iteration 16)."""

from __future__ import annotations

from enum import Enum

from fastapi import APIRouter

from mirofish_backend.api.simulations import (
    LLM_PROVIDER_VALUES,
    POPULATION_SAMPLE_MODE_VALUES,
    SIMULATION_MODE_VALUES,
)
from mirofish_backend.export_bundle import EXPORT_VERSION
from mirofish_backend.simulation.economics import PRICE_MAP_DATE
from mirofish_backend.population.csv_population import POPULATION_SCHEMA_VERSION
from mirofish_backend.scenarios.validate import list_allowed_corpus_paths
from mirofish_backend.simulation.agent_context import AGENT_CONTEXT_VERSION
from mirofish_backend.simulation.interaction_policy import (
    INTERACTION_POLICY_VERSION,
    ChannelType,
    InteractionOverlay,
    TurnOrderPolicy,
    VisibilityPolicy,
)
from mirofish_backend.simulation.sampling_strategy import SAMPLING_STRATEGY_VALUES

router = APIRouter(tags=["capabilities"])


def _enum_values(e: type[Enum]) -> list[str]:
    return sorted(m.value for m in e)


def build_capabilities_dict() -> dict:
    """
    Same payload as GET /capabilities — used by the agent orchestrator (Iteration 17) without HTTP.
    """
    return {
        "export_version": EXPORT_VERSION,
        "agent_context_version": AGENT_CONTEXT_VERSION,
        "population_schema_version": POPULATION_SCHEMA_VERSION,
        "interaction_policy_version": INTERACTION_POLICY_VERSION,
        "interaction_policy": {
            "channel_types": _enum_values(ChannelType),
            "turn_order_policies": _enum_values(TurnOrderPolicy),
            # Omit legacy "full" — API still accepts it; normalized to broadcast (ADR-002).
            "visibility_policies": sorted(
                v for v in _enum_values(VisibilityPolicy) if v != "full"
            ),
            "interaction_overlays": _enum_values(InteractionOverlay),
        },
        "simulation_run": {
            "simulation_modes": sorted(SIMULATION_MODE_VALUES),
            "population_sample_modes": sorted(POPULATION_SAMPLE_MODE_VALUES),
            "llm_providers": sorted(LLM_PROVIDER_VALUES),
            "llm_concurrency_cap": {"default": 4, "min": 1, "max": 16},
            "agent_limit": {"default": 3, "min": 1, "max": 300},
            "speakers_per_round": {"default": 2, "min": 1, "max": 300},
            "aggregation_threshold": {"default": 20, "min": 1, "max": 300},
            "sampling_strategies": sorted(SAMPLING_STRATEGY_VALUES),
            "implementation_posture": {
                "optional": True,
                "description": "Opaque string on scenario personas, roster CSV, or population CSV; used by posture_maxvar to pick Tier-1 diversity across distinct non-empty tags (Iteration 26).",
            },
            "fidelity_tiers": {
                "description": "Optional roster column fidelity_tier (1|2|3) overrides strategy-assigned tier per slot; default Tier 1.",
                "min": 1,
                "max": 3,
            },
            "remainder_config": {
                "optional": True,
                "description": "Iteration 24: synthetic Tier-3 remainder cohort + heuristic tuning. "
                "Fields: remainder_count (< agent_limit), tier_3_dampening, tier_3_noise_std, "
                "initial_support_distribution, initial_resistance_distribution, initial_workload_stress_distribution "
                "(each {mean, std} for Gaussian draw clamped to [0,1]).",
            },
            "network_csv": {
                "optional": True,
                "max_chars": 500000,
                "description": "Iteration 25: source_agent_id,target_agent_id,influence_weight (0–1). "
                "Ids use persona_id_NNN (e.g. principal_001_000); use sampling_audit.per_agent[].agent_id for exact "
                "run ids. Required for sampling_strategy=network_centrality. Unknown endpoints → warnings.",
            },
            "convergence_threshold": {
                "optional": True,
                "min": 0.0,
                "max": 1.0,
                "description": "Iteration 28: omit to run full total_rounds; when set, mean population abs attitude "
                "change (support/resistance/workload) below this for convergence_patience consecutive rounds stops the run.",
            },
            "convergence_patience": {
                "default": 2,
                "min": 1,
                "max": 25,
                "description": "Iteration 28: consecutive sub-threshold rounds required; only used when convergence_threshold is set.",
            },
            "economics": {
                "description": "Iteration 29: GET /simulations/{id} and export include token totals, tier turn counts, "
                "and estimated_cost_usd from per-turn usage. Anthropic-priced turns use list defaults (pricing snapshot "
                f"{PRICE_MAP_DATE}; override via ANTHROPIC_INPUT_PRICE_PER_MTOK / ANTHROPIC_OUTPUT_PRICE_PER_MTOK); "
                "lmstudio/heuristic turns are $0.",
            },
        },
        "persona_attribute_sections": ["identity", "attitudes", "personal_history"],
        "bundled_rag_paths": list_allowed_corpus_paths(),
        "experiments": {
            "description": "Iteration 27: multi-run experiment records; shared scenario_id and random_seed; "
            "runs execute sequentially via POST /simulations/run. Iteration 28+: optional convergence_threshold "
            "and convergence_patience on POST /experiments (same values for all child runs). Iteration 29: "
            "GET /experiments/{id} includes per-run economics, total_estimated_cost_usd, and comparison.csv token/cost columns.",
            "max_runs_per_experiment": 16,
            "experiment_statuses": sorted(["pending", "running", "completed", "failed"]),
            "endpoints": {
                "create": "POST /experiments",
                "list": "GET /experiments",
                "detail": "GET /experiments/{experiment_id}",
                "export_json": "GET /experiments/{experiment_id}/export.json",
                "export_zip": "GET /experiments/{experiment_id}/export.zip",
            },
        },
    }


@router.get("/capabilities")
async def get_capabilities() -> dict:
    """
    Structured parameter space derived from code (enums + shared constants).

    **bundled_rag_paths** is resolved from ``scenarios/data`` on the server filesystem at request
    time; it may be empty in stripped installs and differs by deployment. Cross-environment
    contract tests should not assert an exact path list.
    """
    return build_capabilities_dict()

"""Synthetic remainder personas (Iteration 24) — no YAML; Tier-3 cohort with sampled initial state."""

from __future__ import annotations

import random

from mirofish_backend.scenarios.registry import PersonaTemplate, ScenarioConfig

SYNTHETIC_REMAINDER_PREFIX = "synthetic_remainder_"


def is_synthetic_remainder_persona(persona: PersonaTemplate) -> bool:
    return persona.persona_id.startswith(SYNTHETIC_REMAINDER_PREFIX)


def _clamp01(x: float) -> float:
    return max(0.0, min(1.0, x))


def build_synthetic_remainder_personas(
    scenario: ScenarioConfig,
    count: int,
    *,
    random_seed: int,
    support_mean: float = 0.52,
    support_std: float = 0.1,
    resistance_mean: float = 0.35,
    resistance_std: float = 0.1,
    workload_mean: float = 0.6,
    workload_std: float = 0.08,
) -> list[PersonaTemplate]:
    if count <= 0:
        return []
    max_rl = max(p.role_level for p in scenario.personas) if scenario.personas else 1
    syn_rl = max_rl + 1
    out: list[PersonaTemplate] = []
    for j in range(count):
        mix = (random_seed & 0xFFFFFFFF) ^ (j * 0x9E3779B9) ^ 0x524D_0000
        rng = random.Random(mix)
        support = _clamp01(rng.gauss(support_mean, support_std))
        resistance = _clamp01(rng.gauss(resistance_mean, resistance_std))
        workload = _clamp01(rng.gauss(workload_mean, workload_std))
        pid = f"{SYNTHETIC_REMAINDER_PREFIX}{j:04d}"
        out.append(
            PersonaTemplate(
                persona_id=pid,
                role="remainder",
                name=f"Remainder {j + 1}",
                role_level=syn_rl,
                style_cues="Generic stakeholder; minimal voice in Tier-3 heuristic cohort.",
                beliefs={"policy_exposure": 0.5},
                initial_state={
                    "support_level": support,
                    "resistance_level": resistance,
                    "workload_stress": workload,
                    "belief_posture": "neutral",
                },
            )
        )
    return out

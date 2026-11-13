"""Version-controlled prompts for agent reflection synthesis (senna-iter-51)."""

from __future__ import annotations

import json
from typing import Any

REFLECTION_PROMPT_VERSION = "v1"


def build_reflection_prompt(
    *,
    prompt_version: str,
    agent_name: str,
    agent_role: str,
    round_number: int,
    observations: list[dict[str, Any]],
) -> tuple[str, str]:
    """Return (system, user) for synthesising a reflection from accumulated observations."""
    system = (
        "You are a reflection synthesiser for a multi-agent simulation. "
        "Given several of an agent's recent observation utterances, produce one short "
        "higher-level statement about what they learned or inferred — not a replay of persona facts. "
        f"Prompt version: {prompt_version}."
    )
    lines = [
        f"Agent: {agent_name} ({agent_role})",
        f"Round {round_number} — synthesise from these observations:",
        "",
    ]
    for obs in observations:
        lines.append(
            f"- turn_id={obs['turn_id']} | round={obs.get('round_number')} "
            f"importance={obs.get('importance_score')}"
        )
        lines.append(f"  utterance: {(obs.get('raw_response') or '').strip()[:1500]}")
        lines.append("")
    example = {
        "reflection_text": "Short synthesised insight grounded in the observations.",
        "source_turn_ids": [observations[0]["turn_id"]] if observations else [],
    }
    lines.extend(
        [
            "Respond with exactly one block:",
            "<reflection>",
            json.dumps(example, indent=2),
            "</reflection>",
            "List every source turn_id you used in source_turn_ids.",
        ]
    )
    return system, "\n".join(lines)

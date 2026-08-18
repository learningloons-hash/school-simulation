"""Round-end Likert self-report helpers (senna-iter-40)."""

from __future__ import annotations

import json
import re
from typing import Any

from mirofish_backend.llm.likert_parse import LIKERT_ORDINAL_FLOAT_MAP
from mirofish_backend.scenarios.registry import PersonaTemplate, ScenarioConfig

INDICATOR_FLOAT_KEYS: dict[str, str] = {
    "support": "support_level",
    "resistance": "resistance_level",
    "workload_stress": "workload_stress",
}

DEFAULT_LIKERT_INDICATORS: tuple[str, ...] = ("support", "resistance", "workload_stress")

_LIKERT_HISTORY_MAX_CHARS = 8000
_STATE_BLOCK = re.compile(r"<state>.*?</state>", re.DOTALL | re.IGNORECASE)


def parse_anchor_labels(raw: Any) -> dict[str, tuple[str, ...]]:
    if not isinstance(raw, dict):
        return {}
    out: dict[str, tuple[str, ...]] = {}
    for key, labels in raw.items():
        if not isinstance(labels, list) or len(labels) != 6:
            continue
        out[str(key)] = tuple(str(x) for x in labels)
    return out


def resolve_likert_anchor_labels(
    scenario: ScenarioConfig,
    persona: PersonaTemplate,
) -> dict[str, tuple[str, ...]]:
    merged = dict(scenario.likert_anchor_labels)
    merged.update(parse_anchor_labels(getattr(persona, "likert_anchor_labels", None) or {}))
    return merged


def resolve_likert_indicators(anchor_labels: dict[str, tuple[str, ...]]) -> tuple[str, ...]:
    if anchor_labels:
        valid = [k for k, v in anchor_labels.items() if len(v) == 6]
        if valid:
            return tuple(sorted(valid))
    return DEFAULT_LIKERT_INDICATORS


def resolve_likert_enabled(*, request_flag: bool | None, scenario: ScenarioConfig) -> bool:
    if request_flag is not None:
        return request_flag
    return bool(scenario.likert_self_report_enabled)


def float_value_for_indicator(indicator: str, state: Any) -> float | None:
    key = INDICATOR_FLOAT_KEYS.get(indicator, indicator)
    val = getattr(state, key, None)
    if val is None and isinstance(state, dict):
        val = state.get(key)
    if val is None:
        return None
    try:
        return float(val)
    except (TypeError, ValueError):
        return None


def _strip_state_block(text: str) -> str:
    return _STATE_BLOCK.sub("", text or "").strip()


def format_likert_visible_history(
    visible_turns: list[dict[str, Any]],
    *,
    agent_id: str,
    max_chars: int = _LIKERT_HISTORY_MAX_CHARS,
) -> str:
    """Format agent-visible spoken history without prompts or internal state tags."""
    lines: list[str] = []
    for turn in visible_turns:
        rnd = int(turn.get("round_number") or 0)
        speaker = str(turn.get("agent_name") or turn.get("agent_id") or "unknown")
        role = str(turn.get("agent_role") or "")
        is_self = str(turn.get("agent_id")) == agent_id
        label = "You" if is_self else speaker
        response = _strip_state_block(str(turn.get("raw_response") or "")).strip()
        if not response:
            continue
        role_bit = f" ({role})" if role and not is_self else ""
        lines.append(f"Round {rnd} — {label}{role_bit}: {response}")

    if not lines:
        return (
            "Discussion history visible to you under the school's interaction policy: "
            "(no prior spoken turns were visible at this round boundary.)"
        )

    body = "\n".join(lines)
    if len(body) <= max_chars:
        header = (
            "Discussion history visible to you (your turns and peers you could observe "
            "under the school's interaction policy):"
        )
        return f"{header}\n\n{body}"

    trimmed = body[-max_chars:]
    cut = trimmed.find("\n")
    if cut > 0:
        trimmed = trimmed[cut + 1:]
    header = (
        "Discussion history visible to you (truncated; most recent visible turns retained):"
    )
    return f"{header}\n\n{trimmed}"


def build_likert_actor_system_prompt(
    *,
    scenario_id: str,
    persona: PersonaTemplate,
    agent_name: str,
    agent_role: str,
    demographics: dict[str, Any] | None,
    prompt_version: str,
) -> str:
    """Persona grounding for Likert self-report — no float state (independently measured)."""
    demo = demographics or {}
    demo_bits = [
        f"{k}: {v}"
        for k, v in demo.items()
        if v is not None and str(v).strip()
    ]
    demo_block = "\n".join(f"- {b}" for b in demo_bits) if demo_bits else "- (not specified)"
    return (
        f"You are {agent_name}, acting as a {agent_role} in scenario '{scenario_id}'.\n"
        f"Prompt version: {prompt_version}.\n\n"
        "Role and stance (use this voice for your self-report):\n"
        f"- Style cues: {persona.style_cues}\n"
        f"- Beliefs / policy position: {persona.beliefs}\n\n"
        "Demographics:\n"
        f"{demo_block}\n\n"
        "You are completing a structured round-end self-report grounded in what you "
        "experienced in the discussion so far. Respond only with the requested JSON inside "
        "a <likert>...</likert> block. Use the exact anchor label text for each indicator — "
        "no numbers or scale positions."
    )


def build_likert_self_report_prompt(
    *,
    round_number: int,
    scenario_id: str,
    persona: PersonaTemplate,
    agent_name: str,
    agent_role: str,
    demographics: dict[str, Any] | None,
    prompt_version: str,
    indicators: tuple[str, ...],
    anchor_labels: dict[str, tuple[str, ...]],
    visible_history: str | None = None,
) -> tuple[str, str]:
    lines: list[str] = []
    for ind in indicators:
        anchors = anchor_labels.get(ind)
        if not anchors or len(anchors) != 6:
            continue
        numbered = "; ".join(f'"{a}"' for a in anchors)
        lines.append(f"- {ind}: choose exactly one of [{numbered}]")

    indicator_block = "\n".join(lines)
    system = build_likert_actor_system_prompt(
        scenario_id=scenario_id,
        persona=persona,
        agent_name=agent_name,
        agent_role=agent_role,
        demographics=demographics,
        prompt_version=prompt_version,
    )
    example = {
        ind: anchor_labels[ind][2]
        for ind in indicators
        if ind in anchor_labels and len(anchor_labels[ind]) == 6
    }
    user_parts = [
        f"Round {round_number} has ended. Reflect on the discussion history below and "
        f"report your current stance on each indicator using exactly one anchor label per item:\n",
    ]
    if visible_history:
        user_parts.append(visible_history.strip())
        user_parts.append("")
    user_parts.extend(
        [
            indicator_block,
            "",
            "Append a single block:",
            "<likert>",
            json.dumps(example, indent=2),
            "</likert>",
            "Replace each value with your chosen anchor label text (not the example ordinal).",
        ]
    )
    user = "\n".join(user_parts)
    return system, user


def likert_config_snapshot_fields(
    *,
    enabled: bool,
    anchor_labels: dict[str, tuple[str, ...]],
    indicators: tuple[str, ...],
) -> dict[str, Any]:
    return {
        "likert_self_report_enabled": enabled,
        "likert_ordinal_float_mapping": list(LIKERT_ORDINAL_FLOAT_MAP),
        "likert_indicators": list(indicators),
        "likert_anchor_labels": {k: list(v) for k, v in anchor_labels.items()},
    }


def compute_divergence(float_value: float | None, mapped_float: float) -> float | None:
    if float_value is None:
        return None
    return round(abs(float(float_value) - mapped_float), 6)

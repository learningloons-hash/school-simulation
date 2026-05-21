from typing import Any, cast


def _profile_lines(title: str, profile: dict[str, Any]) -> str:
    if not profile:
        return ""
    lines = [f"{title}:"]
    for k, v in sorted(profile.items(), key=lambda kv: str(kv[0])):
        lines.append(f"- {k}: {v}")
    return "\n".join(lines) + "\n\n"


def build_system_prompt(
    *,
    scenario_id: str,
    role: str,
    name: str,
    style_cues: str,
    beliefs: dict[str, Any],
    demographics: dict[str, Any],
    state: dict[str, Any],
    prompt_version: str,
    psychological_profile: dict[str, Any] | None = None,
    implementation_profile: dict[str, Any] | None = None,
    group_affiliations: tuple[str, ...] = (),
    identity: dict[str, Any] | None = None,
    attitudes: dict[str, Any] | None = None,
    personal_history: dict[str, Any] | None = None,
) -> str:
    psych = _profile_lines("Psychological profile (simulation)", psychological_profile or {})
    impl = _profile_lines("Implementation profile (simulation)", implementation_profile or {})
    id_block = _profile_lines("Identity (structured attributes)", identity or {})
    att_block = _profile_lines("Attitudes / stance (structured)", attitudes or {})
    hist_block = _profile_lines("Personal history (structured)", personal_history or {})
    group_line = (
        f"- Group / cohort affiliations (in-character): {', '.join(group_affiliations)}\n"
        if group_affiliations
        else ""
    )
    return (
        f"You are {name}, acting as a {role} in scenario '{scenario_id}'.\n"
        f"Prompt version: {prompt_version}.\n\n"
        "Persona identity and stance:\n"
        f"- Style cues: {style_cues}\n"
        f"- Beliefs: {beliefs}\n"
        f"- Demographics: {demographics}\n"
        f"{group_line}\n"
        f"{id_block}"
        f"{att_block}"
        f"{hist_block}"
        f"{psych}"
        f"{impl}"
        "Current internal state:\n"
        f"- Support level: {state['support_level']:.2f}\n"
        f"- Resistance level: {state['resistance_level']:.2f}\n"
        f"- Workload stress: {state['workload_stress']:.2f}\n"
        f"- Belief posture: {state['belief_posture']}\n\n"
        "Stay in character. Use concise, policy-relevant language grounded in your role."
    )


def simplified_persona_prompt(
    *,
    scenario_id: str,
    role: str,
    name: str,
    style_cues: str,
    beliefs: dict[str, Any],
    state: dict[str, Any],
    prompt_version: str,
) -> str:
    """Iteration 23 Tier-2 system prompt: role + stance + state only (no deep persona blocks)."""
    return (
        f"You are {name}, acting as a {role} in scenario '{scenario_id}'.\n"
        f"Prompt version: {prompt_version}.\n"
        "Fidelity: Tier 2 (simplified persona — structural participation; omit deep biography).\n\n"
        "Position and stance:\n"
        f"- Style cues: {style_cues}\n"
        f"- Beliefs / policy position: {beliefs}\n\n"
        "Current internal state:\n"
        f"- Support level: {state['support_level']:.2f}\n"
        f"- Resistance level: {state['resistance_level']:.2f}\n"
        f"- Workload stress: {state['workload_stress']:.2f}\n"
        f"- Belief posture: {state['belief_posture']}\n\n"
        "Stay in character. Use concise, policy-relevant language grounded in your role."
    )


def _format_peer_line(item: dict[str, Any]) -> str:
    r = cast(int, item["round_number"])
    t = cast(int, item["turn_index"])
    name = cast(str, item["agent_name"])
    it = cast(str, item["interaction_type"])
    tgt = cast(str, item["target_agent_name"])
    body = cast(str, item["raw_response"])
    return f"- [Round {r}, turn {t}] {name} [{it} to {tgt}] -> {body}"


def build_user_prompt(
    *,
    round_number: int,
    policy_event: str,
    interaction_type: str,
    target_scope: str,
    target_agent_name: str | None,
    intent_tag: str,
    prior_agent_memory: list[str],
    recent_interactions: list[dict[str, Any]],
    context_snippets: list[dict[str, Any]] | None = None,
    round_summaries: list[str] | None = None,
) -> str:
    memory_block = "\n".join([f"- {m}" for m in prior_agent_memory]) if prior_agent_memory else "- (none)"
    interaction_block = (
        "\n".join([_format_peer_line(item) for item in recent_interactions])
        if recent_interactions
        else "- (none)"
    )
    target_name = target_agent_name or "all stakeholders"
    rag_block = ""
    if context_snippets:
        lines: list[str] = []
        for i, item in enumerate(context_snippets, start=1):
            src = str(item.get("source", "corpus"))
            body = str(item.get("text", "")).strip()
            score = item.get("score")
            score_s = f"{float(score):.4f}" if isinstance(score, int | float) else str(score)
            lines.append(f"{i}. [{src}] (similarity {score_s})\n{body}")
        rag_block = (
            "\nReference excerpts (retrieved policy corpus; cite sparingly, stay in character):\n"
            + "\n\n".join(lines)
            + "\n\n"
        )
    evolution_note = ""
    if round_number > 1:
        evolution_note = (
            "\nEarlier simulation rounds have already occurred. The lines below include prior rounds "
            "(see [Round …, turn …]). Build on that shared history—do not repeat your own earlier "
            "message verbatim unless the new policy event explicitly requires a restatement.\n"
        )
    summaries_block = ""
    if round_summaries:
        joined = "\n\n".join(round_summaries)
        summaries_block = (
            "Prior rounds — compact summaries (all agents, structured):\n"
            f"{joined}\n\n"
        )
    peer_heading = (
        "Current round — what others have said so far (excludes your current line):\n"
        if round_summaries
        else "What others have said (chronological in this window; excludes your current line):\n"
    )
    return (
        f"Round: {round_number}\n"
        f"Policy event: {policy_event}\n"
        f"{rag_block}"
        f"{evolution_note}\n"
        f"{summaries_block}"
        "Interaction task:\n"
        f"- Type: {interaction_type}\n"
        f"- Target scope: {target_scope}\n"
        f"- Target: {target_name}\n"
        f"- Intent: {intent_tag}\n\n"
        "Working memory (your own prior lines in this simulation):\n"
        f"{memory_block}\n\n"
        f"{peer_heading}"
        f"{interaction_block}\n\n"
        "Write one policy-relevant message as this agent.\n"
        "Output style: 3-6 concise sentences only. Do not print "
        "\"Thinking Process\", numbered analysis steps, or meta commentary—only the in-character text, "
        "then the <state> block.\n\n"
        "After your message, append a machine-readable state block exactly in this form:\n"
        "<state>\n"
        '{"support_level": <0-1 float>, "resistance_level": <0-1 float>, '
        '"workload_stress": <0-1 float>, "belief_posture": "<short label>", '
        '"perceived_conflict": <true|false>}\n'
        "</state>\n"
        "Use honest self-assessment of your stance after this round; keep numbers in [0,1]."
    )

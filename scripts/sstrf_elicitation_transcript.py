"""Transcript context for SSTRF elicitation (network-bounded visibility)."""

from __future__ import annotations

import os
import re
import types
from typing import Any

from mirofish_backend.simulation.interaction_policy import (
    VisibilityPolicy,
    build_interaction_policy,
    visible_turns_for_agent,
)
from mirofish_backend.simulation.network import parse_network_csv, undirected_neighbor_map

DEFAULT_TRANSCRIPT_MAX_CHARS = int(
    os.environ.get("SSTRF_ELICITATION_TRANSCRIPT_MAX_CHARS", "120000")
)


def _strip_state_block(text: str) -> str:
    return re.sub(r"<state>.*?</state>", "", text, flags=re.DOTALL | re.IGNORECASE).strip()


def _turn_order_policy(cfg: dict[str, Any]) -> str:
    ip = cfg.get("interaction_policy")
    if isinstance(ip, dict) and ip.get("turn_order_policy"):
        return str(ip["turn_order_policy"])
    return str(cfg.get("turn_order_policy") or "round_robin")


def _agent_observer(agent_id: str, group_ids: frozenset[str]) -> Any:
    return types.SimpleNamespace(
        agent_id=agent_id,
        context=types.SimpleNamespace(group_ids=tuple(group_ids)),
    )


def _network_neighbors_from_bundle(bundle: dict[str, Any]) -> dict[str, frozenset[str]] | None:
    cfg = (bundle.get("run") or {}).get("config_snapshot") or {}
    network_csv = (cfg.get("network_csv") or "").strip()
    if not network_csv:
        return None
    agent_ids = frozenset(
        str(s.get("agent_id"))
        for s in (bundle.get("agent_state_snapshots") or [])
        if s.get("agent_id")
    )
    if not agent_ids:
        return None
    parsed = parse_network_csv(network_csv, known_agent_ids=agent_ids)
    return undirected_neighbor_map(agent_ids, parsed.edges)


def _effective_visibility(
    cfg: dict[str, Any],
    network_neighbors: dict[str, frozenset[str]] | None,
) -> VisibilityPolicy:
    vis_raw = str(cfg.get("visibility_policy") or "broadcast").strip().lower()
    if vis_raw == "full":
        vis_raw = "broadcast"
    if vis_raw == "network_bounded":
        if not network_neighbors or not cfg.get("network_csv_applied"):
            return VisibilityPolicy.BROADCAST
        return VisibilityPolicy.NETWORK_BOUNDED
    return VisibilityPolicy(vis_raw)


def visible_transcript_for_agent(
    *,
    bundle: dict[str, Any],
    agent_id: str,
    group_ids: frozenset[str],
) -> list[dict[str, Any]]:
    transcript = list(bundle.get("transcript") or [])
    if not transcript:
        return []
    cfg = (bundle.get("run") or {}).get("config_snapshot") or {}
    policy = build_interaction_policy(
        turn_order_policy=_turn_order_policy(cfg),
        visibility_policy=str(cfg.get("visibility_policy") or "broadcast"),
        interaction_overlay=str(cfg.get("interaction_overlay") or "none"),
    )
    neighbors = _network_neighbors_from_bundle(bundle)
    effective_visibility = _effective_visibility(cfg, neighbors)
    observer = _agent_observer(agent_id, group_ids)
    return visible_turns_for_agent(
        transcript,
        observer,
        policy,
        effective_visibility=effective_visibility,
        network_neighbors=neighbors,
    )


def _format_turn_line(turn: dict[str, Any], *, agent_id: str) -> str:
    rnd = int(turn.get("round_number") or 0)
    speaker = str(turn.get("agent_name") or turn.get("agent_id") or "unknown")
    role = str(turn.get("agent_role") or "")
    is_self = str(turn.get("agent_id")) == agent_id
    label = "You" if is_self else speaker
    response = _strip_state_block(str(turn.get("raw_response") or "")).strip()
    if not response:
        response = "(no spoken response recorded)"
    role_bit = f" ({role})" if role and not is_self else ""
    return f"Round {rnd} — {label}{role_bit}: {response}"


def _compress_visible_turns(
    visible: list[dict[str, Any]],
    *,
    agent_id: str,
    max_chars: int,
) -> str:
    by_round: dict[int, list[str]] = {}
    for turn in visible:
        rnd = int(turn.get("round_number") or 0)
        by_round.setdefault(rnd, []).append(_format_turn_line(turn, agent_id=agent_id))
    lines: list[str] = []
    for rnd in sorted(by_round):
        chunk = " | ".join(by_round[rnd])
        if len(chunk) > 400:
            chunk = chunk[:397] + "..."
        lines.append(f"Round {rnd} summary: {chunk}")
    body = "\n".join(lines)
    if len(body) <= max_chars:
        return body
    while lines and len("\n".join(lines)) > max_chars:
        lines.pop(0)
    body = "\n".join(lines)
    if len(body) > max_chars:
        return body[: max_chars - 3] + "..."
    return body


def _total_rounds_from_bundle(bundle: dict[str, Any]) -> int:
    run = bundle.get("run") or {}
    for key in ("total_rounds", "current_round"):
        val = run.get(key)
        if val is not None:
            try:
                n = int(val)
                if n > 0:
                    return n
            except (TypeError, ValueError):
                pass
    transcript = bundle.get("transcript") or []
    if transcript:
        return max(int(t.get("round_number") or 0) for t in transcript)
    return 0


def build_transcript_context_block(
    *,
    bundle: dict[str, Any],
    agent_id: str,
    group_ids: frozenset[str],
    max_chars: int = DEFAULT_TRANSCRIPT_MAX_CHARS,
) -> str:
    visible = visible_transcript_for_agent(
        bundle=bundle,
        agent_id=agent_id,
        group_ids=group_ids,
    )
    total_rounds = _total_rounds_from_bundle(bundle)
    rounds_label = f"all {total_rounds} rounds" if total_rounds else "all rounds"
    if not visible:
        return (
            "Simulation history visible to you: (no transcript rows matched the "
            "network-bounded visibility policy for this agent.)"
        )
    full_lines = [_format_turn_line(t, agent_id=agent_id) for t in visible]
    full_text = "\n".join(full_lines)
    if len(full_text) <= max_chars:
        header = (
            f"Simulation history visible to you across {rounds_label} "
            "(your turns and peers you could observe under the school's network policy):"
        )
        return f"{header}\n\n{full_text}"
    compressed = _compress_visible_turns(visible, agent_id=agent_id, max_chars=max_chars)
    header = (
        "Simulation history visible to you (per-round compressed summary; full transcript "
        "exceeded the elicitation context budget):"
    )
    return f"{header}\n\n{compressed}"

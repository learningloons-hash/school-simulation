"""
Incremental Markdown transcript writer.

One file per simulation: {transcript_dir}/{simulation_id}.md
Written round-by-round so a partial transcript survives a crash mid-run.
Contains full untruncated agent text — the durable research record.
"""

from __future__ import annotations

import os
import re
from datetime import datetime, timezone

_STATE_WRAPPER = re.compile(r"<state>\s*[\s\S]*?\s*</state>", re.IGNORECASE)


def _strip_state(text: str) -> str:
    return _STATE_WRAPPER.sub("", text or "").strip()


def _transcript_path(transcript_dir: str, simulation_id: str) -> str:
    return os.path.join(transcript_dir, f"{simulation_id}.md")


async def open_transcript(
    transcript_dir: str,
    *,
    simulation_id: str,
    scenario_id: str,
    agent_names: list[tuple[str, str]],  # [(name, role), ...]
    total_rounds: int,
    model_used: str,
) -> str:
    """Write simulation header. Returns the transcript path."""
    os.makedirs(transcript_dir, exist_ok=True)
    path = _transcript_path(transcript_dir, simulation_id)
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    roster = "\n".join(f"| {n} | {r} |" for n, r in agent_names)
    header = (
        f"# Senna Simulation Transcript\n\n"
        f"**Simulation ID:** `{simulation_id}`  \n"
        f"**Scenario:** `{scenario_id}`  \n"
        f"**Agents:** {len(agent_names)} | **Rounds planned:** {total_rounds}  \n"
        f"**Started:** {now}  \n"
        f"**Model:** `{model_used}`\n\n"
        f"## Agent Roster\n\n"
        f"| Name | Role |\n"
        f"|------|------|\n"
        f"{roster}\n\n"
        f"---\n\n"
    )
    with open(path, "w", encoding="utf-8") as f:
        f.write(header)
    return path


async def append_round_to_transcript(
    transcript_dir: str,
    *,
    simulation_id: str,
    round_number: int,
    policy_event: str,
    turns: list[dict],
    round_summary: str,
) -> None:
    """Append one round's full turns + compact summary to the transcript file."""
    path = _transcript_path(transcript_dir, simulation_id)
    lines = [f"## Round {round_number} — {policy_event}\n"]
    for turn in turns:
        name = turn.get("agent_name", "?")
        role = turn.get("agent_role", "?")
        raw = turn.get("raw_response", "")
        clean = _strip_state(raw)
        lines.append(f"**{name}** *({role})*\n\n> {clean}\n")
    lines.append(f"### Round {round_number} Summary\n\n```\n{round_summary}\n```\n\n---\n\n")
    with open(path, "a", encoding="utf-8") as f:
        f.write("\n".join(lines))


async def close_transcript(
    transcript_dir: str,
    *,
    simulation_id: str,
    completed_rounds: int,
    status: str,
) -> None:
    """Append a footer when the simulation ends."""
    path = _transcript_path(transcript_dir, simulation_id)
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    footer = (
        f"## Simulation Complete\n\n"
        f"**Status:** {status}  \n"
        f"**Rounds completed:** {completed_rounds}  \n"
        f"**Ended:** {now}\n"
    )
    with open(path, "a", encoding="utf-8") as f:
        f.write(footer)

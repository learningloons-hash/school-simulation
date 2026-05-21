# HANDOFF_SENNA_ARC6 — Context Bounding & Simulation Transcripts

**Owner:** Claude → Cursor Architect → Cursor Builder  
**Branch base:** main (all Arc 5 work merged)  
**Goal:** Keep per-call LLM prompt size O(1) across any number of rounds; write a durable `.md` transcript per simulation for research review.  
**Scope:** Backend only — no frontend changes.

---

## Motivation

With the default `interaction_last_k` formula (`len(agents) × (round_number − 1)`, capped 120), a 4-agent 15-round simulation sends up to 56 peer turns of raw text in round 15 prompts. Combined with the local LLM's constrained VRAM budget (n_ctx set to 8 192 in LM Studio), this causes OOM failures after ~2 runs.

**Solution:** after each round closes, build a compact deterministic summary (no extra LLM call) and store it in the DB. Subsequent rounds inject prior-round summaries (~120 tokens each) instead of raw turns. Full untruncated text is written to a per-simulation `.md` transcript for research use.

---

## Design constants (reference for all iterations)

| Symbol | Value | Notes |
|--------|-------|-------|
| `INTERACTION_LAST_K_CAP` | `12` | Replaces `120`; bounds current-round peer context |
| `SNIPPET_CHARS` | `80` | Opening chars of each agent turn in summary |
| `SUMMARY_MAX_TOKENS` | ~120 per round | Estimated; 14 prior rounds ≈ 1 680 tokens |
| Transcript dir | `./data/transcripts/` | Configurable via `transcript_dir` in `config.py` |

---

## senna-iter-26 — DB schema + round summary builder

### `db/schema.py`

Add new table inside `init_db()`, after the `round_outcomes` table block:

```python
await db.execute(
    """
    CREATE TABLE IF NOT EXISTS round_summaries (
      simulation_id TEXT NOT NULL,
      round_number  INTEGER NOT NULL,
      summary_text  TEXT NOT NULL,
      created_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
      PRIMARY KEY (simulation_id, round_number)
    );
    """
)
```

No `_ensure_column` migration needed — `CREATE TABLE IF NOT EXISTS` handles new and existing DBs.

### `db/repo.py`

Add three new async functions (append after existing repo functions):

```python
async def upsert_round_summary(
    sqlite_path: str,
    *,
    simulation_id: str,
    round_number: int,
    summary_text: str,
) -> None:
    async with aiosqlite.connect(sqlite_path) as db:
        await db.execute(
            """
            INSERT INTO round_summaries (simulation_id, round_number, summary_text)
            VALUES (?, ?, ?)
            ON CONFLICT (simulation_id, round_number) DO UPDATE SET summary_text = excluded.summary_text;
            """,
            (simulation_id, round_number, summary_text),
        )
        await db.commit()


async def get_round_summaries(
    sqlite_path: str,
    *,
    simulation_id: str,
    up_to_round: int | None = None,
) -> list[dict[str, Any]]:
    """Return summaries oldest-first, optionally capped at up_to_round (exclusive)."""
    async with aiosqlite.connect(sqlite_path) as db:
        if up_to_round is not None:
            cursor = await db.execute(
                """
                SELECT round_number, summary_text
                FROM round_summaries
                WHERE simulation_id = ? AND round_number < ?
                ORDER BY round_number ASC;
                """,
                (simulation_id, up_to_round),
            )
        else:
            cursor = await db.execute(
                """
                SELECT round_number, summary_text
                FROM round_summaries
                WHERE simulation_id = ?
                ORDER BY round_number ASC;
                """,
                (simulation_id,),
            )
        rows = await cursor.fetchall()
    return [{"round_number": int(r[0]), "summary_text": str(r[1])} for r in rows]


async def get_turns_for_round(
    sqlite_path: str,
    *,
    simulation_id: str,
    round_number: int,
) -> list[dict[str, Any]]:
    """Return all agent turns for a specific round, ordered by turn_index ascending."""
    async with aiosqlite.connect(sqlite_path) as db:
        cursor = await db.execute(
            """
            SELECT turn_index, agent_id, agent_name, agent_role,
                   interaction_type, target_agent_name, raw_response
            FROM agent_turns
            WHERE simulation_id = ? AND round_number = ?
            ORDER BY turn_index ASC;
            """,
            (simulation_id, round_number),
        )
        rows = await cursor.fetchall()
    return [
        {
            "turn_index": int(r[0]),
            "agent_id": str(r[1]),
            "agent_name": str(r[2]),
            "agent_role": str(r[3]),
            "interaction_type": str(r[4]),
            "target_agent_name": r[5] or "all",
            "raw_response": str(r[6]),
        }
        for r in rows
    ]
```

### `llm/round_summary.py` (new file)

```python
"""
Deterministic per-round context summary — no LLM call.

Builds a compact structured block from agent turns already in the DB:
  [Round N — <policy_event>]
  AgentName: support=0.72, resistance=0.21, posture=cautiously_supportive — "Opening snippet…"
  ...

This block is injected into subsequent rounds instead of growing raw peer history,
keeping per-call prompt size O(1) regardless of total rounds.
"""

from __future__ import annotations

import json
import re

_STATE_BLOCK = re.compile(r"<state>\s*([\s\S]*?)\s*</state>", re.IGNORECASE)
_STATE_WRAPPER = re.compile(r"<state>\s*[\s\S]*?\s*</state>", re.IGNORECASE)


def _extract_state(raw_response: str) -> dict:
    m = _STATE_BLOCK.search(raw_response or "")
    if not m:
        return {}
    try:
        return json.loads(m.group(1).strip())
    except Exception:
        return {}


def _strip_state(text: str) -> str:
    return _STATE_WRAPPER.sub("", text or "").strip()


def build_round_summary(
    *,
    round_number: int,
    policy_event: str,
    turns: list[dict],
    snippet_chars: int = 80,
) -> str:
    """
    Args:
        turns: list of dicts with keys agent_name, raw_response (as returned by get_turns_for_round).
        snippet_chars: max chars of cleaned response text to include per agent.
    Returns:
        Multi-line string suitable for injecting into future prompts.
    """
    lines = [f"[Round {round_number} — {policy_event}]"]
    for turn in turns:
        name = turn.get("agent_name", "?")
        raw = turn.get("raw_response", "")
        state = _extract_state(raw)
        clean = _strip_state(raw)
        snippet = clean[:snippet_chars].replace("\n", " ")
        if len(clean) > snippet_chars:
            snippet += "…"
        sup = state.get("support_level")
        res = state.get("resistance_level")
        posture = state.get("belief_posture", "?")
        sup_s = f"{float(sup):.2f}" if isinstance(sup, (int, float)) else "?"
        res_s = f"{float(res):.2f}" if isinstance(res, (int, float)) else "?"
        lines.append(f"{name}: support={sup_s}, resistance={res_s}, posture={posture} — \"{snippet}\"")
    return "\n".join(lines)
```

### Definition of done

- `pytest` green
- `rg 'round_summaries' backend/src/mirofish_backend/db/schema.py` — matches
- `rg 'build_round_summary' backend/src/mirofish_backend/llm/round_summary.py` — matches
- Unit test: `build_round_summary()` with 2 turns (one with valid `<state>` block, one without) — both produce non-empty output, no exception

---

## senna-iter-27 — Orchestrator wiring & prompt injection

### `llm/prompt_templates.py`

Update `build_user_prompt()` signature to add `round_summaries` parameter:

```python
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
    round_summaries: list[str] | None = None,   # ← NEW
) -> str:
```

Inject summaries block before the peer interactions block. When `round_summaries` is provided and non-empty:

```python
summaries_block = ""
if round_summaries:
    joined = "\n\n".join(round_summaries)
    summaries_block = (
        "Prior rounds — compact summaries (all agents, structured):\n"
        f"{joined}\n\n"
    )
```

Change the peer interactions section heading to distinguish prior-round history from current-round context:

```python
peer_heading = (
    "Current round — what others have said so far (excludes your current line):\n"
    if round_summaries
    else "What others have said (chronological in this window; excludes your current line):\n"
)
```

Full return statement (replace existing):

```python
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
```

### `simulation/orchestrator.py`

**1. New imports (top of file):**

```python
from mirofish_backend.llm.round_summary import build_round_summary
from mirofish_backend.db.repo import (
    ...,          # existing imports
    upsert_round_summary,
    get_round_summaries,
    get_turns_for_round,
)
```

**2. New parameters on `run_simulation_task` (keyword-only, with defaults):**

```python
round_summary_enabled: bool = True,
transcript_dir: str = "./data/transcripts",
```

Mirror these in `run_simulation_task_guarded` with the same defaults and pass-through.

**3. Cap `interaction_last_k` — change line 588:**

```python
interaction_last_k = min(
    12,   # was 120 — bounded to current-round window
    max(working_memory_last_k * 2, len(agents) * (round_number - 1)),
)
```

**4. Fetch and inject round summaries when building prompts (inside `_run_one_turn`, after `recent_interactions` is resolved, ~line 625):**

```python
prior_summaries: list[str] | None = None
if round_summary_enabled and round_number > 1:
    summary_rows = await get_round_summaries(
        sqlite_path,
        simulation_id=simulation_id,
        up_to_round=round_number,
    )
    prior_summaries = [r["summary_text"] for r in summary_rows] if summary_rows else None
```

Pass `round_summaries=prior_summaries` to both `build_user_prompt()` and `simplified_persona_prompt()`-path calls.

**5. After each round closes (after the `insert_agent_state_snapshot` loop, before `prev_agent_triples` assignment, ~line 879):**

```python
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
```

### `api/simulations.py`

Add `round_summary_enabled` and `transcript_dir` to the `run_simulation_task_guarded(...)` call site (read from `settings`):

```python
round_summary_enabled=settings.round_summary_enabled,
transcript_dir=settings.transcript_dir,
```

### Definition of done

- `pytest` green
- `rg 'round_summaries' backend/src/mirofish_backend/simulation/orchestrator.py` — matches
- `rg 'prior_summaries' backend/src/mirofish_backend/simulation/orchestrator.py` — matches
- Manual check: `interaction_last_k` cap value is `12` not `120`
- Build prompt output check: when `round_summaries` is non-empty, the string "Prior rounds" appears in the returned prompt

---

## senna-iter-28 — `.md` transcript writer

### `simulation/transcript_writer.py` (new file)

```python
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
    agent_names: list[tuple[str, str]],   # [(name, role), ...]
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
```

### `simulation/orchestrator.py` — wiring transcript writer

**Import:**
```python
from mirofish_backend.simulation.transcript_writer import (
    open_transcript,
    append_round_to_transcript,
    close_transcript,
)
```

**Before round loop (after `agents` list is built, ~line 460):**

```python
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
```

**After `upsert_round_summary(...)` call (end of each round):**

```python
    await append_round_to_transcript(
        transcript_dir,
        simulation_id=simulation_id,
        round_number=round_number,
        policy_event=policy_event,
        turns=round_turns,          # already fetched for summary
        round_summary=summary_text,
    )
```

**After the round loop ends (just before `set_simulation_status("completed"...)`):**

```python
if round_summary_enabled:
    await close_transcript(
        transcript_dir,
        simulation_id=simulation_id,
        completed_rounds=total_rounds,
        status="completed",
    )
```

Also call `close_transcript` in the convergence-early-exit path with `status="converged"` and `completed_rounds=round_number`.

### Definition of done

- `pytest` green
- After a short test run (2 rounds, 2 agents), a `.md` file exists at `data/transcripts/{simulation_id}.md`
- File contains header, both round sections, and footer
- `rg 'open_transcript' backend/src/mirofish_backend/simulation/orchestrator.py` — matches

---

## senna-iter-29 — Config flag + tests

### `config.py`

Add two new settings with defaults:

```python
round_summary_enabled: bool = True
transcript_dir: str = "./data/transcripts"
```

### `api/simulations.py`

Confirm `round_summary_enabled` and `transcript_dir` are read from `settings` and forwarded to `run_simulation_task_guarded()`. No logic changes needed here — just plumbing.

### Tests

Add to `tests/` (new file `test_round_summary.py`):

```python
from mirofish_backend.llm.round_summary import build_round_summary

def test_build_round_summary_with_state():
    turns = [
        {
            "agent_name": "Principal_Lim",
            "agent_role": "school_principal",
            "raw_response": 'The banding approach aligns with MOE direction.\n<state>\n{"support_level":0.72,"resistance_level":0.21,"workload_stress":0.30,"belief_posture":"cautiously_supportive","perceived_conflict":false}\n</state>',
        },
        {
            "agent_name": "Parent_Rep",
            "agent_role": "parent_representative",
            "raw_response": "Parents are not ready for this change.",
            # No state block — should degrade gracefully
        },
    ]
    result = build_round_summary(round_number=1, policy_event="PSLE banding rollout", turns=turns)
    assert "Round 1" in result
    assert "Principal_Lim" in result
    assert "support=0.72" in result
    assert "Parent_Rep" in result
    assert "support=?" in result    # graceful degradation


def test_build_round_summary_empty_turns():
    result = build_round_summary(round_number=3, policy_event="No speakers", turns=[])
    assert "Round 3" in result
```

Add to `tests/` (new file `test_transcript_writer.py`) — a sync test that calls `open_transcript` / `append_round_to_transcript` / `close_transcript` using `asyncio.run()` against a temp dir, and asserts the `.md` file exists with expected content sections.

### Definition of done

- `pytest` green (all existing + new tests)
- `rg 'round_summary_enabled' backend/src` — appears in `config.py`, `simulations.py`, `orchestrator.py`
- `rg 'transcript_dir' backend/src` — appears in `config.py`, `simulations.py`, `orchestrator.py`
- `rg 'transcript_writer' backend/src/mirofish_backend/simulation/orchestrator.py` — matches

---

## Arc 6 overall Definition of done

1. `pytest` — green
2. `npm run build` in `frontend/` — PASS (no frontend changes, but confirm no regressions)
3. A full 3-round, 4-agent simulation completes without error
4. Transcript file written to `data/transcripts/`
5. `SELECT round_number, summary_text FROM round_summaries WHERE simulation_id = '<id>';` returns one row per completed round
6. Prompt for round 3 (inspected via `raw_prompt` column) contains "Prior rounds — compact summaries"
7. `interaction_last_k` cap is 12 (verify via `rg '12' backend/src/mirofish_backend/simulation/orchestrator.py` and visual check)

---

## Not in scope

- Frontend display of transcripts (future arc)
- LLM-generated summaries (Option A) — deterministic summaries (Option B) shipped here
- RAG over transcript content

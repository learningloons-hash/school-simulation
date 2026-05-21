# Senna iter-27 closeout — Orchestrator wiring & prompt injection

**Arc:** 6 — Context Bounding & Simulation Transcripts (backend).  
**Spec:** [`docs/handoffs/HANDOFF_SENNA_ARC6.md`](../handoffs/HANDOFF_SENNA_ARC6.md) **`## senna-iter-27`**.  
**Not** thesis **Iteration 27** (experiments) — [`iteration-27-closeout.md`](iteration-27-closeout.md).

**Date:** 2026-04-26

## Shipped

| Area | Change |
|------|--------|
| `llm/prompt_templates.py` | `build_user_prompt(..., round_summaries=…)`; `summaries_block` + `peer_heading` per spec |
| `simulation/orchestrator.py` | Imports `build_round_summary`, `get_round_summaries`, `get_turns_for_round`, `upsert_round_summary`; `interaction_last_k` cap **12** (was 120); prior-round summaries for prompts when `round_number > 1`; `upsert_round_summary` after each round’s snapshots |
| `config.py` | `round_summary_enabled`, `transcript_dir` (defaults; **transcript_dir** for **senna-iter-28**) |
| `api/simulations.py` | `run_simulation_task_guarded` forwards settings into `run_simulation_task` |
| `tests/test_prompt_messages.py` | `test_user_prompt_prior_round_summaries_block` — **"Prior rounds"** when `round_summaries` non-empty |

## Verification (Definition of done)

- `rg 'round_summaries' backend/src/mirofish_backend/simulation/orchestrator.py` — matches (`round_summaries=prior_summaries`)
- `rg 'prior_summaries' backend/src/mirofish_backend/simulation/orchestrator.py` — matches
- `interaction_last_k` uses **`12`** not `120` in `min(12, …)` for `turn_index == 1 and round_number > 1`
- `uv run pytest` (from `backend/`): **194 passed, 1 skipped**

## Not in this gate

`.md` transcript files on disk — **senna-iter-28**; extra tests from **senna-iter-29** bundle as in arc handoff.

## Architect

Update [`HANDOFF_TO_ARCHITECT.md`](../handoffs/HANDOFF_TO_ARCHITECT.md) § *Senna Arc 6*; next: **`## senna-iter-28`** + [`HANDOFF_TO_BUILDER.md`](../handoffs/HANDOFF_TO_BUILDER.md) when seeded.

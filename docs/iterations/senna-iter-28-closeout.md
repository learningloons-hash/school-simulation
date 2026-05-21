# Senna iter-28 closeout — `.md` simulation transcript

**Arc:** 6 — Context Bounding & Simulation Transcripts (backend).  
**Spec:** [`docs/handoffs/HANDOFF_SENNA_ARC6.md`](../handoffs/HANDOFF_SENNA_ARC6.md) **`## senna-iter-28`**.  
**Date:** 2026-04-26

## Shipped

| File | Role |
|------|------|
| `simulation/transcript_writer.py` | `open_transcript`, `append_round_to_transcript`, `close_transcript` — one `{transcript_dir}/{simulation_id}.md` per run |
| `simulation/orchestrator.py` | When `round_summary_enabled`: `open_transcript` before round loop; after each `upsert_round_summary`, `append_round_to_transcript` (reuses `round_turns` / `summary_text`); `close_transcript` on normal finish (`status=completed`) and on convergence early exit (`status=converged`, `completed_rounds=round_number`) |
| `tests/test_transcript_writer.py` | Full round-trip + `asyncio.run` smoke test |

`config.py` / `api/simulations.py` already expose `transcript_dir` and `round_summary_enabled` (**senna-iter-27**).

## Definition of done

- `rg 'open_transcript' backend/src/mirofish_backend/simulation/orchestrator.py` — matches
- `uv run pytest` (from `backend/`): **196 passed, 1 skipped**

## Next

**senna-iter-29** — config confirmation + bundle tests per arc — [`HANDOFF_SENNA_ARC6.md`](../handoffs/HANDOFF_SENNA_ARC6.md) **`## senna-iter-29`**.

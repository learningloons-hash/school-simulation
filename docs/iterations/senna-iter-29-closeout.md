# Senna iter-29 closeout — Config + test confirmation (Arc 6 final gate)

**Spec:** [`docs/handoffs/HANDOFF_SENNA_ARC6.md`](../handoffs/HANDOFF_SENNA_ARC6.md) **`## senna-iter-29`**.  
**Date:** 2026-04-26

## Already landed (iters 26–28)

| Item | Status |
|------|--------|
| `config.py` — `round_summary_enabled`, `transcript_dir` | Present with arc defaults |
| `api/simulations.py` — `run_simulation_task_guarded(..., settings.…)` | Forwards both from `get_settings()` |
| `simulation/orchestrator.py` — uses flags + `transcript_writer` | `rg 'transcript_writer' …/orchestrator.py` matches |
| `tests/test_round_summary.py` | Matches arc (Principal_Lim / Parent_Rep, empty turns) |
| `tests/test_transcript_writer.py` | Full round-trip + `asyncio.run` smoke |

## This gate

- **`tests/test_senna_arc6_config.py`** — `Settings` / `get_settings()` expose `round_summary_enabled` and `transcript_dir` with expected defaults (iter-29 contract test).

## Definition of done (arc)

- `uv run pytest` — **198 passed, 1 skipped**
- `rg 'round_summary_enabled' backend/src` — `config.py`, `simulations.py`, `orchestrator.py`
- `rg 'transcript_dir' backend/src` — same three (+ `transcript_writer.py` docstrings/params)
- `rg 'transcript_writer' …/orchestrator.py` — import from `mirofish_backend.simulation.transcript_writer`
- `npm run build` in `frontend/` — **PASS** (no frontend code changes; regression check for Arc 6 overall DoD)

## Arc 6

All **`senna-iter-26`–`29`** complete per [`HANDOFF_SENNA_ARC6.md`](../handoffs/HANDOFF_SENNA_ARC6.md) § *Arc 6 overall Definition of done* (manual E2E / DB checks remain optional product QA). Architect sign-off: [`HANDOFF_TO_ARCHITECT.md`](../handoffs/HANDOFF_TO_ARCHITECT.md) § *Senna Arc 6*.

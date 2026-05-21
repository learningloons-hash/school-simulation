# Senna iter-38 closeout — Pre-Run Context and Cost Checks

**Spec:** [`docs/handoffs/HANDOFF_SENNA_ARC8.md`](../handoffs/HANDOFF_SENNA_ARC8.md) **`## senna-iter-38`**.  
**Date:** 2026-05-19

## Shipped

- **`simulation/preflight.py`:** Pure estimator for speaking turns, LLM vs heuristic counts, anthropic/openai-compatible split, token/cost envelope (`estimate_cost_usd` + `openai`/`openrouter` pricing keys), context pressure ratio, and analyst-facing warnings.
- **API:** `POST /simulations/preflight` returns `{ warnings, preflight }`; `POST /simulations/run` merges preflight warnings into `warnings[]` and stores compact `preflight` on `config_snapshot`.
- **Frontend:** Debounced preflight on Run setup (Set Up & Run tab) — estimate summary + yellow warning panel before Start; post-start server warnings unchanged.

## Files touched

- `backend/src/mirofish_backend/simulation/preflight.py` (new)
- `backend/src/mirofish_backend/simulation/economics.py`
- `backend/src/mirofish_backend/api/simulations.py`
- `backend/tests/test_senna_iter38_preflight.py` (new)
- `frontend/src/lib/api.ts`
- `frontend/src/App.tsx`

## Verification

- `uv run pytest` (from `backend/`): **271 passed, 1 skipped**
- `npm run build` (from `frontend/`): **PASS**
- Local-only runs: `$0` envelope; hybrid/commercial: non-zero when pricing known

## Next

- **senna-iter-39** — structured output reliability + Arc 8 integration (`HANDOFF_SENNA_ARC8.md` § senna-iter-39)

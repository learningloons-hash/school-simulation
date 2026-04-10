# Iteration 29 closeout — Run economics (tokens + cost)

**Date:** 2026-04-08 (ship); **post–review tidy** same day  
**Architect:** **PASS** — [`review-iteration-29.md`](../reviews/review-iteration-29.md) (follow-ups applied — see § *Follow-up resolution*).  
**Theme:** Instrument **token usage** per LLM turn and per run; persist totals; **estimate USD cost** from list-price defaults (Anthropic-scale for `anthropic` turns; **$0** for `lmstudio` / heuristic / Tier-3 rows); surface in **API**, **exports**, **Experiments**, and **Run metadata** UI.

## Shipped

| Area | Detail |
|------|--------|
| **DB** | `simulation_runs.total_input_tokens`, `total_output_tokens`; `agent_turns.input_tokens`, `output_tokens` (nullable; Tier-3 uses `0`). |
| **LLM** | `LLMCompletion` from `llm_complete`; LM Studio + Anthropic clients parse `usage` when present. |
| **Orchestrator** | Accumulates tokens after each round’s `asyncio.gather`; `update_simulation_token_totals` per round. |
| **Economics** | `simulation/economics.py` — `PROVIDER_PRICE_MAP`, `PRICE_MAP_DATE`, env overrides; per-turn cost sum for `estimated_cost_usd`. |
| **GET /simulations/{id}** | `economics` object + per-turn `input_tokens` / `output_tokens` on transcript rows. |
| **GET /experiments/{id}** | Per-run `economics`, `total_estimated_cost_usd`; `comparison.csv` adds `input_tokens`, `output_tokens`, `estimated_cost_usd`. |
| **Export** | **`export_version` `8`**; `run.economics`, run token totals; `agent_turns.csv` token columns. |
| **Capabilities** | `simulation_run.economics` description + pricing snapshot date. |
| **Frontend** | Run metadata **economics** panel; Experiments total cost + per-run tokens/cost; comparison table header hints. |

## Post–architect review (2026-04-08)

Minor items from [`review-iteration-29.md`](../reviews/review-iteration-29.md) **M1–M5**:

| Item | Change |
|------|--------|
| **M1** | `estimate_cost_usd` uses `_per_mtok_rates(provider_key)` (future-proof for new map entries). |
| **M2** | Inline comment on `PROVIDER_PRICE_MAP["hybrid"]` vs per-turn `effective_provider` billing. |
| **M3** | `test_economics_pure_functions` — isolated tests for pricing, `None` tokens, tier breakdown, payload shape. |
| **M4** | Documented below as design invariant (no code change). |
| **M5** | E2E test with `llm_provider=anthropic` asserts **non-zero** `estimated_cost_usd`. |

## Design notes

- **Run token totals (M4):** `simulation_runs.total_input_tokens` / `total_output_tokens` are **denormalised** sums updated by the orchestrator after each round. There is **no** API path to mutate or delete `agent_turns` rows today; if that ever changes, recompute totals (trigger or batch job).

## Behaviour notes

- **Missing usage** from local OpenAI-compatible servers → `null` per-turn tokens (distinct from Tier-3 **`0`**).
- **Hybrid** runs: only turns with `effective_provider == anthropic` contribute to **non-zero** `estimated_cost_usd`.
- **Thesis:** RQ2 cost tables can use experiment **`comparison.csv`** (repeated per-row token/cost columns) or per-run ZIP bundles.

## Gate evidence

```bash
cd backend && uv run pytest --tb=no -q
# 191 passed, 1 skipped
cd ../frontend && npm run build
```

## Tests

**`tests/test_iteration29.py`** — E2E: simulation + export + experiment ZIP; **anthropic** pricing path (`estimated_cost_usd` > 0); **unit**: `estimate_cost_usd`, transcript cost sum, `None` usage, tier breakdown, `build_run_economics_payload`.

## Next

**Arc complete** for platform economics + prior convergence work. Backlog: real-time cost ticker; hard pre-run cost cap; invoice reconciliation; parallel experiment dispatch / SSE / WAL (see `HANDOFF_TO_BUILDER.md`).

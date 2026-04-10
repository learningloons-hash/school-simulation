# Iteration 8 — Live dashboard & observability (design note)

**Audience:** Builder + architect (Joan brief). **Status:** Implemented MVP per Iteration 8; this doc records decisions and future options.

## What we poll today

- The UI calls **`GET /simulations/{id}`** on a timer while `status === "running"` (or `"starting"` until first poll returns).
- Response already includes **`transcript`**, **`state_timeline`**, **`outcome_indicators`**, **`config_snapshot`**, **`validity_notes`**, etc.
- **No SSE/WebSocket** in Iteration 8 — polling is enough for MVP and keeps the backend unchanged.

## Future: streaming (optional)

- **SSE** or **WebSocket** could push turn boundaries or round completions to reduce latency and load.
- **Tradeoff:** server complexity, reconnect logic, and alignment with export snapshots (still want a coherent GET for analysts).
- **Recommendation:** keep polling until **N agents** or **poll frequency** becomes a measured bottleneck.

## Charts at N agents

| N | Layout (current MVP) |
|---|----------------------|
| **≤ ~10** | Per-agent cards with sparklines + global charts — comfortable. |
| **10–30** | Same data model; UI should **scroll** or **collapse** agent cards (future: “focus agents” filter, pagination). |
| **50+** | Requires **product decision**: summary-only view (histograms, top-K movers), not one card per agent. |
| **500** | Out of scope for this dashboard — needs **roster + sampling** interaction model (Iterations 9–10). |

## Key quotations (not in Iteration 8)

- **Phase A (recommended first):** heuristics — e.g. flag turns where **`conflict_events`** spiked, or **`resistance_level`** delta exceeds a threshold vs previous round (no extra LLM).
- **Phase B:** optional small **LLM tagger** on sampled turns (cost + latency budget; batch off critical path).

## Iteration 8 implementation summary

- **Live** tab: global sparklines (readiness, alignment), outcome table + adoption sparkline, per-agent cards with support/resistance/workload series.
- **Faster poll** while run in progress (~750ms vs ~2s) — client-only.
- **Scale/cost** documented in `docs/plans/SCALE_LIMITS_AND_COST.md`.

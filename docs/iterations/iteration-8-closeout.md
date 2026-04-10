# Iteration 8 closeout

**Project:** `mirofish-mvp`  
**Gate date:** 2026-04-02  
**Theme:** Observability + limits (Joan brief Iteration 8).

## Shipped

| Item | Detail |
|------|--------|
| Design note | `docs/plans/iteration-8-live-dashboard-design.md` |
| Scale / cost | `docs/plans/SCALE_LIMITS_AND_COST.md` |
| Live dashboard | **Live** tab: sparklines (readiness, alignment, adoption, per-agent S/R/W) + outcome table |
| Polling | **~750ms** while `running` / `starting` (client-only) |
| Run tab | Link to Live; agent limit blurb → scale doc |
| Architecture index | `references/ARCHITECTURE.md` updated |

## Not in scope (per brief)

- SSE/WebSocket streaming
- Key-quote tagging (Phase A/B documented only)
- Backend schema changes (e.g. `effective_provider` per turn) — Iteration 12 target

## Gate evidence

```bash
cd backend && PYTHONPATH=src pytest tests/ -q   # 27 passed (unchanged backend)
cd ../frontend && npm run build
```

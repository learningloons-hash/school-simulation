# senna-iter-14 closeout — Attitudes tab: readable agent state

**Date:** 2026-04-20  
**Scope:** `docs/handoffs/HANDOFF_SENNA_ARC3.md` § senna-iter-14.

## Shipped

- **`frontend/src/App.tsx` — Attitudes (`state`) tab**
  - Section title **Attitudes** (aligned with tab label).
  - Each **round** wrapped in **`cardStyle`** with `padding: 16` (palette border `#E5E3DC`, white surface).
  - **Global row:** Readiness to adopt (%), Level of agreement (%), optional **Opinion change rate** (three decimals) when `round.global_state.convergence_delta` is present — uppercase micro-labels per handoff.
  - **Agents:** inner cards on `#F7F6F2`, name + role with underscores → spaces, Support / Resistance / Workload as **%** and **Stance** with `<strong>` for values — no `support_level`-style keys in UI copy.
  - **Removed:** demographics bracket line; **`attribute_sections` JSON `<pre>`** (deep data remains in export ZIP only).
  - Empty state unchanged (`emptyStateCardStyle`).

## Verification

- `npm run build` in `frontend/` — PASS

## Not in scope

- senna-iter-15 (Run Details / export consolidation).

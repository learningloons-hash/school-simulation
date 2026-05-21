# senna-iter-6 closeout — Scenario Cards

**Date:** 2026-04-20  
**Scope:** `docs/handoffs/HANDOFF_SENNA_ARC2.md` § senna-iter-6.

## Shipped

- `frontend/src/components/ScenarioSelector.tsx` — card grid (1 col / 2 cols when viewport &gt; 700px), `BUILTIN_DESCRIPTIONS`, fallback copy, selected border/tint/`Selected` pill.
- `frontend/src/App.tsx` — policy scenario `<select>` replaced with `<ScenarioSelector />` and section heading **Policy scenario**.

## Verification

- `npm run build` — PASS

## Post–Arc 2 review (notes)

- **ScenarioSelector:** Live `resize` listener (2-column reflow) called out as stronger than a one-shot `window.innerWidth` check.
- **Defer:** Partial `experiment_id` snippet on history cards — tidy when **Experiments** / compare-runs UX is redesigned (Arc 4).

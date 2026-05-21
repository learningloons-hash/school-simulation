# senna-iter-21 closeout — Shared design tokens + RunResultCard polish

**Date:** 2026-04-22  
**Scope:** `docs/handoffs/HANDOFF_SENNA_ARC5.md` § **senna-iter-21** (Part A + Part B, Definition of done).

## Shipped

### `frontend/src/lib/theme.ts` (new)

- Exports **`COLOR`**, **`FONT`**, **`cardStyle`**, **`emptyStateCardStyle`**, **`sectionHeadingStyle`**, **`secondaryBtnStyle`**, **`primaryBtnStyle`** per Arc 5 handoff (single source of truth for palette and shared inline styles).

### `frontend/src/components/RunResultCard.tsx`

- Imports **`cardStyle`**, **`sectionHeadingStyle`**, **`COLOR`**, **`FONT`** from `../lib/theme`; **`shortStatusLabel`**, **`classifyRunStatusTone`**, **`RUN_STATUS_PILL_STYLES`** from `../lib/runStatusCopy`.
- Header: run label, status pill, simulation id as monospace **truncated** snippet (no `<code>`, no raw status string).
- **`failure_reason`** and **`analysis_error`**: shared error panel using **`COLOR.errorBg`**, **`COLOR.errorBorder`**, **`COLOR.errorText`**; user copy **Something went wrong:** (no **Failure:**).
- **Queue** and **generate** warnings merged under one **Warnings** **`sectionHeadingStyle`** heading and a single list.
- Section titles: **Key findings**, **Summary** (was narrative), **Suggested next questions** (was follow-ups); lists use theme text colours.

## Verification

- `npm run build` in `frontend/` — **PASS** (`vite build`).
- `rg '#e0e0e0|#fafafa|#a30' frontend/src/components/RunResultCard.tsx` — **no matches**.
- `rg 'Queue warnings|Generate warnings|Failure:' frontend/src/components/RunResultCard.tsx` — **no matches**.
- `rg '<code>' frontend/src/components/RunResultCard.tsx` — **no matches**.

## Not in scope

- Refactoring **`App.tsx`**, **`AgentConsole.tsx`**, or other components to import **`theme.ts`** (explicitly deferred to senna-iter-22+ except this card).
- Backend; senna-iter-22+ work.

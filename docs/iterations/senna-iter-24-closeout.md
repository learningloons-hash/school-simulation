# senna-iter-24 closeout — Empty states & micro-polish

**Date:** 2026-04-22  
**Scope:** `docs/handoffs/HANDOFF_SENNA_ARC5.md` § **senna-iter-24** (empty states audit + micro-polish, Definition of done).

## Shipped

### `frontend/src/App.tsx`

- **Watch Live:** empty copy updated; when `runId` set and `status === "starting"`, transitional **`emptyStateCardStyle`** (“Starting up — charts…”); otherwise **`LiveRunDashboard`** as before.
- **Conversation:** `transcript.length === 0` → **`emptyStateCardStyle`** with handoff copy; else **`ConversationView`**.
- **Recent discussions — Open:** `title="Load this discussion"`.
- **Load by ID:** React-controlled **`openRunIdInput`**; **`secondaryBtnStyle`** + **`opacity`** for Load; **`disabled={!openRunIdInput.trim()}`**; removed **`document.getElementById("open-run-id")`**.

### `frontend/src/components/ConversationView.tsx`

- Early return **`if (!turns || turns.length === 0) return null`** (empty UI owned by **`App.tsx`**).

### `frontend/src/components/LiveRunDashboard.tsx`

- Convergence banner: **`marginBottom: 12`**.

### `frontend/src/components/ExperimentConsole.tsx`

- Import **`emptyStateCardStyle`** from **`../lib/theme`**.
- **Metric trends** (no detail): “Start or load a comparison above to see metrics here.”
- **Run results** (no detail): “Load a comparison to see per-run results.”
- **Previous comparisons** empty: **`emptyStateCardStyle`** variant + “No previous comparisons…”

## Verification

- `npm run build` in `frontend/` — **PASS** (`vite build`).
- `rg 'open-run-id|getElementById' frontend/src/App.tsx` — **no matches**.

## Not in scope

- Global focus / ARIA tab linkage (**senna-iter-25**); backend.

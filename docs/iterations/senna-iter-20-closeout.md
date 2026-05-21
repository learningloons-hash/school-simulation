# senna-iter-20 closeout — Arc 4 final jargon / layout sweep

**Date:** 2026-04-22  
**Scope:** `docs/handoffs/HANDOFF_SENNA_ARC4.md` § senna-iter-20.

## Shipped

### `frontend/src/components/ConversationView.tsx`

- Turn detail label **Fidelity tier** → **Detail level** (numeric value unchanged).

### `frontend/src/App.tsx`

- **Recent discussions:** when `experiment_id` is set, show **· part of a comparison run** (`#6B7280`) — no ID fragment.
- **Tab panels:** removed redundant `<h2>` echoes for Watch Live, Conversation, Results, Attitudes, Compare Runs, Assistant; added **`paddingTop: 4`** on those `<section>`s (agent section already had vertical padding).
- **Kept** **Run Details** and **Quality notes** `<h2>`s (in-tab section headings).
- **Palette:** large-run hint `#a60` → **`#92400E`**; list error **coral** → **`#E05252`**.

### Root `CLAUDE.md`

- Arc 4 **Advanced Features Accessible** → **CLOSED**.

## Verification

- `npm run build` in `frontend/` — **PASS**
- `rg 'Fidelity' frontend/src/components/ConversationView.tsx` — no matches
- `rg '<h2' frontend/src/App.tsx` — **Run Details** and **Quality notes** only
- `rg 'coral|#a60|#a30' frontend/src/App.tsx` — no matches

## Note

Off-palette `#a30` / `#a60` / `coral` may remain in other components (e.g. `AgentConsole`, `RunResultCard`); iter-20 handoff scoped palette pass to **`App.tsx`** user-visible strings.

## Not in scope

- Arc 5 visual system pass; backend.

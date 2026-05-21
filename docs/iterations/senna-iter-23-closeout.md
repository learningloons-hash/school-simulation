# senna-iter-23 closeout — Tab bar polish

**Date:** 2026-04-22  
**Scope:** `docs/handoffs/HANDOFF_SENNA_ARC5.md` § **senna-iter-23** (Parts A–B, Definition of done).

## Shipped

### `frontend/src/App.tsx`

- **`PRIMARY_TABS`** / **`SECONDARY_TABS`** module constants — `as const satisfies [TabId, string][]`; tab rendering loops use them (no inline tab arrays).
- **Tab bar:** single horizontal **scroll** strip (`overflowX: "auto"`), **`flexWrap` removed**; **`scrollbarWidth: "none"`**, **`msOverflowStyle: "none"`**; inline **`<style>`** hides WebKit scrollbar on **`div[role="tablist"]`**.
- **Fade:** right-edge **`linear-gradient(to right, transparent, #F7F6F2)`**, **`pointerEvents: "none"`**, **`aria-hidden`**.
- **ARIA:** scroll container **`role="tablist"`**, **`aria-label="Navigation"`**; each tab button **`role="tab"`**, **`aria-selected={activeTab === id}`**.
- **Divider:** **`flexShrink: 0`**; tab bar **`gap: 6`** (was 8 on old wrapper).
- **`tabStyle`:** `padding: "7px 12px"`, **`borderRadius: 8`**, **`fontFamily: "inherit"`**, **`fontSize: 13`**, active/inactive **`fontWeight`** / **`color`**, **`whiteSpace: "nowrap"`**, **`flexShrink: 0`**, **`transition`**, **`outline: "none"`** (iter-25 will move focus to global `:focus-visible`).

### Part B (verify only)

- **Watch Live** / **Conversation** sections still use **`paddingTop: 4`** on their `<section>` — unchanged.

## Verification

- `npm run build` in `frontend/` — **PASS** (`vite build`).
- Tab labels do not wrap inside buttons; narrow viewport: horizontal scroll instead of wrapped rows.

## Not in scope

- **`aria-controls` / `aria-labelledby` / tab `id`** (senna-iter-25); backend.

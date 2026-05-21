# senna-iter-25 closeout — Accessibility pass & Arc 5 complete

**Date:** 2026-04-22  
**Scope:** `docs/handoffs/HANDOFF_SENNA_ARC5.md` § **senna-iter-25** (Parts A–F, Definition of done). **Arc 5** closed.

## Shipped

### `frontend/index.html`

- Global **`:focus-visible`** ring (`#4A6FA5`, offset 2px); **`:focus:not(:focus-visible)`** clears outline; **`box-sizing: border-box`**; **`[role="tablist"]`** WebKit scrollbar hide; **`scroll-behavior: smooth`** on `html`.

### `frontend/src/lib/theme.ts`

- **`COLOR.textSecondary`:** `#595F6B` (WCAG AA on page bg `#F7F6F2`).
- **`emptyStateCardStyle.color`:** remains **`#6B7280`** (muted text on white cards).

### `frontend/src/App.tsx`

- **`<main>`** wraps tab bar and all tab panels (after **`SennaHeader`**).
- Removed duplicate tablist **`<style>`** (now in **`index.html`**).
- Tab buttons: **`id={tab-${id}}`**, **`aria-controls={panel-${id}`**; **`tabStyle`** no longer sets **`outline: "none"`** (global **`:focus-visible`** handles focus).
- Each tab panel: **`id="panel-…"`**, **`role="tabpanel"`**, **`aria-labelledby="tab-…"`** (controls through scenarios).
- **Refresh** (recent discussions): **`aria-label="Refresh run list"`**; page-level secondary copy **`#595F6B`** where text sits on **`#F7F6F2`** (headings, Run Details helpers, Quality notes intro); **`sectionHeadingStyle`** **`#595F6B`**. Helpers **inside white cards** largely unchanged **`#6B7280`**.

### `frontend/src/components/SennaHeader.tsx`

- Tagline colour **`#595F6B`** (on page background).

### `frontend/src/components/ConversationView.tsx`

- Details toggle: **`aria-label`** **Show** / **Hide turn details**.

### `frontend/src/components/ScenarioWizard.tsx`

- Icon-only **×** key-row remove: **`aria-label="Remove"`**.

### `CLAUDE.md` (repo root)

- **Arc 5** → **CLOSED**; design palette note for **`#595F6B`** / card-muted **`#6B7280`**.

### `RunStatusCard.tsx`

- Unchanged: secondary copy is on **white** cards (**`#6B7280`**), per handoff exception.

## Verification

- `npm run build` in `frontend/` — **PASS** (`vite build`).
- `rg 'outline: \"none\"' frontend/src/App.tsx` — only if unrelated controls remain (tab **`tabStyle`** has no outline rule).

## Arc 5

- Senna UX arc series **Visual Design & Polish** complete per **`HANDOFF_SENNA_ARC5.md`**.

# Senna UX Redesign — Arc 5 Handoff (to Cursor Architect)

**Prepared by:** Claude (Cowork / UX Design Architect)  
**Date:** 2026-04-22  
**Arc:** 5 of 5 — Visual Design & Polish  
**Iterations:** senna-iter-21 through senna-iter-25  
**Backend:** Untouched. All changes are frontend-only.

---

## State entering Arc 5

Arcs 1–4 are closed. The frontend is now:
- Fully renamed to Senna with a proper header component
- All user-facing labels and status messages in plain English
- Advanced tabs (Assistant, Compare Runs, Quality Notes, Policy Scenarios) relabeled
- `cardStyle`, `emptyStateCardStyle`, `sectionHeadingStyle`, `metricCardStyle` established in `App.tsx`
- Most palette violations fixed; a few remain in components not touched by Arcs 1–4

**What Arc 5 does:** The previous arcs fixed what the app says. Arc 5 fixes how it looks and how it feels. This means: a shared design token file so palette values stop being duplicated, fixing the one remaining visually broken component (`RunResultCard`), consistent typography and numeric formatting, a polished tab bar, and a final accessibility pass. No new functionality, no new tabs, no API changes.

---

## Design Philosophy (final arc)

The 75/25 rule is now embedded in the language. Arc 5 applies it to the visual layer. The goal is that every screen feels like it came from a single considered hand, not assembled from a dozen independent sessions.

**What "considered" means in practice:**
- Consistent spacing multiples (4 / 8 / 12 / 16 / 20 / 24px — nothing in between unless unavoidable)
- One font size scale (12 / 13 / 14 / 15 / 22px — already established; use it consistently)
- Numbers in data tables and metric displays always in monospace so columns align
- Empty states are warm, not clinical — a brief sentence explaining what will appear there, not just "None yet"
- Focus is visible — the keyboard user and the mouse user should have the same experience quality

**What Arc 5 is NOT:**
- A layout redesign — the two-column Set Up & Run, the tab bar placement, the card structure — all stay
- A component library migration — no Radix, no shadcn/ui, no CSS Modules, no Tailwind — inline styles throughout, consistent with Arc 1–4
- A rebrand — palette, wordmark, tagline, header are all finalized

---

## Established patterns (must not regress)

- `cardStyle`: `{ background: "#FFFFFF", border: "1px solid #E5E3DC", borderRadius: 10, padding: 20 }`
- `emptyStateCardStyle`: `{ background: "#FFFFFF", border: "1px solid #E5E3DC", borderRadius: 10, padding: 24, textAlign: "center", fontSize: 14, color: "#6B7280" }`
- `sectionHeadingStyle`: `{ fontSize: 13, fontWeight: 600, color: "#6B7280", textTransform: "uppercase", letterSpacing: "0.5px", marginBottom: 12 }`
- Tab active: `border: "1px solid #4A6FA5"`, `background: "#EEF3FA"`
- Tab inactive: `border: "1px solid #E5E3DC"`, `background: "#FFFFFF"`
- Primary button: `background: "#4A6FA5"`, `color: "#FFFFFF"`, `borderRadius: 8`, `padding: "10px 18px"`, `fontWeight: 600`
- Secondary button: `background: "#FFFFFF"`, `border: "1px solid #E5E3DC"`, `borderRadius: 8`, `padding: "8px 14px"`

---

## Arc 5 — Iterations

---

### senna-iter-21 — Shared Design Tokens (`theme.ts`) + `RunResultCard` Polish

**Files:** `frontend/src/lib/theme.ts` (new), `frontend/src/components/RunResultCard.tsx`

**Goal:** Create a single source of truth for all design values, and fully polish `RunResultCard` — the last component with raw developer output visible to users.

---

#### Part A — Create `frontend/src/lib/theme.ts`

Create a new file that exports all palette values and shared style constants:

```ts
// frontend/src/lib/theme.ts
import type { CSSProperties } from "react";

// ── Palette ──────────────────────────────────────────────
export const COLOR = {
  bg:        "#F7F6F2",  // page background
  card:      "#FFFFFF",  // card / panel surface
  textPrimary:   "#1A1A1A",
  textSecondary: "#6B7280",
  accent:    "#4A6FA5",  // interactive, active states
  accentLight: "#EEF3FA", // active tab bg, hover bg
  border:    "#E5E3DC",
  success:   "#4CAF82",
  successBg: "#D1FAE5",
  successText: "#065F46",
  successBorder: "#A7F3D0",
  warning:   "#F59E0B",
  warningBg: "#FEF3C7",
  warningText: "#92400E",
  error:     "#E05252",
  errorBg:   "#FEE2E2",
  errorText: "#991B1B",
  errorBorder: "#FECACA",
} as const;

export const FONT = {
  system: '-apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif',
  mono: '"SF Mono", "Fira Code", "Fira Mono", "Roboto Mono", ui-monospace, monospace',
} as const;

// ── Shared component styles ───────────────────────────────
export const cardStyle: CSSProperties = {
  background: COLOR.card,
  border: `1px solid ${COLOR.border}`,
  borderRadius: 10,
  padding: 20,
};

export const emptyStateCardStyle: CSSProperties = {
  background: COLOR.card,
  border: `1px solid ${COLOR.border}`,
  borderRadius: 10,
  padding: 24,
  textAlign: "center",
  fontSize: 14,
  color: COLOR.textSecondary,
};

export const sectionHeadingStyle: CSSProperties = {
  fontSize: 13,
  fontWeight: 600,
  color: COLOR.textSecondary,
  textTransform: "uppercase",
  letterSpacing: "0.5px",
  marginBottom: 12,
};

export const secondaryBtnStyle: CSSProperties = {
  background: COLOR.card,
  color: COLOR.textPrimary,
  border: `1px solid ${COLOR.border}`,
  borderRadius: 8,
  padding: "8px 14px",
  fontSize: 14,
  cursor: "pointer",
  fontFamily: FONT.system,
  textDecoration: "none",
  display: "inline-block",
};

export const primaryBtnStyle: CSSProperties = {
  background: COLOR.accent,
  color: "#FFFFFF",
  border: "none",
  borderRadius: 8,
  padding: "10px 18px",
  fontWeight: 600,
  fontSize: 15,
  cursor: "pointer",
  fontFamily: FONT.system,
};
```

**Do NOT refactor existing components in this iteration** to import from `theme.ts` — that is a large diff that risks regressions. `theme.ts` is created now and used progressively in iter-22 onwards and by future maintainers. The only component that must import from it in this iteration is `RunResultCard.tsx`.

---

#### Part B — Polish `RunResultCard.tsx`

`RunResultCard` is used in the Assistant tab (`AgentConsole`) to display the result of each planned run. Currently it has off-palette colours, raw `<code>` tags showing status strings and simulation IDs, and developer-facing warning headings.

**Import from `theme.ts`:**
```tsx
import { COLOR, FONT, cardStyle, sectionHeadingStyle } from "../lib/theme";
```
Remove the local `cardStyle` constant — use the imported one.

**Card style update:**
- Current: `padding: 10, border: "1px solid #e0e0e0", borderRadius: 6, background: "#fafafa"`
- Use the imported `cardStyle` — this gives `borderRadius: 10`, proper border, white background

**Header line (run label + status + sim ID):**

Current:
```tsx
<div style={{ fontWeight: 600, marginBottom: 6 }}>
  {run.label} — <code>{run.status}</code>
  {run.simulation_id ? <> · sim <code>{run.simulation_id}</code></> : null}
</div>
```

New — import `shortStatusLabel` from `runStatusCopy.ts` and `classifyRunStatusTone` + `RUN_STATUS_PILL_STYLES`:
```tsx
import { shortStatusLabel, classifyRunStatusTone, RUN_STATUS_PILL_STYLES } from "../lib/runStatusCopy";

// In JSX:
<div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", flexWrap: "wrap", gap: 8, marginBottom: 10 }}>
  <div style={{ fontWeight: 600, fontSize: 15, color: COLOR.textPrimary }}>
    {run.label || "Run"}
  </div>
  <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
    <span style={{
      ...RUN_STATUS_PILL_STYLES[classifyRunStatusTone(run.status)],
      borderRadius: 999, padding: "3px 10px", fontSize: 12, fontWeight: 500,
    }}>
      {shortStatusLabel(run.status)}
    </span>
    {run.simulation_id ? (
      <span style={{ fontFamily: FONT.mono, fontSize: 11, color: COLOR.textSecondary }}>
        {run.simulation_id.slice(0, 10)}…
      </span>
    ) : null}
  </div>
</div>
```

**Failure reason:**
- Current: `color: "#a30"` and text: `"Failure: {run.failure_reason}"`
- New:
```tsx
{run.failure_reason ? (
  <div style={{ padding: "10px 12px", background: COLOR.errorBg, border: `1px solid ${COLOR.errorBorder}`, borderRadius: 8, fontSize: 13, color: COLOR.errorText, marginBottom: 8 }}>
    <strong>Something went wrong:</strong> {run.failure_reason}
  </div>
) : null}
```

**Analysis error:**
- Current: `color: "#a30"` — change to `color: COLOR.errorText`, wrap in same error panel as above

**Queue warnings:**
- Current heading: `<strong>Queue warnings</strong>`
- New: `<div style={sectionHeadingStyle}>Warnings</div>` — merge both queue and generate warnings under a single "Warnings" heading if both are present; show them together in one list

**Generate warnings:**
- Merge with queue warnings as above — no need for a separate "Generate warnings" section; both are server warnings and the user doesn't care which queue they came from

**"Key findings" section:**
- Current: `<strong>Key findings</strong>` with bare `<ul>`
- New: `<div style={{ fontWeight: 600, fontSize: 14, color: COLOR.textPrimary, marginBottom: 6 }}>Key findings</div>` + styled list

**"Narrative" section:**
- Current: `<strong>Narrative</strong>` 
- New: `<div style={{ fontWeight: 600, fontSize: 14, color: COLOR.textPrimary, marginBottom: 6 }}>Summary</div>`

**"Follow-ups" section:**
- Current: `<strong>Follow-ups</strong>`
- New: `<div style={{ fontWeight: 600, fontSize: 14, color: COLOR.textSecondary, marginBottom: 4, fontSize: 13 }}>Suggested next questions</div>`

**Definition of done:**
- [ ] `frontend/src/lib/theme.ts` created and exports all constants listed above
- [ ] `RunResultCard.tsx` imports from `theme.ts` and `runStatusCopy.ts` — no local palette values
- [ ] No `<code>` tags showing raw status or simulation ID
- [ ] `#e0e0e0`, `#fafafa`, `#a30` gone from `RunResultCard.tsx`
- [ ] "Queue warnings" / "Generate warnings" / "Failure:" labels not visible to users
- [ ] `npm run build` passes

**Closeout:** Write `docs/iterations/senna-iter-21-closeout.md`

---

### senna-iter-22 — Typography & Numeric Formatting Pass

**Files:** `frontend/src/App.tsx`, `frontend/src/components/LiveRunDashboard.tsx`

**Goal:** Two focused improvements — monospace font on numeric data cells so columns align, and consistent heading treatment for the two remaining raw `<h2>` elements ("Run Details", "Quality notes").

---

#### Part A — Monospace numeric cells

**Results tab — outcome indicators table (`App.tsx`):**

The `<td>` cells currently use default font. Numbers in data tables should be monospace so they align visually:

```tsx
// Add to numeric data cells in the outcomeIndicators table:
style={{ padding: "8px 12px", color: "#1A1A1A", fontFamily: FONT.mono, fontSize: 13 }}
```

Apply to: adoption score, disagreements, consistency score cells. The "Round" column (ordinal number) can stay sans-serif.

> Import `FONT` from `"./lib/theme"` at the top of `App.tsx`.

**Compare Runs — metrics table (`ExperimentConsole.tsx`):**

The table cells already use `fontFamily: "monospace"` — update to use `FONT.mono` from `theme.ts`:
```tsx
import { FONT } from "../lib/theme";
// ...
style={{ ..., fontFamily: FONT.mono, fontSize: 11 }}
```

**LiveRunDashboard — round-by-round table cells:**

Find the outcomes table in `LiveRunDashboard.tsx`. Any `<td>` cells containing numeric values should get `fontFamily: FONT.mono`.

---

#### Part B — Heading consistency

Two sections in `App.tsx` still use raw browser `<h2>` elements: Run Details and Quality notes. These should be styled consistently rather than relying on browser defaults:

**Run Details heading:**
```tsx
// Current:
<h2>Run Details</h2>
// New:
<div style={{ fontSize: 18, fontWeight: 600, color: "#1A1A1A", marginBottom: 20, marginTop: 0 }}>Run Details</div>
```

**Quality notes heading:**
```tsx
// Current:
<h2 style={{ marginTop: 0, marginBottom: 16, fontSize: 18, fontWeight: 600 }}>Quality notes</h2>
// Tighten to:
<div style={{ fontSize: 18, fontWeight: 600, color: "#1A1A1A", marginBottom: 16 }}>Quality notes</div>
```

This removes reliance on browser `<h2>` default styles which vary, and ensures the heading matches the design system's type scale.

---

#### Part C — Spacing tightening in `App.tsx`

A few spacing values in `App.tsx` are slightly off the 4px grid. While doing the above changes, correct the following:

- Run Details section: ensure consistent `marginTop` between the Download section and the Session ID line — set `marginTop: 16` between sections
- Quality notes form card: padding is currently 20 — keep; `gap: 10` on the grid — keep; ensure the score field grid uses `gap: 8` not a mix

No other spacing changes — don't pursue a comprehensive spacing audit in this iteration.

**Definition of done:**
- [ ] Numeric cells in the Results table use `FONT.mono`
- [ ] `ExperimentConsole.tsx` uses `FONT.mono` from `theme.ts` (not inline `"monospace"`)
- [ ] Numeric cells in `LiveRunDashboard.tsx` outcomes table use `FONT.mono`
- [ ] `<h2>Run Details</h2>` and `<h2>Quality notes</h2>` replaced with styled `<div>` elements
- [ ] No new browser-default `<h2>` or `<h3>` introduced
- [ ] `npm run build` passes

**Closeout:** Write `docs/iterations/senna-iter-22-closeout.md`

---

### senna-iter-23 — Tab Bar Polish

**File:** `frontend/src/App.tsx` (tab bar rendering section, lines ~404–441)

**Goal:** The tab bar currently wraps to multiple lines on narrower viewports without any visual accommodation. On a laptop at 1024px width it looks fine; at 768px the tabs wrap awkwardly. This iteration makes the tab bar robust and adds the ARIA semantics needed for accessibility.

---

#### Part A — Tab bar layout

**Current structure:** A single `<div style={{ display: "flex", flexWrap: "wrap", ... }}>` containing all 10 tab buttons and a vertical divider.

**New structure:** Replace with a scrollable tab strip that stays on one line and shows a fade on the right edge when it overflows. On wide screens it behaves identically to before; on narrow screens it scrolls horizontally.

```tsx
// Outer wrapper — clips the scroll content and provides the fade
<div
  style={{
    position: "relative",
    marginBottom: 16,
  }}
>
  {/* Scrollable strip */}
  <div
    role="tablist"
    aria-label="Navigation"
    style={{
      display: "flex",
      alignItems: "center",
      gap: 6,
      overflowX: "auto",
      scrollbarWidth: "none",       // Firefox
      msOverflowStyle: "none",      // IE/Edge legacy
      paddingBottom: 2,             // room for focus ring
    }}
  >
    {/* Primary tabs */}
    {primaryTabs.map(([id, label]) => (
      <button
        key={id}
        type="button"
        role="tab"
        aria-selected={activeTab === id}
        style={tabStyle(id)}
        onClick={() => setActiveTab(id)}
      >
        {label}
      </button>
    ))}

    {/* Divider */}
    <div
      style={{
        width: 1,
        alignSelf: "stretch",
        minHeight: 28,
        background: "#E5E3DC",
        margin: "0 4px",
        flexShrink: 0,
      }}
      aria-hidden
    />

    {/* Secondary tabs */}
    {secondaryTabs.map(([id, label]) => (
      <button
        key={id}
        type="button"
        role="tab"
        aria-selected={activeTab === id}
        style={tabStyle(id)}
        onClick={() => setActiveTab(id)}
      >
        {label}
      </button>
    ))}
  </div>

  {/* Fade overlay — right edge only */}
  <div
    aria-hidden
    style={{
      position: "absolute",
      top: 0,
      right: 0,
      width: 32,
      height: "100%",
      background: "linear-gradient(to right, transparent, #F7F6F2)",
      pointerEvents: "none",
    }}
  />
</div>
```

Add a `<style>` tag inside the component (or inline with `dangerouslySetInnerHTML`) to hide the scrollbar on WebKit:
```tsx
<style>{`div[role="tablist"]::-webkit-scrollbar { display: none; }`}</style>
```

**Tab button style refinement:**

Current `tabStyle`:
```ts
padding: "8px 12px",
borderRadius: 6,
border: active ? "1px solid #4A6FA5" : "1px solid #E5E3DC",
background: active ? "#EEF3FA" : "#FFFFFF",
cursor: "pointer",
```

Updated `tabStyle`:
```ts
padding: "7px 12px",
borderRadius: 8,            // up from 6 — matches card radius family
border: active ? "1px solid #4A6FA5" : "1px solid #E5E3DC",
background: active ? "#EEF3FA" : "#FFFFFF",
cursor: "pointer",
fontFamily: "inherit",      // ensure system font, not browser button default
fontSize: 13,               // consistent — was relying on browser button default
fontWeight: active ? 500 : 400,
color: active ? "#4A6FA5" : "#1A1A1A",
whiteSpace: "nowrap",       // prevent any label from wrapping within the button
flexShrink: 0,              // prevent buttons from shrinking in the flex strip
transition: "background 0.1s ease, border-color 0.1s ease",
outline: "none",            // outline managed via :focus-visible in iter-25
```

**Extract tab arrays** (remove the inline `as const` array literals):
```ts
const PRIMARY_TABS = [
  ["controls", "Set Up & Run"],
  ["live", "Watch Live"],
  ["transcript", "Conversation"],
  ["outcomes", "Results"],
  ["state", "Attitudes"],
] as const satisfies [TabId, string][];

const SECONDARY_TABS = [
  ["experiments", "Compare Runs"],
  ["agent", "Assistant"],
  ["scenarios", "Policy Scenarios"],
  ["validity", "Quality Notes"],
  ["metadata", "Run Details"],
] as const satisfies [TabId, string][];
```

Use these constants in the rendering loop.

---

#### Part B — Tab panel wrappers

Each tab panel section should have a consistent outer wrapper. Currently each section uses `tabPanelStyle(id)` inline which sets `display: "block" | "none"`. That's correct and should stay.

Add `paddingTop: 0` to the Watch Live and Conversation sections if removing the `<h2>` in iter-20 left them feeling top-heavy. (iter-20 added `paddingTop: 4` — keep that.)

**Definition of done:**
- [ ] Tab bar renders on a single scrollable line — no wrapping
- [ ] Scrollbar hidden (WebKit + Firefox)
- [ ] Fade overlay present on right edge
- [ ] All tab buttons have `role="tab"` and `aria-selected`
- [ ] Tab bar has `role="tablist"` and `aria-label="Navigation"`
- [ ] `PRIMARY_TABS` and `SECONDARY_TABS` constants extracted and used
- [ ] Tab button font, colour, and `whiteSpace: nowrap` applied
- [ ] `npm run build` passes

**Closeout:** Write `docs/iterations/senna-iter-23-closeout.md`

---

### senna-iter-24 — Empty States & Micro-Polish

**Files:** `frontend/src/App.tsx`, `frontend/src/components/LiveRunDashboard.tsx`, `frontend/src/components/ConversationView.tsx`, `frontend/src/components/ExperimentConsole.tsx`

**Goal:** Every tab has a meaningful empty state. Micro-inconsistencies in copy and layout are resolved. This is the final content pass before the accessibility iteration.

---

#### Empty states audit and fixes

**Watch Live tab (`App.tsx`):**

Current: When `runId` is null, shows `<div style={emptyStateCardStyle}>Start a run or load one from the Set Up & Run tab to see live metrics.</div>`

When `runId` is not null but `status === "starting"`, `LiveRunDashboard` receives data but shows empty chart areas. Add a transitional state in the Watch Live section:

```tsx
{!runId ? (
  <div style={emptyStateCardStyle}>
    Start a discussion from the Set Up &amp; Run tab to see live charts here.
  </div>
) : status === "starting" ? (
  <div style={emptyStateCardStyle}>
    Starting up — charts will appear once the first round begins.
  </div>
) : (
  <LiveRunDashboard ... />
)}
```

**Conversation tab (`App.tsx` + `ConversationView.tsx`):**

`ConversationView` currently renders nothing when `turns` is empty. The tab panel in `App.tsx` should render `ConversationView` only when there are turns; otherwise show empty state:

```tsx
{transcript.length === 0 ? (
  <div style={emptyStateCardStyle}>
    No conversation yet. Start a discussion and exchanges will appear here as they happen.
  </div>
) : (
  <ConversationView turns={transcript} />
)}
```

**Results tab (`App.tsx`):**

Current empty state: `"Results will appear here once a discussion is complete."` — this is fine. Keep.

**Attitudes tab (`App.tsx`):**

Current empty state: `"Attitude data will appear here as the discussion progresses."` — this is fine. Keep.

**Compare Runs tab (`ExperimentConsole.tsx`):**

The component loads its own experiment list on mount. When `expList.length === 0` after loading, the current display is a bare `<div>None yet.</div>`. Update:

```tsx
{expList.length === 0 ? (
  <div style={{ ...emptyStateCardStyle, textAlign: "left", padding: "14px 16px" }}>
    No previous comparisons. Set up a new one above to get started.
  </div>
) : (
  // existing list
)}
```

Also: the "No experiment loaded" states in the Metric trends and Run results sections:
- `"Create or load an experiment to see metrics by round."` → `"Start or load a comparison above to see metrics here."`
- `"No experiment loaded."` (Per-run status / Run results) → `"Load a comparison to see per-run results."`

**Assistant tab (`AgentConsole.tsx`):**

`lastAsk` is null on first load. The empty state is just the question textarea — that's fine for a tool tab. No change needed.

**Policy Scenarios tab (`ScenarioWizard.tsx`):**

No tab-level empty state needed — the wizard is always in a usable state.

**Quality Notes tab (`App.tsx`):**

The "Load a run first to add notes." message when `!runId` is already clear. Keep.

---

#### Micro-polish items

**`ConversationView.tsx` — empty turns guard:**

Add a guard at the top of the render function:
```tsx
if (!turns || turns.length === 0) return null;
```
This prevents the container div rendering with no content (visible as extra whitespace).

**`LiveRunDashboard.tsx` — convergence banner spacing:**

The convergence banner ("`✓ Consensus reached...`") currently has no bottom margin before the content below it. Add `marginBottom: 12`.

**`App.tsx` — "Open" button in run history:**

The "Open" button in Recent discussions loads the run and switches tab. After clicking, the active tab changes but there's no visual confirmation. Add `title="Load this discussion"` to the Open button so users get a tooltip.

**`App.tsx` — Load by ID button:**

The "Load" button next to the run ID input has no disabled state when the input is empty. Add:
```tsx
disabled={!(document.getElementById("open-run-id") as HTMLInputElement)?.value?.trim()}
```
This won't work reliably with DOM querying — convert the `open-run-id` field to React-controlled state:
```tsx
const [openRunIdInput, setOpenRunIdInput] = useState("");
```
Replace the `<input id="open-run-id" />` with a controlled input:
```tsx
<input
  value={openRunIdInput}
  onChange={(e) => setOpenRunIdInput(e.target.value)}
  placeholder="Paste a run ID to reload a previous session"
  style={{ flex: "1 1 240px", padding: "8px 12px", border: "1px solid #E5E3DC", borderRadius: 8, fontFamily: "inherit" }}
/>
<button
  type="button"
  disabled={!openRunIdInput.trim()}
  style={{ ...secondaryBtnStyle, opacity: openRunIdInput.trim() ? 1 : 0.5 }}
  onClick={() => void loadRunById(openRunIdInput)}
>
  Load
</button>
```
Remove the `document.getElementById` call.

**Definition of done:**
- [ ] Watch Live shows "Starting up" message when `status === "starting"` and run has begun
- [ ] Conversation tab shows empty state when `transcript.length === 0`
- [ ] `ConversationView` has early return guard for empty turns
- [ ] `ExperimentConsole` recent experiments and chart section empty states updated
- [ ] Run ID input is React-controlled (no `document.getElementById`); Load button disabled when empty
- [ ] `npm run build` passes

**Closeout:** Write `docs/iterations/senna-iter-24-closeout.md`

---

### senna-iter-25 — Accessibility Pass

**Files:** `frontend/src/App.tsx`, `frontend/index.html`, and any component with interactive controls that lack ARIA attributes

**Goal:** Keyboard users and screen reader users should be able to use Senna without friction. This is the final iteration — ship it clean.

---

#### Part A — Global focus ring (`index.html` or `App.tsx`)

Currently buttons have no visible focus ring (browsers suppress the default on `:focus` for mouse interactions; `:focus-visible` is the modern approach).

Add a `<style>` block in `index.html` (in the `<head>`):

```html
<style>
  *, *::before, *::after { box-sizing: border-box; }

  /* Visible focus ring for keyboard navigation */
  :focus-visible {
    outline: 2px solid #4A6FA5;
    outline-offset: 2px;
  }

  /* Remove focus ring for mouse/pointer interactions */
  :focus:not(:focus-visible) {
    outline: none;
  }

  /* Scrollbar hide for tab bar (WebKit) */
  [role="tablist"]::-webkit-scrollbar {
    display: none;
  }

  /* Smooth scrolling */
  html {
    scroll-behavior: smooth;
  }
</style>
```

This removes the need for the inline `outline: "none"` on tab buttons added in iter-23 — remove that style property from `tabStyle` after this is added.

---

#### Part B — Tab bar ARIA (already added in iter-23 — verify)

Verify the tab bar from iter-23 has:
- `role="tablist"` on the scroll container
- `role="tab"` on each button
- `aria-selected={activeTab === id}` on each button

Additionally add `id` attributes to tab buttons and `aria-controls` pointing to their panels:
```tsx
<button
  id={`tab-${id}`}
  role="tab"
  aria-selected={activeTab === id}
  aria-controls={`panel-${id}`}
  ...
>
```

And on each panel section add `id` and `aria-labelledby`:
```tsx
<section
  id={`panel-${activeTab}`}
  role="tabpanel"
  aria-labelledby={`tab-${activeTab}`}
  style={tabPanelStyle("controls")}
  aria-hidden={tabPanelHidden("controls")}
>
```
Do this for all 10 tab panels.

> Note: `aria-hidden={tabPanelHidden(id)}` was already in place from earlier arcs. The `id` + `aria-controls` + `aria-labelledby` linkage is the new addition.

---

#### Part C — Icon-only controls

Several controls have no accessible label because their visible content is an icon or symbol:

| Element | Current | Fix |
|---------|---------|-----|
| ↻ Refresh button (run list) | No label | `aria-label="Refresh run list"` |
| ▸ / ▾ Details toggle (ConversationView) | Symbol only | `aria-label={open ? "Hide turn details" : "Show turn details"}` |
| ▸ Advanced settings toggle (AgentConsole) | Text included — OK | No change needed |
| × Remove buttons (ScenarioWizard) | Symbol only | `aria-label="Remove"` |
| + Add … buttons (ScenarioWizard) | Text included — OK | No change needed |

---

#### Part D — Form field `id` / `htmlFor` linkage

Several `<label>` elements in `App.tsx` use the `style={{ display: "grid" }}` wrapping pattern which does implicitly associate the label with the input. That pattern is fine and accessible — no change needed for those.

However, the standalone label text + input pairs in the Quality Notes section that use `<label style={{ display: "grid", gap: 4 }}>` are already correct.

Check: the three score inputs are inside a `gridTemplateColumns: "1fr 1fr 1fr"` div but the `<label>` wraps each — correct.

No `id`/`htmlFor` changes needed.

---

#### Part E — Colour contrast verification

The secondary text colour `#6B7280` on `#F7F6F2` background: contrast ratio ≈ 4.0:1. This just misses WCAG AA (4.5:1) for normal text. However, all secondary text in Senna is either:
- Helper text at 12px (WCAG large text threshold is 18px/14px bold — helper text is below this, so 4.5:1 applies), or
- Labels at 13px (same)

For these edge cases, increase secondary text to `#595F6B` (approx 4.6:1 on `#F7F6F2`). This is a subtle darkening — not visually noticeable but compliant.

**Apply globally:** In `App.tsx`, change the `sectionHeadingStyle` and all `color: "#6B7280"` secondary text occurrences that appear on the `#F7F6F2` background to `#595F6B`.

**Exception:** Secondary text that appears on `#FFFFFF` card backgrounds — `#6B7280` on `#FFFFFF` has a contrast of 4.6:1, which passes AA. Leave those unchanged.

> Implementation note: the safest approach is to change the `COLOR.textSecondary` value in `theme.ts` to `"#595F6B"` for iter-25. Components that import from `theme.ts` get the fix automatically. Components that still have `color: "#6B7280"` inline should be updated in `App.tsx` and wherever the change is easiest to make. Full sweep of all components is optional for this iteration — prioritise `App.tsx`, `SennaHeader.tsx`, and `RunStatusCard.tsx`.

---

#### Part F — `<main>` landmark

Wrap the main application content in a `<main>` element for screen reader navigation:

In `App.tsx`, wrap everything inside the outer `<div>` (after `<SennaHeader>`) in a `<main>`:
```tsx
<SennaHeader ... />
<main>
  {/* tab bar */}
  {/* tab panels */}
</main>
```

This allows screen reader users to skip to the main content with a single keystroke.

---

**Definition of done:**
- [ ] Global `:focus-visible` ring visible in browser when tabbing through controls
- [ ] All tab buttons have `role="tab"`, `aria-selected`, `id`, `aria-controls`
- [ ] All tab panels have `role="tabpanel"`, `id`, `aria-labelledby`
- [ ] Tab bar container has `role="tablist"`, `aria-label`
- [ ] ↻ Refresh, × Remove, and ▾ toggle buttons have `aria-label`
- [ ] `<main>` landmark wraps app content
- [ ] Secondary text on page background (`#F7F6F2`) uses `#595F6B` in `App.tsx`, `SennaHeader.tsx`, `RunStatusCard.tsx`
- [ ] `COLOR.textSecondary` in `theme.ts` updated to `#595F6B`
- [ ] `npm run build` passes
- [ ] Arc 5 complete: update `CLAUDE.md` Arc 5 → CLOSED

**Closeout:** Write `docs/iterations/senna-iter-25-closeout.md`

---

## Arc 5 — Architect Instructions

Work through iterations **sequentially**: senna-iter-21 → 22 → 23 → 24 → 25.

For each iteration:
1. Seed Builder with the relevant `###` section from this document
2. Include the standard bootstrap: read `CLAUDE.md` + `docs/handoffs/HANDOFF_TO_BUILDER.md` + this file first
3. Builder implements, runs `npm run build`, writes closeout
4. Architect reviews closeout + build output
5. PASS → seed next. PASS_WITH_ISSUES → resolve before next.

**Builder bootstrap (paste into each new Cursor chat):**

> You are implementing the Senna UX redesign in `mirofish-mvp/frontend/`. Read in order:
> 1. `CLAUDE.md` (project context and design system)
> 2. `docs/handoffs/HANDOFF_SENNA_ARC5.md` (this handoff — full spec for Arc 5)
> 3. Then jump to the **senna-iter-N** section for the current iteration.
>
> Rules: Match existing code style. Frontend changes only (backend untouched). Run `npm run build` in `frontend/` after changes. Write `docs/iterations/senna-iter-N-closeout.md` when done. Do not expand scope beyond the active iteration spec.

---

## Arc 5 — Definition of Arc Complete

All of the following must be true before handing back to Claude for arc review:

- [ ] `frontend/src/lib/theme.ts` exists with all palette + style constants
- [ ] `RunResultCard` uses palette values from `theme.ts`; no raw `<code>` tags, no `#a30`, `#e0e0e0`, `#fafafa`
- [ ] Numeric cells in Results, Compare Runs, and LiveRunDashboard tables use `FONT.mono`
- [ ] `<h2>Run Details</h2>` and `<h2>Quality notes</h2>` replaced with styled `<div>` elements
- [ ] Tab bar is on a single scrollable non-wrapping line with hidden scrollbar
- [ ] Tab buttons have `role="tab"`, `aria-selected`, `id`, `aria-controls`
- [ ] `role="tabpanel"`, `id`, `aria-labelledby` on all panels
- [ ] `role="tablist"` + `aria-label` on tab bar container
- [ ] Watch Live shows "Starting up" state when `status === "starting"`
- [ ] Conversation tab shows empty state before first turn
- [ ] Run ID input is React-controlled; Load button disabled when empty
- [ ] Global `:focus-visible` outline in `index.html`
- [ ] `aria-label` on ↻ Refresh, × Remove, ▾ toggle buttons
- [ ] `<main>` landmark wraps app content
- [ ] `COLOR.textSecondary` in `theme.ts` is `#595F6B`; applied in `App.tsx`, `SennaHeader.tsx`, `RunStatusCard.tsx`
- [ ] `CLAUDE.md` Arc 5 → CLOSED
- [ ] `npm run build` passes clean

---

## Arc 5 — This is the final arc

Once Arc 5 is reviewed and approved by Claude, the Senna UX redesign is complete. The 25-iteration arc series (5 arcs × 5 iterations) will be closed.

Remaining work for future sessions falls into two separate tracks:
- **Thesis prep** (backend): Full SBB YAML scenario, Trinidad agent profiles, validation benchmark runs — tracked in `docs/handoffs/HANDOFF_TO_BUILDER.md` Current focus § and backlog
- **Future Senna features**: SSE live chart, parallel experiment dispatch, real-time cost ticker — tracked in `SESSION_STATE.md` backlog

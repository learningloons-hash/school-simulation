# Senna UX Redesign — Arc 2 Handoff (to Cursor Architect)

**Prepared by:** Claude (Cowork / UX Design Architect)  
**Date:** 2026-04-20  
**Arc:** 2 of 5 — Run Setup Experience  
**Iterations:** senna-iter-6 through senna-iter-10  
**Backend:** Untouched. All changes are frontend-only.

---

## State entering Arc 2

Arc 1 is closed. The following is already in place:
- `SennaHeader` component with live status pill
- `runStatusCopy.ts` with plain-English status helpers (`getRunStatusLabel`, `getProgressLine`, `classifyRunStatusTone`)
- All tab labels renamed and split into two visual groups
- All form fields in plain English with Advanced options collapsible
- App background `#F7F6F2`, font stack `-apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif`
- Palette tokens in use: `#1A1A1A`, `#6B7280`, `#4A6FA5`, `#E5E3DC`, `#FFFFFF`, `#F7F6F2`

**The Set Up & Run tab right now** is a single vertical column: form section → Current run section → Recent runs section → Open run by ID section. All functional, all in plain English, but visually undifferentiated — no hierarchy, no breathing room, no empty states.

**Arc 2 goal:** Make the Set Up & Run tab feel like a product. A user who has never seen Senna before should be able to understand the available policy scenarios, configure a run, launch it, and find their history — without reading a manual.

---

## Design Philosophy (reminder)

75% Apple minimal, 25% practical warmth. Off-white background `#F7F6F2`. Accent `#4A6FA5`. Cards lift to `#FFFFFF`. No heavy chrome. Keep helper text where it genuinely helps.

**New in Arc 2 — component patterns to establish and reuse:**
- **Status pill:** already built in `SennaHeader` / `runStatusCopy.ts` — reuse `classifyRunStatusTone` for any status badge
- **Card:** `background: #FFFFFF`, `border: 1px solid #E5E3DC`, `border-radius: 10px`, `padding: 16px`
- **Primary button:** `background: #4A6FA5`, `color: #FFFFFF`, `border: none`, `border-radius: 8px`, `padding: 10px 20px`, `font-weight: 600`, `font-size: 15px`, `cursor: pointer` — for the main action on any section
- **Secondary button:** `background: #FFFFFF`, `color: #1A1A1A`, `border: 1px solid #E5E3DC`, `border-radius: 8px`, `padding: 8px 14px`, `font-size: 14px`
- **Section heading:** `font-size: 13px`, `font-weight: 600`, `color: #6B7280`, `text-transform: uppercase`, `letter-spacing: 0.5px`, `margin-bottom: 12px` — used as a label above a section

---

## Arc 2 — Iterations

---

### senna-iter-6 — Scenario Cards

**Goal:** Replace the policy scenario `<select>` dropdown with a set of clickable cards. Each card communicates what the scenario is about in plain English. The selected card is visually highlighted.

**New component:** `ScenarioSelector.tsx` in `frontend/src/components/`

**Props:**
```ts
type ScenarioPick = {
  id: string;
  name: string;
  rag_enabled: boolean;
  source: string;
};

type ScenarioSelectorProps = {
  scenarios: ScenarioPick[];
  selected: string;
  onChange: (id: string) => void;
};
```

**Built-in scenario descriptions (define in `ScenarioSelector.tsx`):**
```ts
const BUILTIN_DESCRIPTIONS: Record<string, string> = {
  psle_reform_mvp:
    "Simulate a stakeholder discussion about reforming the Primary School Leaving Examination — exploring how teachers, principals, and policymakers respond to proposed changes.",
  fsbb_comparator:
    "Explore how education stakeholders deliberate on Full Subject-Based Banding, a policy that allows students to take subjects at different levels based on ability.",
};
```

For any scenario not in `BUILTIN_DESCRIPTIONS`, fall back to: `"A custom scenario. Run the simulation to see how participants deliberate on this policy."`

**Card layout:**
```
┌─────────────────────────────────────────────────────┐
│  PSLE Reform                          ● Selected    │
│  Simulate a stakeholder discussion about reforming  │
│  the Primary School Leaving Examination…            │
└─────────────────────────────────────────────────────┘
```

- Cards stack vertically (display grid, 1 column). On screens wider than 700px, display 2 columns.
- Each card: `background: #FFFFFF`, `border: 1px solid #E5E3DC`, `border-radius: 10px`, `padding: 14px 16px`, `cursor: pointer`
- **Selected state:** `border: 2px solid #4A6FA5`, `background: #EEF3FA` (light blue tint)
- **Title:** `font-size: 15px`, `font-weight: 600`, `color: #1A1A1A`
- **Description:** `font-size: 13px`, `color: #6B7280`, `margin-top: 4px`, `line-height: 1.5`
- **Selected indicator:** a small pill — `border-radius: 999px`, `background: #4A6FA5`, `color: #FFFFFF`, `font-size: 11px`, `padding: 2px 8px`, text: "Selected" — top-right aligned within the card header row
- `rag_enabled` scenarios: no badge needed for now (the description handles it)

**In `App.tsx`:**
- Replace the `<label>` + `<select>` for Policy scenario with `<ScenarioSelector scenarios={runScenarioChoices} selected={scenarioId} onChange={setScenarioId} />`
- Add a section heading above it: `<div style={sectionHeadingStyle}>Policy scenario</div>`

**Definition of done:**
- [ ] `ScenarioSelector.tsx` created with card UI and built-in descriptions
- [ ] Selecting a card updates `scenarioId` state correctly
- [ ] Selected card is visually distinct (blue border + tint + "Selected" pill)
- [ ] No `<select>` dropdown remains for scenario selection
- [ ] Fallback description shown for any scenario not in `BUILTIN_DESCRIPTIONS`
- [ ] `npm run build` passes

**Closeout:** `docs/iterations/senna-iter-6-closeout.md`

---

### senna-iter-7 — Setup Form Visual Refinement & Primary Button

**Goal:** The Quick Setup form section gets a proper heading, more breathing room between fields, and a visually prominent "Start discussion" primary button. This iteration establishes the primary/secondary button pattern for the whole app.

**Changes to `App.tsx`:**

**1. Section heading above the form:**
Add above the setup `<section>`:
```tsx
<div style={sectionHeadingStyle}>Set up your discussion</div>
```
where `sectionHeadingStyle` is a constant:
```ts
const sectionHeadingStyle: React.CSSProperties = {
  fontSize: 13,
  fontWeight: 600,
  color: "#6B7280",
  textTransform: "uppercase",
  letterSpacing: "0.5px",
  marginBottom: 12,
};
```

**2. Form gap:**
Increase the `<section>` grid gap from `12` to `20`. This gives each field more breathing room.

**3. Field dividers (optional, tasteful):**
Between each field group (not between label and its helper text), add a subtle `<hr style={{ border: "none", borderTop: "1px solid #F0EEE8", margin: "4px 0" }} />`. This visually separates fields without being heavy. Apply between each top-level `<label>` block and between the `<details>` block — not inside the Advanced section.

**4. "Start discussion" primary button:**
Replace the existing plain `<button>` with the primary button style:
```tsx
<button
  type="button"
  onClick={() => void onStart()}
  disabled={status === "running" || status === "starting"}
  style={{
    background: status === "running" || status === "starting" ? "#9BAFC7" : "#4A6FA5",
    color: "#FFFFFF",
    border: "none",
    borderRadius: 8,
    padding: "12px 24px",
    fontWeight: 600,
    fontSize: 15,
    cursor: status === "running" || status === "starting" ? "not-allowed" : "pointer",
    width: "100%",
    marginTop: 4,
    fontFamily: "inherit",
    transition: "background 0.15s ease",
  }}
>
  {status === "starting" ? "Starting…" : status === "running" ? "Running…" : "Start discussion"}
</button>
```
- Disabled state uses muted blue `#9BAFC7` (not grey — it reads as "same action, temporarily unavailable")
- Full-width within the form card

**5. Advanced options summary styling:**
The `<summary>` inside `<details>` should look like a secondary link, not a heading:
```tsx
<summary style={{
  cursor: "pointer",
  fontSize: 13,
  color: "#4A6FA5",
  fontWeight: 500,
  listStyle: "none",
  display: "flex",
  alignItems: "center",
  gap: 6,
}}>
  ▸ Advanced options
</summary>
```
When open, the triangle character rotates to `▾` — this can be handled with CSS `details[open] > summary` if using a stylesheet, or just leave the static `▸` for now (Arc 5 handles full CSS).

**Definition of done:**
- [ ] Section heading "SET UP YOUR DISCUSSION" appears above form
- [ ] Form fields have noticeably more vertical breathing room (gap 20)
- [ ] Subtle field dividers between top-level sections
- [ ] "Start discussion" button is blue (`#4A6FA5`), full-width, bold
- [ ] Disabled state uses muted blue `#9BAFC7`
- [ ] Advanced options `<summary>` styled as a secondary link
- [ ] `npm run build` passes

**Closeout:** `docs/iterations/senna-iter-7-closeout.md`

---

### senna-iter-8 — Current Run Status Card

**Goal:** Redesign the "Current run" section below the setup form into a proper status card with a visual progress bar, clear action buttons, and a helpful empty state when no run is loaded.

**New component:** `RunStatusCard.tsx` in `frontend/src/components/`

**Props:**
```ts
type RunStatusCardProps = {
  status: string;
  runId: string | null;
  currentRound: number;
  totalRounds: number;
  convergedAtRound: number | null;
  transcriptLength: number;
  failureReason: string | null;
  onOpenLive: () => void;
  onOpenConversation: () => void;
  exportZipUrl: (id: string) => string;
  onDownloadJson: (id: string) => void;
};
```

**Empty state (runId is null and status is "idle"):**
```
┌──────────────────────────────────────────────┐
│                                              │
│   No discussion running yet.                 │
│   Set up your parameters above and press     │
│   "Start discussion" to begin.               │
│                                              │
└──────────────────────────────────────────────┘
```
- Card: `background: #FFFFFF`, `border: 1px solid #E5E3DC`, `border-radius: 10px`, `padding: 24px`
- Text: `fontSize: 14`, `color: #6B7280`, `textAlign: center`

**Active / completed state:**
```
┌──────────────────────────────────────────────┐
│  Current discussion                          │
│                                              │
│  [Status message — plain English]            │
│                                              │
│  ████████████░░░░  Round 3 of 5             │
│                                              │
│  [Watch Live]   [View Conversation]          │
│  [Download report ▾]                         │
└──────────────────────────────────────────────┘
```

**Progress bar:**
```tsx
// Show only when a run is loaded (runId is set)
<div style={{ margin: "12px 0" }}>
  <div style={{ display: "flex", justifyContent: "space-between", fontSize: 12, color: "#6B7280", marginBottom: 4 }}>
    <span>Progress</span>
    <span>Round {currentRound} of {totalRounds}</span>
  </div>
  <div style={{ background: "#E5E3DC", borderRadius: 999, height: 6, overflow: "hidden" }}>
    <div style={{
      background: status === "completed" ? "#4CAF82" : "#4A6FA5",
      borderRadius: 999,
      height: "100%",
      width: `${totalRounds > 0 ? Math.round((currentRound / totalRounds) * 100) : 0}%`,
      transition: "width 0.4s ease",
    }} />
  </div>
</div>
```
- Completed: bar fills green (`#4CAF82`)
- Running: bar fills blue (`#4A6FA5`)
- `width` transitions smoothly as `currentRound` increases

**Action buttons (when runId is set):**
- "Watch Live" → secondary button → calls `onOpenLive()`
- "View Conversation" → secondary button (shown when `transcriptLength > 0`) → calls `onOpenConversation()`
- "Download report" → secondary button with a small ▾ arrow — for now this triggers the ZIP download directly (`href={exportZipUrl(runId)}`). Arc 3 will add a proper dropdown.

**Failure state:**
```tsx
{failureReason ? (
  <div style={{ marginTop: 12, padding: 12, background: "#FEE2E2", borderRadius: 8, fontSize: 13, color: "#991B1B" }}>
    <strong>Something went wrong:</strong> {failureReason}
  </div>
) : null}
```

**Remove from this section:**
- "Run id: {runId ?? '(none)'}" — remove entirely from this card. Run ID stays in Run Details tab only.
- "Download JSON" as a separate button — consolidate into "Download report" (just ZIP for now; Arc 3 redesigns exports)

**In `App.tsx`:**
Replace the existing `<section style={{ marginTop: 18 }}>` Current run block with:
```tsx
<div style={{ marginTop: 24 }}>
  <div style={sectionHeadingStyle}>Current discussion</div>
  <RunStatusCard
    status={status}
    runId={runId}
    currentRound={currentRound}
    totalRounds={totalRounds}
    convergedAtRound={convergedAtRound}
    transcriptLength={transcript.length}
    failureReason={failureReason}
    onOpenLive={() => setActiveTab("live")}
    onOpenConversation={() => setActiveTab("transcript")}
    exportZipUrl={exportZipUrl}
    onDownloadJson={(id) => downloadExportJson(id).catch((e) => setStatus(`error: ${String(e)}`))}
  />
</div>
```

**Definition of done:**
- [ ] `RunStatusCard.tsx` created
- [ ] Empty state shown when `runId` is null and status is `idle`
- [ ] Progress bar renders and updates as `currentRound` increases
- [ ] Bar turns green on `completed`
- [ ] "Watch Live" and "View Conversation" buttons navigate to correct tabs
- [ ] Raw Run ID no longer visible in this section
- [ ] "Download JSON" consolidated — ZIP download only for now
- [ ] Failure state shows in red card
- [ ] `npm run build` passes

**Closeout:** `docs/iterations/senna-iter-8-closeout.md`

---

### senna-iter-9 — Run History Redesign

**Goal:** Replace the raw run list (monospace IDs, raw status strings, raw scenario_ids) with a proper history panel that shows human-readable timestamps, scenario names, status badges, and clean actions.

**Changes to `App.tsx` — "Recent runs" section:**

**Section heading:**
```tsx
<div style={{ ...sectionHeadingStyle, marginTop: 28 }}>Recent discussions</div>
```

**Empty state (runList.length === 0):**
```tsx
<div style={{
  background: "#FFFFFF",
  border: "1px solid #E5E3DC",
  borderRadius: 10,
  padding: 24,
  textAlign: "center",
  fontSize: 14,
  color: "#6B7280",
}}>
  No previous discussions yet. Start one above.
</div>
```

**Run list item — redesigned:**

Each `<li>` becomes a card row:
```
┌─────────────────────────────────────────────────────────┐
│  PSLE Reform                   ● Finished    14 Apr     │
│  4 of 4 rounds · 10 participants                        │
│  [Open]  [Download]                                     │
└─────────────────────────────────────────────────────────┘
```

**Scenario name:** map `r.scenario_id` to a display name using `runScenarioChoices` catalog:
```ts
const scenarioName = runScenarioChoices.find(s => s.id === r.scenario_id)?.name ?? r.scenario_id;
```

**Timestamp:** format `r.created_at` as a relative or short absolute date:
```ts
function formatRunDate(iso: string | null | undefined): string {
  if (!iso) return "";
  const d = new Date(iso);
  const now = new Date();
  const diffDays = Math.floor((now.getTime() - d.getTime()) / 86_400_000);
  if (diffDays === 0) return "Today";
  if (diffDays === 1) return "Yesterday";
  if (diffDays < 7) return `${diffDays} days ago`;
  return d.toLocaleDateString(undefined, { day: "numeric", month: "short" });
}
```

**Status badge:** use `classifyRunStatusTone(r.status)` from `runStatusCopy.ts` and the `PILL_TONE_STYLE` map (import from `SennaHeader` or move to `runStatusCopy.ts` for shared use). Badge label: short form only:
```ts
function shortStatusLabel(status: string): string {
  if (status === "completed") return "Finished";
  if (status === "running") return "In progress";
  if (status === "failed") return "Failed";
  if (status === "starting") return "Starting";
  if (status.startsWith("error:")) return "Error";
  return status;
}
```

**Participant count:** `r.agent_limit` — if available on `SimulationListItem`. Check the type; if not present, omit this line (do not add it to the API — backend is frozen).

**Actions:**
- "Open" → secondary button → `loadRunById(r.id)` — then auto-switch to Watch Live tab if status is "running", or Conversation tab if "completed"
- "Download" → small secondary button → `href={exportZipUrl(r.id)}`, `download` attribute

**"Open run by ID" section:**
- Rename heading to "Load a previous discussion by ID"
- Keep the input and button but style the input with `border: 1px solid #E5E3DC`, `border-radius: 8px`, `padding: 8px 12px`
- Button uses secondary button style

**Refresh button:**
- Remove the "Refresh list" button from above the list — replace with auto-refresh on tab focus. Add a `useEffect` that calls `refreshRuns()` whenever `activeTab === "controls"`. Keep the manual button as a small `↻` icon-text link below the list heading: `<button style={{ fontSize: 12, color: "#6B7280", background: "none", border: "none", cursor: "pointer" }}>↻ Refresh</button>`

> **Note on `agent_limit`:** Check `SimulationListItem` type in `api.ts`. If `agent_limit` is not on that type, do not add it to the API — just omit the participant count from the history card.

**Definition of done:**
- [ ] Scenario names shown (not raw `scenario_id` strings)
- [ ] Human-readable dates shown (relative or short absolute)
- [ ] Status badges use colour from `classifyRunStatusTone`
- [ ] Empty state shown when no runs
- [ ] "Open" button loads run and navigates to appropriate tab
- [ ] Raw monospace run ID removed from card face (still used internally for load/download)
- [ ] Auto-refresh on tab focus added
- [ ] `npm run build` passes

**Closeout:** `docs/iterations/senna-iter-9-closeout.md`

---

### senna-iter-10 — Set Up & Run Tab: Layout & Empty States

**Goal:** Pull together all of Arc 2's components into a coherent page layout. On wider screens, the setup form and the run status/history panel sit side-by-side. On narrow screens, they stack. Add polish to empty states throughout the tab.

**Layout structure:**

```
┌────────────────────────────────────────────────────────┐
│  SET UP YOUR DISCUSSION         CURRENT DISCUSSION     │
│  ┌──────────────────────┐      ┌────────────────────┐  │
│  │  ScenarioSelector    │      │  RunStatusCard     │  │
│  │  ──────────────────  │      │  (empty or live)   │  │
│  │  Discussion rounds   │      └────────────────────┘  │
│  │  Participants        │                              │
│  │  Turns per round     │      RECENT DISCUSSIONS      │
│  │  AI model            │      ┌────────────────────┐  │
│  │  ─ Advanced ─        │      │  Run history list  │  │
│  │                      │      │  (or empty state)  │  │
│  │  [Start discussion]  │      └────────────────────┘  │
│  └──────────────────────┘                              │
└────────────────────────────────────────────────────────┘
```

**Implementation:**

Wrap the Set Up & Run tab content in a two-column CSS grid:
```tsx
<div style={{
  display: "grid",
  gridTemplateColumns: "minmax(0, 1fr) minmax(0, 1fr)",
  gap: 24,
  alignItems: "start",
}}>
  {/* Left column */}
  <div>
    <div style={sectionHeadingStyle}>Set up your discussion</div>
    <section style={cardStyle}>
      {/* ScenarioSelector + form fields + Advanced + Start button */}
    </section>
  </div>

  {/* Right column */}
  <div>
    <div style={sectionHeadingStyle}>Current discussion</div>
    <RunStatusCard … />

    <div style={{ ...sectionHeadingStyle, marginTop: 28 }}>Recent discussions</div>
    {/* Run history list */}

    <div style={{ marginTop: 20 }}>
      <div style={sectionHeadingStyle}>Load by ID</div>
      {/* Open run by ID */}
    </div>
  </div>
</div>
```

**Responsive behaviour:**
On narrow screens (< 700px), collapse to single column:
```tsx
// Simple approach: use a state or just set a narrower breakpoint via inline style
// For now, use a fixed breakpoint check via window.innerWidth at render time
// Arc 5 will handle proper responsive CSS — for now, a simple approach is acceptable
const isWide = typeof window !== "undefined" && window.innerWidth >= 700;

style={{
  display: "grid",
  gridTemplateColumns: isWide ? "minmax(0, 1fr) minmax(0, 1fr)" : "1fr",
  gap: 24,
  alignItems: "start",
}}
```

> **Arc 5 note:** This simple `window.innerWidth` check is a placeholder. Arc 5 (responsive pass) will replace it with a proper CSS media query or `ResizeObserver` approach. Do not over-engineer responsiveness in Arc 2.

**Card style constant:**
Define once near the top of `App.tsx` and reuse:
```ts
const cardStyle: React.CSSProperties = {
  background: "#FFFFFF",
  border: "1px solid #E5E3DC",
  borderRadius: 10,
  padding: 20,
};
```

**Empty states audit — add to any section that doesn't already have one:**
- Conversation tab: if `transcript.length === 0`: *"No conversation yet. Start a discussion from the Set Up & Run tab."*
- Results tab: if `outcomeIndicators.length === 0`: *"Results will appear here once a discussion is complete."*
- Attitudes tab: if `stateTimeline.length === 0`: *"Attitude data will appear here as the discussion progresses."*
- Run Details tab: if `configSnapshot === null`: *"Run details will appear here once a discussion is loaded."*

These empty states use the same pattern: white card, centred `#6B7280` text, 14px.

**Definition of done:**
- [ ] Two-column layout renders on wide screens; collapses to single column on narrow screens
- [ ] Left column: form (ScenarioSelector + fields + Advanced + Start button)
- [ ] Right column: RunStatusCard + run history + load-by-ID
- [ ] `cardStyle` constant defined and used consistently across the tab
- [ ] Empty states added to Conversation, Results, Attitudes, and Run Details tabs
- [ ] No layout regressions on the other tabs (check each one)
- [ ] `npm run build` passes

**Closeout:** `docs/iterations/senna-iter-10-closeout.md`

---

## Arc 2 — Architect Instructions

Work through iterations **sequentially**: senna-iter-6 → 7 → 8 → 9 → 10.

**Builder bootstrap (paste into each new Cursor Builder chat):**

> You are implementing the Senna UX redesign in `mirofish-mvp/frontend/`. Read in order:
> 1. `docs/SESSION_STATE.md`
> 2. `docs/handoffs/HANDOFF_SENNA_ARC1.md` — for design palette and patterns established in Arc 1
> 3. `docs/handoffs/HANDOFF_SENNA_ARC2.md` — full spec for Arc 2 (this file)
> 4. Then jump to the **senna-iter-N** section for the current iteration.
>
> Rules: Frontend only (backend untouched). Match existing code style. Run `npm run build` in `frontend/` after changes. Write `docs/iterations/senna-iter-N-closeout.md` when done. Do not expand scope beyond the active iteration spec.

**Key dependencies between iterations:**
- Iter 8 (`RunStatusCard`) uses `classifyRunStatusTone` and `getRunStatusLabel` from `runStatusCopy.ts` — already exists from Arc 1
- Iter 9 (run history) uses `classifyRunStatusTone` — import from `runStatusCopy.ts`; consider moving `PILL_TONE_STYLE` there too for reuse
- Iter 10 uses `RunStatusCard` (Iter 8) and the history list (Iter 9) — must be done last
- Iters 6 and 7 are independent of each other and of 8/9, so Architect can seed them in order but either can be revisited without breaking the other

---

## Arc 2 — Definition of Arc Complete

- [ ] Scenario cards replace the dropdown — selected state visually clear
- [ ] Setup form has heading, breathing room, and a blue primary "Start discussion" button
- [ ] `RunStatusCard` shows progress bar, status, and actions — no raw Run ID visible
- [ ] Run history shows scenario name, relative date, status badge, and clean actions
- [ ] Two-column layout on wide screens, single column on narrow
- [ ] Empty states on Conversation, Results, Attitudes, Run Details tabs
- [ ] `npm run build` passes clean

---

## Arc 2 — Summary Template (Architect fills on completion)

```
Arc 2 complete — [date]
Iterations shipped: senna-iter-6, 7, 8, 9, 10
Build: PASS / FAIL
Deferred items: [list anything deferred]
Notes for Claude review: [anything the UX architect should pay attention to]
```

---

## What Comes Next (Arc 3 preview)

Arc 3 (Live Experience & Results) makes the running and completed simulation readable and meaningful. Key work: plain-English labels on the Live dashboard charts, the iMessage-style Conversation view redesign, a plain-English Results summary, the Attitudes timeline, and a cleaner export/download flow.

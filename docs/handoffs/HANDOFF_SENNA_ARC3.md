# Senna UX Redesign — Arc 3 Handoff (to Cursor Architect)

**Prepared by:** Claude (Cowork / UX Design Architect)  
**Date:** 2026-04-20  
**Arc:** 3 of 5 — Live Experience & Results  
**Iterations:** senna-iter-11 through senna-iter-15  
**Backend:** Untouched. All changes are frontend-only.

---

## State entering Arc 3

Arcs 1 and 2 are closed. The following is in place:
- `SennaHeader`, `ScenarioSelector`, `RunStatusCard` components
- `runStatusCopy.ts` with shared status helpers and `classifyRunStatusTone`
- Two-column layout on Set Up & Run tab, `cardStyle` / `emptyStateCardStyle` / `sectionHeadingStyle` constants
- Palette: `#F7F6F2` bg, `#FFFFFF` card, `#1A1A1A` text, `#6B7280` secondary, `#4A6FA5` accent, `#E5E3DC` border
- System font stack on root `<div>`

**The problem Arc 3 solves:** the back-half of the app is still completely raw. The Watch Live tab has developer notes and monospace jargon. The Conversation tab renders agent turns as a `<pre>` wall of text. The Results tab is a raw data list. The Attitudes tab dumps agent state as compact inline strings with JSON blobs. The Run Details tab shows a raw JSON config snapshot. A non-technical user looking at any of these tabs would be lost.

**Arc 3 goal:** Everything a user sees after a discussion runs should be readable and meaningful — no raw keys, no `<pre>` JSON, no developer documentation visible in the UI.

---

## Design Philosophy (reminder)

75% Apple minimal, 25% practical warmth. The 25% is especially important in Arc 3 — results data needs enough context and labelling to be understood, not just prettified. Don't strip labels in the name of minimalism.

**Established patterns to keep using:**
- `cardStyle`, `emptyStateCardStyle`, `sectionHeadingStyle` — defined in `App.tsx`, use consistently
- Secondary button style from Arc 2
- `classifyRunStatusTone` for any status colouring

**New pattern introduced in Arc 3 — metric card:**
```ts
const metricCardStyle: React.CSSProperties = {
  background: "#FFFFFF",
  border: "1px solid #E5E3DC",
  borderRadius: 10,
  padding: "14px 16px",
};
// Label above value:
// label: fontSize 12, color #6B7280, marginBottom 4, fontWeight 500
// value: fontSize 22, fontWeight 600, color #1A1A1A
// subtext: fontSize 12, color #6B7280, marginTop 4
```

---

## Arc 3 — Iterations

---

### senna-iter-11 — Watch Live: Plain-English Labels

**Goal:** Remove all developer-facing text from `LiveRunDashboard.tsx`. Rename every metric label, section heading, and data field to plain English. The dashboard should be readable by a non-researcher watching a simulation run.

**File to edit:** `frontend/src/components/LiveRunDashboard.tsx`

**1. Remove the developer note div entirely:**
Delete this block completely — it is not user-facing content:
```tsx
<div style={{ fontSize: 14, opacity: 0.85, maxWidth: 720 }}>
  Data updates from the same <code>GET /simulations/{"{id}"}</code> payload ...
  See <code>docs/plans/iteration-8-live-dashboard-design.md</code> ...
</div>
```

**2. Convergence banner — plain English:**
Current: `"Converged at round {N} (threshold X.XXXX, patience Y)"`  
New:
```tsx
<div style={{ padding: "10px 14px", borderRadius: 8, background: "#ECFDF5", border: "1px solid #6EE7B7", fontSize: 14 }}>
  ✓ Consensus reached at Round <strong>{convergedAtRound}</strong> — the discussion stabilised and stopped early.
</div>
```
Remove the raw `threshold` / `patience` figures from this banner entirely (they belong in Run Details).

**3. Stats cards — rename all fields:**

| Current label | New label |
|---------------|-----------|
| Status | Discussion status |
| Run id (raw UUID) | **Remove entirely** from this component |
| Progress → "Rounds completed: N / M" | Rounds completed: N of M |
| Transcript turns | Exchanges so far |
| `agent_limit (config): N` | Participants: N |
| `simulation_mode: full_round_robin` | Turn style: Everyone speaks each round |
| `simulation_mode: sample_k_per_round · K=N` | Turn style: Rotating speakers (N per round) |
| `population: schema vX · pool Y rows · weighted` | Participant pool: Y people, weighted sampling |

For the status value, use `getRunStatusLabel` from `runStatusCopy.ts` (already imported in `App.tsx` — pass it as a prop or import directly).

**4. Section headings:**

| Current | New |
|---------|-----|
| Global state (by completed round) | Opinion trends by round |
| Round outcomes | Round-by-round outcomes |
| Agents (latest round snapshot + series) | Participants |

**5. Sparkline labels (the small text above each chart):**

| Current | New |
|---------|-----|
| Implementation readiness | Readiness to adopt |
| Alignment index | Level of agreement |
| Convergence δ (rounds 2+) | Opinion change rate |
| Adoption momentum | Adoption momentum |

Remove `label="..."` props from `<Sparkline>` components — these are tooltip/ARIA labels that still say the raw key name. Replace with the plain-English equivalents above.

**6. Agent cards:**

Current agent card body:
```
Latest: support 0.72 · resistance 0.28 · workload 0.41 · supporter
```
New format:
```
Support: 72%  ·  Resistance: 28%  ·  Workload: 41%  ·  Stance: supporter
```
Implementation:
```tsx
<div style={{ fontSize: 12, color: "#6B7280" }}>
  Support: {((agent?.support_level ?? 0) * 100).toFixed(0)}% &nbsp;·&nbsp;
  Resistance: {((agent?.resistance_level ?? 0) * 100).toFixed(0)}% &nbsp;·&nbsp;
  Workload: {((agent?.workload_stress ?? 0) * 100).toFixed(0)}% &nbsp;·&nbsp;
  Stance: {agent?.belief_posture ?? "unknown"}
</div>
```

Sparkline row labels:
- `support` → "Support"
- `resistance` → "Resistance"  
- `workload` → "Workload"

**7. Outcomes table headers:**

| Current | New |
|---------|-----|
| Round | Round |
| Adoption | Adoption score |
| Conflicts | Disagreements |
| Consistency | Consistency score |

**8. Empty state for outcomes:**
Current: `"No outcome rows yet (first row appears after round 1 completes)."`  
New — use `emptyStateCardStyle` (pass as a prop or define locally with same values):
```tsx
<div style={emptyStateCardStyle}>
  Outcomes will appear after the first round completes.
</div>
```

**9. Agent section empty state:**
Current: `"No agent state until at least one round completes."`  
New:
```tsx
<div style={emptyStateCardStyle}>
  Participant data will appear after the first round completes.
</div>
```

> **Note on `emptyStateCardStyle`:** This constant is defined in `App.tsx`. Either pass it as a prop to `LiveRunDashboard`, redefine it locally (same values: `background #FFFFFF, border 1px solid #E5E3DC, borderRadius 10, padding 24, textAlign center, fontSize 14, color #6B7280`), or extract it to a shared file. Extracting to `frontend/src/lib/styles.ts` is the cleanest option for Arc 3+ — Architect's call.

**Definition of done:**
- [ ] Developer note div removed
- [ ] Raw metric keys (`implementation_readiness`, `alignment_index`, etc.) absent from all visible labels
- [ ] `agent_limit`, `simulation_mode`, `convergence_threshold/patience` shown in plain English or removed
- [ ] Run ID removed from this component
- [ ] Agent card shows "Support: X%  ·  Resistance: X%  ·  Workload: X%"
- [ ] Outcomes table uses plain headers
- [ ] `npm run build` passes

**Closeout:** `docs/iterations/senna-iter-11-closeout.md`

---

### senna-iter-12 — Conversation View (iMessage-style)

**Goal:** Replace the `<pre>` transcript dump with a proper conversation thread. Each turn is a speech bubble with a coloured role avatar, agent name, role badge, round tag, and the message as readable prose. Technical metadata (interaction type, intent, fidelity tier, LLM model) collapses behind a Details toggle.

**New component:** `ConversationView.tsx` in `frontend/src/components/`

**Props:**
```ts
import type { SimulationTurn } from "../lib/api";

type ConversationViewProps = {
  turns: SimulationTurn[];
};
```

**Role-to-colour map (define inside the component):**
```ts
const ROLE_COLORS: Record<string, string> = {
  teacher: "#4A90D9",
  principal: "#7B68EE",
  ministry_official: "#E8A838",
  ministry: "#E8A838",
  parent: "#52C278",
  researcher: "#E06666",
  academic: "#E06666",
  default: "#8B8FA8",
};

function roleColor(role: string): string {
  const key = role.toLowerCase().replace(/\s+/g, "_");
  return ROLE_COLORS[key] ?? ROLE_COLORS.default;
}
```

**Initials avatar:**
```ts
function initials(name: string): string {
  return name
    .split(" ")
    .map((w) => w[0] ?? "")
    .join("")
    .slice(0, 2)
    .toUpperCase();
}
```

**Turn card layout:**
```
┌─────────────────────────────────────────────────────┐
│  ●A  Alice Tan                [Teacher]   Round 2   │
│                                                     │
│  As a teacher with 15 years of experience, I        │
│  believe this policy change will require...         │
│                                                     │
│  ▸ Details                                          │
└─────────────────────────────────────────────────────┘
```

**Implementation:**
```tsx
export function ConversationView({ turns }: ConversationViewProps) {
  if (turns.length === 0) {
    return (
      <div style={{ background: "#FFFFFF", border: "1px solid #E5E3DC", borderRadius: 10, padding: 24,
        textAlign: "center", fontSize: 14, color: "#6B7280" }}>
        No conversation yet. Start a discussion from the Set Up &amp; Run tab.
      </div>
    );
  }

  return (
    <div style={{ display: "grid", gap: 16 }}>
      {turns.map((t, idx) => {
        const color = roleColor(t.agent_role);
        const avatarInitials = initials(t.agent_name);
        return (
          <TurnBubble key={`${t.id ?? "turn"}-${idx}`} turn={t} color={color} avatarInitials={avatarInitials} />
        );
      })}
    </div>
  );
}
```

**`TurnBubble` sub-component (define in same file):**
```tsx
function TurnBubble({ turn, color, avatarInitials }: { turn: SimulationTurn; color: string; avatarInitials: string }) {
  const [open, setOpen] = React.useState(false);

  // Format role for display
  const roleDisplay = turn.agent_role
    .replace(/_/g, " ")
    .replace(/\b\w/g, (c) => c.toUpperCase());

  return (
    <div style={{ background: "#FFFFFF", border: "1px solid #E5E3DC", borderRadius: 12, padding: "16px 20px",
      borderLeft: `4px solid ${color}` }}>
      
      {/* Header row */}
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between",
        flexWrap: "wrap", gap: 8, marginBottom: 12 }}>
        <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
          {/* Avatar circle */}
          <div style={{ width: 32, height: 32, borderRadius: "50%", background: color,
            color: "#FFFFFF", fontSize: 12, fontWeight: 700, display: "flex",
            alignItems: "center", justifyContent: "center", flexShrink: 0 }}>
            {avatarInitials}
          </div>
          {/* Name */}
          <span style={{ fontWeight: 600, fontSize: 15, color: "#1A1A1A" }}>{turn.agent_name}</span>
          {/* Role badge */}
          <span style={{ fontSize: 11, fontWeight: 500, color: color,
            background: `${color}18`, borderRadius: 999, padding: "2px 8px" }}>
            {roleDisplay}
          </span>
        </div>
        {/* Round tag */}
        <span style={{ fontSize: 12, color: "#6B7280", flexShrink: 0 }}>Round {turn.round_number}</span>
      </div>

      {/* Message body */}
      <div style={{ fontSize: 15, color: "#1A1A1A", lineHeight: 1.6, whiteSpace: "pre-wrap" }}>
        {turn.raw_response}
      </div>

      {/* Details toggle */}
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        style={{ marginTop: 12, fontSize: 12, color: "#6B7280", background: "none", border: "none",
          cursor: "pointer", padding: 0, display: "flex", alignItems: "center", gap: 4 }}
      >
        {open ? "▾" : "▸"} Details
      </button>

      {open ? (
        <div style={{ marginTop: 8, fontSize: 12, color: "#6B7280", display: "grid", gap: 4,
          padding: "10px 12px", background: "#F7F6F2", borderRadius: 8 }}>
          {turn.interaction_type ? (
            <div>Interaction: {turn.interaction_type.replace(/_/g, " ")}</div>
          ) : null}
          {turn.target_agent_name ?? turn.target_scope ? (
            <div>Directed to: {turn.target_agent_name ?? turn.target_scope}</div>
          ) : null}
          {turn.intent_tag ? (
            <div>Intent: {turn.intent_tag.replace(/_/g, " ")}</div>
          ) : null}
          {turn.fidelity_tier != null ? (
            <div>Fidelity tier: {turn.fidelity_tier}</div>
          ) : null}
          {turn.effective_provider || turn.effective_model ? (
            <div>AI model: {[turn.effective_provider, turn.effective_model].filter(Boolean).join(" / ")}</div>
          ) : null}
        </div>
      ) : null}
    </div>
  );
}
```

**In `App.tsx`:**
- Import `ConversationView` 
- Replace the Conversation tab's `transcript.map(...)` block with `<ConversationView turns={transcript} />`
- The empty state is now handled inside `ConversationView` — remove the outer empty state check for this tab (or keep it as a guard, either is fine)

**Definition of done:**
- [ ] `ConversationView.tsx` created with `TurnBubble` sub-component
- [ ] Each turn shows: coloured avatar circle, agent name, role badge (colour-matched), round number, message as readable prose
- [ ] Left colour border on card uses role colour
- [ ] Role displayed as human-readable (underscores replaced, title-cased)
- [ ] Details toggle collapses/expands: interaction type, directed to, intent, fidelity tier, AI model
- [ ] `<pre>` tag gone — `raw_response` renders as `<div>` with `white-space: pre-wrap` and readable font size
- [ ] `npm run build` passes

**Architect gate:** This iteration is the Arc 3 centrepiece — iMessage-style bubbles (colour left edge, role avatar, collapsible **Details**) matter more visually than in prior iterations. **Do not mark PASS from closeout text alone**; confirm in the running app (or screenshots) that hierarchy, spacing, and bubble readability match the spec before signing off.

**Closeout:** `docs/iterations/senna-iter-12-closeout.md`

---

### senna-iter-13 — Results Tab: Plain-English Summary

**Goal:** Replace the raw "Round N: adoption=0.xx · conflicts=N · consistency=0.xx" list with a proper results view: a plain-English narrative summary block at the top, followed by a clean readable table.

**Changes to `App.tsx` — Outcomes section:**

**1. Narrative summary block:**

Compute these values from available data:
```ts
const firstState = stateTimeline[0]?.global_state;
const lastState = stateTimeline[stateTimeline.length - 1]?.global_state;
const firstReadiness = firstState?.implementation_readiness ?? null;
const lastReadiness = lastState?.implementation_readiness ?? null;
const firstAlignment = firstState?.alignment_index ?? null;
const lastAlignment = lastState?.alignment_index ?? null;
const totalConflicts = outcomeIndicators.reduce((sum, o) => sum + (o.conflict_events ?? 0), 0);
const totalRoundsCompleted = stateTimeline.length;
```

Helper to translate 0–1 float to plain-English level:
```ts
function readinessLevel(v: number | null): string {
  if (v === null) return "unknown";
  if (v < 0.33) return "low";
  if (v < 0.66) return "moderate";
  return "high";
}
```

Render the summary above the table only when `stateTimeline.length > 0`:
```tsx
{stateTimeline.length > 0 && (
  <div style={{ background: "#FFFFFF", border: "1px solid #E5E3DC", borderRadius: 10,
    padding: "18px 20px", marginBottom: 20, fontSize: 14, lineHeight: 1.7, color: "#1A1A1A" }}>
    <div style={{ fontWeight: 600, marginBottom: 8, fontSize: 15 }}>Discussion summary</div>
    <p style={{ margin: "0 0 8px 0" }}>
      After <strong>{totalRoundsCompleted}</strong> round{totalRoundsCompleted !== 1 ? "s" : ""} of discussion
      {convergedAtRound != null
        ? `, the group reached consensus at Round ${convergedAtRound} and the discussion stopped early`
        : ""},
      {" "}readiness to adopt the policy
      {firstReadiness !== null && lastReadiness !== null
        ? ` moved from <strong>${readinessLevel(firstReadiness)}</strong> to <strong>${readinessLevel(lastReadiness)}</strong>`
        : " was tracked across all rounds"}.
    </p>
    {firstAlignment !== null && lastAlignment !== null && (
      <p style={{ margin: "0 0 8px 0" }}>
        Group agreement {lastAlignment > firstAlignment ? "rose" : lastAlignment < firstAlignment ? "fell" : "held steady"}
        {" "}from <strong>{Math.round(firstAlignment * 100)}%</strong> to <strong>{Math.round(lastAlignment * 100)}%</strong>.
      </p>
    )}
    {totalConflicts > 0 && (
      <p style={{ margin: 0 }}>
        There {totalConflicts === 1 ? "was" : "were"} <strong>{totalConflicts}</strong> moment{totalConflicts !== 1 ? "s" : ""} of disagreement across the discussion.
      </p>
    )}
  </div>
)}
```

> **JSX note:** React does not support `<strong>` inside template literals. Refactor the sentences above into proper JSX fragments rather than string interpolation when `<strong>` is needed. The structure above illustrates the content — Cursor should render it correctly as JSX.

**2. Replace raw outcome list with a clean table:**

```tsx
{outcomeIndicators.length > 0 && (
  <div style={{ overflowX: "auto" }}>
    <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 13 }}>
      <thead>
        <tr style={{ borderBottom: "2px solid #E5E3DC" }}>
          <th style={{ padding: "8px 12px", textAlign: "left", color: "#6B7280", fontWeight: 600 }}>Round</th>
          <th style={{ padding: "8px 12px", textAlign: "left", color: "#6B7280", fontWeight: 600 }}>Adoption score</th>
          <th style={{ padding: "8px 12px", textAlign: "left", color: "#6B7280", fontWeight: 600 }}>Disagreements</th>
          <th style={{ padding: "8px 12px", textAlign: "left", color: "#6B7280", fontWeight: 600 }}>Consistency score</th>
        </tr>
      </thead>
      <tbody>
        {outcomeIndicators.map((o) => (
          <tr key={o.round_number} style={{ borderBottom: "1px solid #F0EEE8" }}>
            <td style={{ padding: "8px 12px", color: "#1A1A1A" }}>{o.round_number}</td>
            <td style={{ padding: "8px 12px", color: "#1A1A1A" }}>{o.adoption_momentum.toFixed(2)}</td>
            <td style={{ padding: "8px 12px", color: "#1A1A1A" }}>{o.conflict_events}</td>
            <td style={{ padding: "8px 12px", color: "#1A1A1A" }}>{o.consistency_index.toFixed(2)}</td>
          </tr>
        ))}
      </tbody>
    </table>
  </div>
)}
```

**Definition of done:**
- [ ] Discussion summary block renders above the table when data is available
- [ ] Summary uses plain-English readiness levels (low / moderate / high)
- [ ] Convergence note shown in summary when `convergedAtRound` is set
- [ ] Agreement change direction (rose / fell / held steady) computed correctly
- [ ] Outcomes table uses clean headers (Adoption score, Disagreements, Consistency score)
- [ ] Raw "adoption=0.xx · conflicts=N" list is gone
- [ ] **JSX:** Narrative summary uses real JSX (`<strong>…</strong>`, fragments, conditional branches) — never `<strong>` inside template literals / string interpolation (invalid React; breaks build or renders literal tag text). See **JSX note** above the example block.
- [ ] `npm run build` passes

**Closeout:** `docs/iterations/senna-iter-13-closeout.md`

---

### senna-iter-14 — Attitudes Tab: Readable Agent State

**Goal:** Replace the compact agent state strings and raw JSON blobs in the Attitudes (State) tab with a readable, card-based layout. Each round card shows global metrics in plain English, and each agent's state as a clean labelled list — no raw key names, no JSON dumps.

**Changes to `App.tsx` — State timeline section:**

**1. Global state per round:**

Current:
```
Global readiness: 0.67 · alignment: 0.78
```
New:
```tsx
<div style={{ display: "flex", flexWrap: "wrap", gap: 16, marginBottom: 12 }}>
  <div>
    <div style={{ fontSize: 11, color: "#6B7280", fontWeight: 500, textTransform: "uppercase", letterSpacing: "0.4px" }}>
      Readiness to adopt
    </div>
    <div style={{ fontSize: 20, fontWeight: 600, color: "#1A1A1A" }}>
      {Math.round((round.global_state?.implementation_readiness ?? 0) * 100)}%
    </div>
  </div>
  <div>
    <div style={{ fontSize: 11, color: "#6B7280", fontWeight: 500, textTransform: "uppercase", letterSpacing: "0.4px" }}>
      Level of agreement
    </div>
    <div style={{ fontSize: 20, fontWeight: 600, color: "#1A1A1A" }}>
      {Math.round((round.global_state?.alignment_index ?? 0) * 100)}%
    </div>
  </div>
  {round.global_state?.convergence_delta != null && (
    <div>
      <div style={{ fontSize: 11, color: "#6B7280", fontWeight: 500, textTransform: "uppercase", letterSpacing: "0.4px" }}>
        Opinion change rate
      </div>
      <div style={{ fontSize: 20, fontWeight: 600, color: "#1A1A1A" }}>
        {round.global_state.convergence_delta.toFixed(3)}
      </div>
    </div>
  )}
</div>
```

**2. Agent rows per round:**

Current (compact single line with raw JSON):
```
Alice Tan (teacher) [45/F/Chinese/middle] support=0.72 resistance=0.28 workload=0.41 posture=supporter
{...JSON blob...}
```

New — each agent gets a small card inside the round card:
```tsx
{(round.agents ?? []).map((agent) => (
  <div key={`${round.round_number}-${agent.agent_id}`}
    style={{ background: "#F7F6F2", borderRadius: 8, padding: "10px 12px", fontSize: 13 }}>
    <div style={{ fontWeight: 600, color: "#1A1A1A", marginBottom: 6 }}>
      {agent.agent_name}
      <span style={{ fontWeight: 400, color: "#6B7280", marginLeft: 6 }}>
        {agent.agent_role.replace(/_/g, " ")}
      </span>
    </div>
    <div style={{ display: "flex", flexWrap: "wrap", gap: 16, fontSize: 12, color: "#6B7280" }}>
      <span>Support <strong style={{ color: "#1A1A1A" }}>{Math.round(agent.support_level * 100)}%</strong></span>
      <span>Resistance <strong style={{ color: "#1A1A1A" }}>{Math.round(agent.resistance_level * 100)}%</strong></span>
      <span>Workload <strong style={{ color: "#1A1A1A" }}>{Math.round(agent.workload_stress * 100)}%</strong></span>
      <span>Stance <strong style={{ color: "#1A1A1A" }}>{agent.belief_posture ?? "—"}</strong></span>
    </div>
  </div>
))}
```

**3. Remove completely:**
- Demographics inline string (`[45/F/Chinese/middle]`) — demographics are technical research data, not needed in this view
- `attribute_sections` JSON `<pre>` block — this is deep research data, remove from Attitudes tab entirely. It can live in the raw export ZIP for researchers who need it.

**4. Round card style:**
Wrap each round in a card using `cardStyle` (or its values: `background #FFFFFF, border 1px solid #E5E3DC, borderRadius 10, padding 16px`).

**Definition of done:**
- [ ] Global state shown as "Readiness to adopt: X%", "Level of agreement: X%", "Opinion change rate: X.XXX"
- [ ] Agent rows show name, role (human-readable), Support/Resistance/Workload as percentages, Stance
- [ ] No raw key names (`support_level`, `workload_stress`, etc.) visible
- [ ] Demographics string `[age/sex/ethnicity/ses]` removed
- [ ] `attribute_sections` JSON blob removed from this tab
- [ ] Each round is a card using the established `cardStyle` values
- [ ] `npm run build` passes

**Closeout:** `docs/iterations/senna-iter-14-closeout.md`

---

### senna-iter-15 — Run Details & Export: Plain Language

**Goal:** Clean up the Run Details tab (metadata) and the export/download flow. Plain-English economics, remove raw JSON config snapshot from user view, consolidate downloads into a single clear action.

**Changes to `App.tsx` — Run Details tab:**

**1. Run ID — reframe as "Session ID":**
```tsx
<div style={{ fontSize: 12, color: "#6B7280" }}>
  Session ID: <span style={{ fontFamily: "monospace" }}>{runId ?? "—"}</span>
</div>
```

**2. Economics block — plain English:**

Current:
```
Tokens in / out: 12400 / 8900
Estimated cost (USD): 0.042
Provider (request): anthropic
Tier turns — T1 8, T2 2, T3 0
```

New:
```tsx
{runEconomics && (
  <div style={{ background: "#F0FDF4", border: "1px solid #BBF7D0", borderRadius: 10,
    padding: "14px 16px", marginTop: 16 }}>
    <div style={{ fontWeight: 600, fontSize: 14, color: "#1A1A1A", marginBottom: 10 }}>
      AI usage
    </div>
    <div style={{ display: "grid", gap: 6, fontSize: 13, color: "#1A1A1A" }}>
      <div>
        Tokens used: ~{((runEconomics.total_input_tokens ?? 0) + (runEconomics.total_output_tokens ?? 0)).toLocaleString()}
      </div>
      <div>
        Estimated cost:{" "}
        {runEconomics.estimated_cost_usd != null && runEconomics.estimated_cost_usd > 0
          ? `$${runEconomics.estimated_cost_usd.toFixed(4)}`
          : runEconomics.llm_provider === "lmstudio" || runEconomics.llm_provider === ""
          ? "Free (local model)"
          : "—"}
      </div>
      {runEconomics.tier_breakdown && (
        <div style={{ color: "#6B7280", fontSize: 12, marginTop: 4 }}>
          Full AI turns: {runEconomics.tier_breakdown.tier_1_turns ?? 0} &nbsp;·&nbsp;
          Simplified turns: {runEconomics.tier_breakdown.tier_2_turns ?? 0} &nbsp;·&nbsp;
          Rule-based turns: {runEconomics.tier_breakdown.tier_3_turns ?? 0}
        </div>
      )}
    </div>
  </div>
)}
```

**3. Config snapshot — collapse behind a Details toggle:**

The raw JSON `configSnapshot` is valuable for researchers but should not be the first thing a user sees in Run Details. Wrap it:
```tsx
<details style={{ marginTop: 20 }}>
  <summary style={{ cursor: "pointer", fontSize: 13, color: "#4A6FA5", fontWeight: 500,
    listStyle: "none", display: "flex", alignItems: "center", gap: 6 }}>
    ▸ Technical configuration
  </summary>
  <div style={{ marginTop: 10 }}>
    {configSnapshot ? (
      <pre style={{ whiteSpace: "pre-wrap", background: "#F7F6F2", padding: 12,
        borderRadius: 8, fontSize: 12, color: "#1A1A1A", overflowX: "auto" }}>
        {JSON.stringify(configSnapshot, null, 2)}
      </pre>
    ) : (
      <div style={{ fontSize: 13, color: "#6B7280" }}>No configuration loaded.</div>
    )}
    {runId && (status === "completed" || status === "failed") ? (
      <div style={{ marginTop: 10, fontSize: 12 }}>
        <a href={samplingReportUrl(runId)} target="_blank" rel="noreferrer"
          style={{ color: "#4A6FA5" }}>
          Sampling report
        </a>
        <span style={{ color: "#6B7280" }}> — tier, role, and posture breakdown</span>
      </div>
    ) : null}
  </div>
</details>
```

Remove the `state_audit_enabled` paragraph — it is internal and not user-relevant.

**4. Export buttons — consolidate in Run Details:**

Add a clean download section at the top of Run Details (above the status line), only shown when `runId` is set and status is completed/failed/running:
```tsx
{runId && (status === "completed" || status === "failed" || status === "running") && (
  <div style={{ marginBottom: 20 }}>
    <div style={sectionHeadingStyle}>Download</div>
    <div style={{ display: "flex", flexWrap: "wrap", gap: 8 }}>
      <a href={exportZipUrl(runId)} download
        style={{ background: "#4A6FA5", color: "#FFFFFF", border: "none", borderRadius: 8,
          padding: "10px 18px", fontWeight: 600, fontSize: 14, textDecoration: "none",
          display: "inline-block", cursor: "pointer" }}>
        Download full report
      </a>
      <button type="button"
        style={{ background: "#FFFFFF", color: "#1A1A1A", border: "1px solid #E5E3DC",
          borderRadius: 8, padding: "10px 18px", fontSize: 14, cursor: "pointer", fontFamily: "inherit" }}
        onClick={() => downloadExportJson(runId).catch((e) => setStatus(`error: ${String(e)}`))}>
        Export as JSON
      </button>
    </div>
    <div style={{ fontSize: 12, color: "#6B7280", marginTop: 6 }}>
      Full report includes conversation transcript, participant attitudes, outcomes, and cost data.
    </div>
  </div>
)}
```

**5. The "Download ZIP (CSVs)" / "Download JSON" buttons on the old Set Up & Run tab:**

These were already removed from the main run section in Arc 1/2. Confirm they are gone — if any remain anywhere outside Run Details, remove them. Downloads should live only in Run Details.

**6. Quality Notes tab (Validity) — remove jargon from description paragraph:**

Current:
```
Manual face / construct / predictive coding per run or per round. Saved notes appear in 
GET /simulations/{id}, export JSON (export_version 4), and ZIP validity_notes.csv.
```
New:
```tsx
<p style={{ fontSize: 14, color: "#6B7280", maxWidth: 560, marginBottom: 20 }}>
  Add quality notes for this discussion — rate how realistic and valid the simulation felt,
  per round or for the whole run. Notes are saved with the run and included in exports.
</p>
```

Also in Quality Notes: the "Run id:" label at the top — change to:
```tsx
{runId
  ? <div style={{ fontSize: 13, color: "#6B7280", marginBottom: 12 }}>
      Noting quality for session: <span style={{ fontFamily: "monospace", fontSize: 12 }}>{runId.slice(0, 12)}…</span>
    </div>
  : <div style={{ fontSize: 13, color: "#6B7280", marginBottom: 12 }}>Load a run first to add notes.</div>
}
```

**Definition of done:**
- [ ] "Run ID" relabelled "Session ID" in Run Details
- [ ] Economics block shows plain-English token count, cost ("Free (local model)" for lmstudio), and tier breakdown in plain language
- [ ] Config snapshot collapsed behind "Technical configuration" `<details>` toggle
- [ ] Sampling report link moved inside that Technical configuration section
- [ ] `state_audit_enabled` paragraph removed
- [ ] Download section at top of Run Details with primary "Download full report" button + secondary "Export as JSON"
- [ ] Quality Notes description paragraph rewritten in plain English
- [ ] Quality Notes "Run id:" changed to "Noting quality for session:"
- [ ] **Order:** Implement Run Details + Quality Notes changes in this iteration **before** the repo-wide download audit below (so new export home is in place first).
- [ ] **Global grep:** Search the frontend for `exportZipUrl` and `downloadExportJson` (e.g. `rg exportZipUrl frontend/src` and `rg downloadExportJson frontend/src`). Every call site **outside** Run Details must be removed or redirected per §5 — only Run Details should offer these downloads after this iteration.
- [ ] `npm run build` passes

**Closeout:** `docs/iterations/senna-iter-15-closeout.md`

---

## Arc 3 — Architect Instructions

Work through iterations **sequentially**: senna-iter-11 → 12 → 13 → 14 → 15.

Iters 11, 12, 13, 14 are independent of each other (different files/sections). Iter 15 touches shared elements across tabs (Run Details + Quality Notes + any stray download buttons), so it should go last.

**Architect / reviewer emphasis (Arc 3):**

1. **senna-iter-12** — Conversation view is the centrepiece (bubble, colour left edge, role avatar, **Details** toggle). Review visually before PASS; output quality matters more here than in earlier iterations.
2. **senna-iter-13** — Narrative summary must use clean JSX fragments; **`<strong>` cannot live inside template literals** (see JSX note in that section). Sloppy string interpolation risks failed builds or garbled UI text.
3. **senna-iter-15** — **Order matters:** Run Details + Quality Notes first, then a **global grep** for `exportZipUrl` and `downloadExportJson` outside Run Details; remove or consolidate stray download buttons before closeout.

**Builder bootstrap (paste into each new Cursor Builder chat):**

> You are implementing the Senna UX redesign in `mirofish-mvp/frontend/`. Read in order:
> 1. `docs/SESSION_STATE.md`
> 2. `docs/handoffs/HANDOFF_SENNA_ARC1.md` — design palette and patterns
> 3. `docs/handoffs/HANDOFF_SENNA_ARC2.md` — component patterns established in Arc 2
> 4. `docs/handoffs/HANDOFF_SENNA_ARC3.md` — full spec for Arc 3 (this file)
> 5. Jump to the **senna-iter-N** section for the current iteration.
>
> Rules: Frontend only (backend untouched). Match existing code style. Run `npm run build` in `frontend/` after changes. Write `docs/iterations/senna-iter-N-closeout.md` when done. Do not expand scope beyond the active iteration spec.
>
> **senna-iter-15 only:** After implementing Run Details + Quality Notes, run a repo search for `exportZipUrl` and `downloadExportJson` under `frontend/src/` and document in the closeout that only Run Details retains export entry points (see handoff § **senna-iter-15** Definition of done).

---

## Arc 3 — Definition of Arc Complete

- [x] `LiveRunDashboard` shows no raw API key names; all metrics in plain English
- [x] Conversation tab renders as threaded speech bubbles with role avatars and Details toggle
- [x] Results tab has plain-English narrative summary + clean table
- [x] Attitudes tab shows global metrics as percentages, agent rows as readable cards, no JSON blobs
- [x] Run Details has economics in plain language, config snapshot collapsed, clean download section
- [x] Quality Notes description and session label are plain English
- [x] `npm run build` passes clean

---

## Arc 3 — Summary Template (Architect fills on completion)

```
Arc 3 complete — [date]
Iterations shipped: senna-iter-11, 12, 13, 14, 15
Build: PASS / FAIL
Deferred items: [list anything deferred]
Notes for Claude review: [anything the UX architect should pay attention to]
```

**Completion record (2026-04-20):**

```
Arc 3 complete — 2026-04-20
Iterations shipped: senna-iter-11, 12, 13, 14, 15
Build: PASS
Deferred items: Experiments tab still uses its own ZIP URL helper (`experimentExportZipUrl`); Arc 3 export grep scope was simulation run exports only. Arc 4 will cover Compare Runs / Experiments UX in plain language.
Notes for Claude review: senna-iter-12 formal gate remains visual confirmation of Conversation tab in browser; all other iterations have code + build evidence in closeouts.
```

---

## What Comes Next (Arc 4 preview)

Arc 4 (Advanced Features Accessible) makes the powerful features usable without knowing the internals: Assistant tab redesign, Compare Runs (Experiments) tab in plain language, Quality Notes form with accessible inputs, a consolidated Technical Details section, and Scenario Wizard accessibility improvements.

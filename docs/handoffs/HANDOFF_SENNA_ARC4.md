# Senna UX Redesign — Arc 4 Handoff (to Cursor Architect)

**Prepared by:** Claude (Cowork / UX Design Architect)  
**Date:** 2026-04-22  
**Arc:** 4 of 5 — Advanced Features Accessible  
**Iterations:** senna-iter-16 through senna-iter-20  
**Backend:** Untouched. All changes are frontend-only.

---

## State entering Arc 4

Arcs 1–3 are closed. The following is in place:

- `SennaHeader`, `ScenarioSelector`, `RunStatusCard`, `ConversationView`, `LiveRunDashboard` all redesigned
- `runStatusCopy.ts` shared helpers; `classifyRunStatusTone`, `getRunStatusLabel`, `RUN_STATUS_PILL_STYLES`
- `cardStyle`, `emptyStateCardStyle`, `sectionHeadingStyle`, `metricCardStyle` constants in `App.tsx`
- Two-column Set Up & Run layout, plain-English status messages, iMessage-style conversation view
- Tab active state: `border: 1px solid #4A6FA5`, `background: #EEF3FA`
- Palette: bg `#F7F6F2`, card `#FFFFFF`, text `#1A1A1A`, secondary `#6B7280`, accent `#4A6FA5`, border `#E5E3DC`

**The problem Arc 4 solves:** Four tabs — Assistant, Compare Runs, Quality Notes, and Policy Scenarios — are still full of research and developer jargon. A non-technical user who clicks into any of them would see raw API endpoint paths, snake_case metric names, `beliefs JSON`, `persona_id`, sampling strategy codes, and score labels from academic validity theory. Arc 4 makes these tabs legible to a layperson without removing their functionality.

**Arc 4 goal:** Every label, placeholder, helper text, and section heading in the four remaining "advanced" tabs should be readable and useful to someone who is not a developer or academic researcher. Internal IDs and technical keys stay in the code — they must not appear in the UI.

---

## Design Philosophy (reminder)

75% Apple minimal, 25% practical warmth. The 25% matters especially here: these are complex tools and users need enough context to act. Don't strip explanatory text in the name of minimalism — rewrite it in plain English instead.

**Established patterns — use consistently:**
- `cardStyle` for all content panels
- `emptyStateCardStyle` for empty states
- `sectionHeadingStyle` for section titles within panels
- Tab active state: `border: 1px solid #4A6FA5`, `background: #EEF3FA`
- Secondary button: `background: #FFFFFF`, `border: 1px solid #E5E3DC`, `borderRadius: 8`, `padding: "8px 14px"`
- Primary button: `background: #4A6FA5`, `color: #FFFFFF`, `borderRadius: 8`, `padding: "10px 18px"`, `fontWeight: 600`
- `border: "1px solid #ddd"` and `border: "1px solid #eee"` are off-palette — replace with `#E5E3DC`

---

## Arc 4 — Iterations

---

### senna-iter-16 — Assistant Tab (AgentConsole) Relabeling

**File:** `frontend/src/components/AgentConsole.tsx`

**Goal:** The Assistant tab helps users ask plain-language questions and get Senna to plan and run simulations automatically. Right now it exposes API endpoint paths, JSON plan editing, and temperature/token parameters to users. Relabel and reorganise so a layperson can use the core flow, with advanced options safely tucked away.

**Changes:**

**Intro paragraph (line ~216):**
- Current: `"Describe what you want in plain language. The server plans the run, executes simulations, and returns structured analysis. Use Advanced to tune timeouts, planner temperature, or run Plan / Execute separately."`
- New: `"Describe what you want in plain English and Senna will plan and run the simulation automatically. Use Advanced settings to adjust timing or run the planning and execution steps separately."`

**Question label:**
- Current: `"Research question (min. 8 characters)"`
- New: `"What would you like to explore?"` — remove min-character note from the label (keep the validation logic, just remove it from the visible label; show the small warning text only when the user types < 8 characters, as already coded)

**Question placeholder (QUESTION_PLACEHOLDER constant):**
- Keep as-is — it's a concrete example and helps users understand the kind of question to ask. Do not change.

**Ask button:**
- Current: `"Ask"` / `"Running (plan + execute)…"`
- New: `"Run"` / `"Running…"`

**Cancel button:**
- Current: `"Cancel request"`
- New: `"Cancel"`

**Results section heading:**
- Current: `<h2>Results</h2>` in a raw `<section style={sectionStyle}>`
- New: `<div style={sectionHeadingStyle}>Results</div>` — use the shared constant, not a raw `<h2>`

**Show/hide plan button:**
- Current: `"{planDetailsOpen ? "Hide" : "Show"} execution plan (JSON)"`
- New: `"{planDetailsOpen ? "Hide" : "Show"} technical plan"`

**Advanced section button:**
- Current: `"{advancedOpen ? "▼ Hide advanced" : "▶ Advanced (constraints, plan/execute, tuning)"}"`
- New: `"{advancedOpen ? "▼ Hide advanced settings" : "▸ Advanced settings"}"`

**Inside Advanced — Constraints label:**
- Current: `"Constraints (optional)"`
- New: `"Extra instructions (optional)"`
- Placeholder: keep `"Extra instructions for the planner…"`

**Inside Advanced — Timeout label:**
- Current: `"Wait timeout per run (seconds)"`
- New: `"Max wait time per run (seconds)"`
- Helper text: Current: `"Applied each simulation wait; multi-run asks sum wall-clock."` → New: `"Maximum time to wait for each simulation. Longer runs may need a higher value."`

**Inside Advanced — Planner temperature:**
- Current: `"Planner temperature (optional, 0–2)"`
- New: `"Planning creativity (optional, 0–2)"` — placeholder `"default 0.35"` stays
- Validation message: Current: `"Must be a number between 0 and 2 (or leave empty)."` → keep as-is

**Inside Advanced — Plan max tokens:**
- Current: `"Plan max tokens (optional, 256–4096)"`
- New: `"Planning detail limit (optional, 256–4096)"` — placeholder `"default 2048"` stays

**"Plan only" sub-section:**
- Current heading: `<div style={{ fontWeight: 600 }}>Plan only</div>`
- New: `<div style={{ fontWeight: 600 }}>Plan without running</div>`
- Current description: `"Calls POST /agent/plan with the question above. Fills the execute JSON box below."`
- New: `"Generates a plan from your question without running it. The plan will appear in the box below — you can review or edit it before executing."`
- Button: `"Run plan only"` → `"Generate plan"`
- Loading: `"Planning…"` → keep

**"Execute plan" sub-section:**
- Current heading: `<div style={{ fontWeight: 600 }}>Execute plan</div>`
- New: `<div style={{ fontWeight: 600 }}>Run a saved plan</div>`
- Current description: `"Paste an ExecutionPlan JSON (runs array). Calls POST /agent/execute."`
- New: `"Paste or edit a plan (in JSON format) and run it directly. Use the Generate plan step above to produce a plan first."`
- Button: `"Execute JSON plan"` → `"Run this plan"`
- Loading: `"Executing…"` → keep
- The textarea itself stays as-is (JSON editing for advanced users is intentional)

**"Execute results" label:**
- Current: `<strong>Execute results</strong>`
- New: `<div style={sectionHeadingStyle}>Execution results</div>`

**"Last plan loaded" footnote:**
- Current: `"Last plan loaded — use Execute JSON plan to run it without re-planning."`
- New: `"Plan loaded — use Run this plan to execute it without re-planning."`

**sectionStyle local variable (lines ~200–207):**
- Current: `border: "1px solid #ddd"` 
- New: `border: "1px solid #E5E3DC"` — align to palette

**`advancedTuningInvalid` warning:**
- Current: `"Fix advanced tuning values above before Ask / Plan / Execute."`
- New: `"Fix advanced settings above before running."`

**Definition of done:**
- [ ] No API endpoint paths (`POST /agent/plan`, `POST /agent/execute`) visible in any label or description
- [ ] No `ExecutionPlan`, `runs[]`, or JSON-schema terminology in any visible label or description
- [ ] No raw `<h2>` — section headings use `sectionHeadingStyle` or equivalent
- [ ] All `border: "1px solid #ddd"` replaced with `#E5E3DC`
- [ ] Component still functions identically
- [ ] `npm run build` passes

**Closeout:** Write `docs/iterations/senna-iter-16-closeout.md`

---

### senna-iter-17 — Compare Runs Tab (ExperimentConsole) Relabeling

**File:** `frontend/src/components/ExperimentConsole.tsx`

**Goal:** The Compare Runs tab lets researchers run the same scenario with different participant-selection strategies side by side. Currently it shows raw strategy codes, snake_case metric names, abbreviated table data, and experiment IDs in `<code>` tags. Make it legible.

**Sampling strategy labels (SAMPLING_STRATEGIES constant + select options):**

Map raw values to plain-English labels in the `<select>` dropdown. The `value` attribute must remain unchanged (the backend needs it). Only the visible option text changes:

| Raw value | Display label |
|-----------|---------------|
| `full_census` | All participants speak |
| `role_stratified` | By role group |
| `hybrid_core_remainder` | Core group + random fill |
| `posture_maxvar` | Maximum diversity |
| `network_centrality` | By network influence |

**Comparison metric labels (COMPARISON_METRIC_OPTIONS constant):**

Map raw values to plain-English labels. `value` attributes stay unchanged:

| Raw value | Display label |
|-----------|---------------|
| `implementation_readiness` | Readiness to adopt |
| `alignment_index` | Level of agreement |
| `adoption_momentum` | Adoption momentum |
| `conflict_events` | Disagreements |
| `consistency_index` | Consistency |
| `convergence_delta` | Opinion change rate |

**"Create experiment" section heading:**
- Current: `<h2 style={{ marginTop: 0 }}>Create experiment</h2>`
- New: `<div style={sectionHeadingStyle}>New comparison run</div>` — import/use `sectionHeadingStyle` from `App.tsx` or redeclare locally with the same spec

> Note: `sectionHeadingStyle` is defined in `App.tsx`. The simplest approach is to redeclare it locally in `ExperimentConsole.tsx` using the same values:
> ```ts
> const sectionHeadingStyle: React.CSSProperties = {
>   fontSize: 13, fontWeight: 600, color: "#6B7280",
>   textTransform: "uppercase", letterSpacing: "0.5px", marginBottom: 12,
> };
> ```

**Create experiment intro paragraph:**
- Current: `"Same scenario and seed; each row queues a simulation with a different sampling_strategy. Runs execute sequentially on the server (one finishes before the next starts)."`
- New: `"Run the same scenario with different participant-selection strategies side by side. Each row is one run — all share the same scenario and seed. Runs complete one after another."`

**Form field labels inside "New comparison run":**

| Current label | New label |
|---------------|-----------|
| `Name` | `Comparison name` |
| `Scenario` | `Policy scenario` |
| `Random seed` | `Reproducibility seed` |
| `Total rounds` | `Discussion rounds` |
| `Agent limit` | `Number of participants` |
| `Convergence (optional — same for every run)` | `Auto-stop settings (optional — applies to all runs)` |
| `Threshold (0–1, empty = off)` | `Sensitivity (0.01 = very sensitive, 0.1 = loose)` |
| `Patience (rounds)` | `Rounds to confirm consensus` |

**Run rows section:**
- Current: `<h3 style={{ marginTop: 18 }}>Runs</h3>`
- New: `<div style={{ ...sectionHeadingStyle, marginTop: 18 }}>Runs to compare</div>`
- Row label input: `placeholder="label"` → `placeholder="Run label (e.g. A)"`
- "Add run row" button → `"Add run"`
- "Remove" button → keep as-is

**Start / Cancel buttons:**
- `"Running experiment…"` → `"Running…"`
- `"Start experiment"` → `"Start comparison"`
- `"Cancel"` → keep

**"Last experiment id" line:**
- Current: `"Last experiment id: {lastExperimentId}"`
- New: `"Comparison ID: "` + `<span style={{ fontFamily: "monospace", fontSize: 12 }}>{lastExperimentId.slice(0, 14)}…</span>`

**"Comparison chart" section:**
- Current: `<h2 style={{ marginTop: 0 }}>Comparison chart</h2>`
- New: `<div style={sectionHeadingStyle}>Metric trends</div>`

**Status line inside comparison chart:**
- Current: `"Experiment {detail.experiment.id.slice(0,12)}… — status {detail.experiment.status}"`
- New: `"Run group {detail.experiment.id.slice(0,10)}… · {shortStatusLabel(detail.experiment.status)}"` — use `shortStatusLabel` from `runStatusCopy.ts` for the status

**"Sparkline metric" label:**
- Current: `<span>Sparkline metric</span>`
- New: `<span>Chart by</span>`

**Metrics table (inside `<details>`):**
- `<summary>All metrics by round (table)</summary>` → `<summary>All metrics by round</summary>`
- Table currently shows abbreviated data inline: `ir {v} · al {v} · am {v} · ce {v} · ci {v} · cd {v}`
- Replace each abbreviation with the plain-English label from the metric map above, line-broken for readability:
  ```tsx
  <>
    <div>Readiness: {fmtMetric(met.implementation_readiness)}</div>
    <div>Agreement: {fmtMetric(met.alignment_index)}</div>
    <div>Adoption: {fmtMetric(met.adoption_momentum)}</div>
    <div>Disagreements: {met.conflict_events ?? "—"}</div>
    <div>Consistency: {fmtMetric(met.consistency_index)}</div>
    <div>Opinion change: {fmtMetric(met.convergence_delta)}</div>
  </>
  ```
- Column header token display: Current: `"in/out {e.total_input_tokens}/{e.total_output_tokens} · ${cost}"` → New: `"Tokens: {total} · ${cost}"` where total = input + output; display cost only if > 0

**"Per-run status" section:**
- Current: `<h2 style={{ marginTop: 0 }}>Per-run status</h2>`
- New: `<div style={sectionHeadingStyle}>Run results</div>`
- List items: current: `"{r.series_key} · {r.sampling_strategy ?? "?"} · {r.status}"`
- New: `"{r.series_key} · {strategyLabel(r.sampling_strategy)} · {shortStatusLabel(r.status)}"` — define a `strategyLabel(s: string)` helper using the same mapping table above; fallback to the raw value if not found
- Convergence display: Current: `"Converged R{n}"` → New: `"Consensus at Round {n}"`
- Full rounds display: Current: `"Full {r.total_rounds} rounds"` → New: `"All {r.total_rounds} rounds"`
- Economics line: Current: `"Tokens {in}/{out} · est. ${cost}"` → New: `"~{total} tokens · ${cost}"` (or "Free" for lmstudio) — follow the same pattern as `App.tsx` metadata tab

**"Recent experiments" section:**
- Current: `<h2>Recent experiments</h2>`
- New: `<div style={sectionHeadingStyle}>Previous comparisons</div>`
- List items: show `{e.name}` (already there), status via `shortStatusLabel(e.status)`, run count `"{e.run_count} runs"` — keep; experiment `<code>{e.id.slice(0,14)}…</code>` → `<span style={{ fontFamily: "monospace", fontSize: 11, color: "#6B7280" }}>{e.id.slice(0,10)}…</span>`
- "Load detail" button → `"Load"`

**"Compare two runs (by ID)" section:**
- Current: `<h2>Compare two runs (by ID)</h2>`
- New: `<div style={sectionHeadingStyle}>Compare two individual runs</div>`
- Description: Current: `"Side-by-side outcome indicators from GET /simulations/{id}."` → New: `"Paste two run IDs to compare their outcomes side by side."`
- Placeholders: `"Run ID A"` → `"First run ID"`, `"Run ID B"` → `"Second run ID"`
- "Compare" button → keep

**Side-by-side comparison display:**
- Current: `<h3>A: {compareA.id.slice(0,8)}…</h3>` → `<div style={{ fontWeight: 600, fontSize: 14, marginBottom: 6 }}>Run A · {compareA.id.slice(0,8)}…</div>`
- Same pattern for B
- `"Status: {compareA.status}"` → `shortStatusLabel(compareA.status)`
- Round display: `"R{n}: adoption {v}, conflicts {n}, consistency {v}"` → `"Round {n}: Adoption {v} · Disagreements {n} · Consistency {v}"`

**Border cleanup:** All `border: "1px solid #ddd"` → `#E5E3DC`. All `border: "1px solid #eee"` → `#E5E3DC`.

**Definition of done:**
- [ ] No raw snake_case sampling strategy values visible in dropdowns or list items
- [ ] No snake_case metric names visible in dropdowns, sparkline labels, or table cells
- [ ] No API endpoint paths visible in any description
- [ ] No raw `<h2>` — all section headings use `sectionHeadingStyle`
- [ ] All `#ddd` / `#eee` borders replaced with `#E5E3DC`
- [ ] All functionality unchanged
- [ ] `npm run build` passes

**Closeout:** Write `docs/iterations/senna-iter-17-closeout.md`

---

### senna-iter-18 — Quality Notes Tab Relabeling

**File:** `frontend/src/App.tsx` (the `validity` tab section, lines ~1218–1326)

**Goal:** The Quality Notes tab uses academic validity terminology — face validity, construct validity, predictive validity, rater ID. A non-academic user has no idea what these mean. Translate to plain language while preserving the data structure exactly (field names sent to the backend stay unchanged).

**Context:** Validity in research means: does the simulation feel realistic (face), does it measure what it claims (construct), does it predict real-world outcomes (predictive). The plain-English equivalents below preserve the meaning without the jargon.

**Section heading:**
- Current: `<h2>Validity notes</h2>`
- New: `<h2 style={{ marginTop: 0, marginBottom: 16, fontSize: 18, fontWeight: 600 }}>Quality notes</h2>` — Arc 5 will handle headings globally; for now just clean the text

**Intro paragraph:**
- Current: `"Add quality notes for this discussion — rate how realistic and valid the simulation felt, per round or for the whole run. Notes are saved with the run and included in exports."`
- New: `"Rate how realistic and useful this discussion felt — for the whole run or for individual rounds. Notes are saved with the run and included in all exports."`

**Form container border:**
- Current: `border: "1px solid #ddd"` → `border: "1px solid #E5E3DC"`; `borderRadius: 8` → `borderRadius: 10`; add `background: "#FFFFFF"`, `padding: 20`

**Field label changes:**

| Current label | New label | Notes |
|---------------|-----------|-------|
| `Round (empty = whole run)` | `Round (leave blank for whole run)` | |
| `Rater id (optional)` | `Your name or ID (optional)` | |
| `Face score` | `Realism score` | face validity = does it look realistic |
| `Construct score` | `Accuracy score` | construct validity = does it measure what it claims |
| `Predictive score` | `Predictive score` | keep — understandable as-is |
| `Face rubric / notes` | `Realism notes` | |
| `Construct rubric / notes` | `Accuracy notes` | |
| `Predictive rubric / notes` | `Predictive notes` | |
| `General notes` | `Other notes` | |

**Score field placeholders:** all `"0–1"` → `"0.0 – 1.0"`

**Rater placeholder:** `"analyst_id"` → `"e.g. mark, reviewer-1"`

**Save button:**
- Current: `"Save validity note"` / `"Saving…"`
- New: `"Save quality note"` / `"Saving…"`

**Error message (vnError):**
- Current: `"Add at least one score, rubric, rater, round, or notes."` (in `onSaveValidityNote`)
- New: `"Add at least one score or note before saving."`

**"Saved notes" heading:**
- Current: `<h3>Saved notes</h3>`
- New: `<div style={sectionHeadingStyle}>Saved notes</div>`

**Saved notes empty state:**
- Current: `<div>None yet for this run.</div>`
- New: `<div style={emptyStateCardStyle}>No quality notes yet for this run.</div>`

**Saved notes list items** (lines ~1312–1322):
- Current border: `border: "1px solid #eee"` → `#E5E3DC`
- Header line: `"{n.round_number == null ? "Run-level" : "Round {n.round_number}"} · rater {n.rater_id} · {n.created_at}"`
  - New: `"{n.round_number == null ? "Whole run" : "Round {n.round_number}"}` + `{n.rater_id ? " · " + n.rater_id : ""}` + date if present (format via `formatRunDate`)
- Score lines — current: `"face: {score} / {rubric}"` / `"construct: ..."` / `"predictive: ..."`
  - New:
    ```tsx
    {n.face_score != null || n.face_rubric ? <div>Realism: {n.face_score ?? "—"}{n.face_rubric ? ` — ${n.face_rubric}` : ""}</div> : null}
    {n.construct_score != null || n.construct_rubric ? <div>Accuracy: {n.construct_score ?? "—"}{n.construct_rubric ? ` — ${n.construct_rubric}` : ""}</div> : null}
    {n.predictive_score != null || n.predictive_rubric ? <div>Predictive: {n.predictive_score ?? "—"}{n.predictive_rubric ? ` — ${n.predictive_rubric}` : ""}</div> : null}
    ```
  - Only render a line if at least one of score or rubric is non-null

**Definition of done:**
- [ ] No "face", "construct", "validity", "rater id", "rubric" visible to users in labels
- [ ] Form border uses `#E5E3DC`, not `#ddd`
- [ ] Saved notes display conditionally — only show score types that have data
- [ ] All API payloads unchanged (field names `face_score`, `construct_score` etc. still sent correctly)
- [ ] `npm run build` passes

**Closeout:** Write `docs/iterations/senna-iter-18-closeout.md`

---

### senna-iter-19 — Policy Scenarios Tab (ScenarioWizard) Accessibility

**File:** `frontend/src/components/ScenarioWizard.tsx`

**Goal:** The ScenarioWizard is the most jargon-dense component in the app. It references internal documentation, uses raw database field names as labels, shows `(builtin)` / `(user)` source tags, and its step active state uses an off-palette colour. Clean up all user-visible strings while preserving all functionality.

**Intro description (line ~364):**
- Current: `"Create or edit user scenarios stored in SQLite. Built-in YAML scenarios are read-only; clone or load as template. See docs/plans/scenario-wizard-design.md."`
- New: `"Create your own policy scenarios or customise the built-in ones. Built-in scenarios are read-only — clone them to make changes."`

**Step active state button:**
- Current: `background: step === i ? "#eef" : "#fff"` → `background: step === i ? "#EEF3FA" : "#FFFFFF"`, `border: step === i ? "1px solid #4A6FA5" : "1px solid #E5E3DC"`

**Step labels (STEPS constant):**
- Current: `["Basics", "Policy rounds", "Personas", "Groups", "RAG", "Review"]`
- New: `["Basics", "Policy rounds", "Participants", "Groups", "Knowledge base", "Review"]`

---

**Load / clone section:**

Container heading: `<strong>Load / clone</strong>` → `<strong>Start from a template</strong>`

"Load template into editor" label → `"Load scenario into editor"`

Catalog option rendering — currently shows `"{c.name} ({c.source})"` where source is "builtin" or "user":
- New: `"{c.name}{c.source === "user" ? " (custom)" : ""}"` — drop the "(builtin)" suffix entirely; only flag custom scenarios

"Generate from brief (LLM)" label → `"Generate from a description (AI)"`

Brief textarea placeholder: Current: `"Describe the policy context, stakeholders, and what should happen across rounds (20+ characters). The server validates the result."` → New: `"Describe the policy scenario, who the participants are, and what should happen in each round. Aim for 20+ characters."`

"Clone template → new id" label → `"Copy a scenario"`

Clone template select — same as above: drop `({c.source})` suffix from clone select options

"new_scenario_id (slug)" label → `"New scenario ID"` with helper text below: `<span style={{ fontSize: 11, color: "#6B7280" }}>Lowercase letters, numbers, and hyphens only (e.g. my-reform-scenario)</span>`

Clone new ID placeholder: `"analyst_my_run"` → `"e.g. my-reform-scenario"`

"Display name" label (in clone block) → `"Display name"` — keep as-is, it's clear

---

**Step 0 — Basics:**

`scenario_id (lowercase slug, e.g. analyst_case_a)` label → `"Scenario ID"` with helper text: `<span style={{ fontSize: 11, color: "#6B7280" }}>Lowercase letters, numbers, and hyphens only. Cannot be changed after saving.</span>`

Input has `style={{ fontFamily: "monospace" }}` — keep the monospace style (it signals "slug format")

"Display name" label → keep

Radio buttons:
- `"New scenario (POST)"` → `"Create new scenario"`
- `"Update existing user scenario"` → `"Update existing scenario"`

"Pick user scenario to edit" label → `"Choose scenario to edit"`

---

**Step 1 — Policy rounds:**

Everything here is already plain English. No changes needed.

---

**Step 2 — Participants (formerly Personas):**

**Per-persona card border:** current `border: "1px solid #dde"` → `border: "1px solid #E5E3DC"`

**`persona_id` input placeholder:** `"persona_id"` → `"participant-id (e.g. teacher-1)"`

**`name` input placeholder:** `"name"` → `"Display name"`

**Role select options:** current raw values `"principal"`, `"middle_manager"`, `"teacher"` — wrap in a display label:
- Render as: `<option value="principal">Principal</option>`, `<option value="middle_manager">Middle manager</option>`, `<option value="teacher">Teacher</option>` — capitalise display only, keep values unchanged

**`role_level` label:** current `<label style={{ fontSize: 12 }}>role_level<input …/></label>` → `<label style={{ fontSize: 12, display: "grid", gap: 4 }}><span>Seniority (1–3)</span><input …/></label>`

**`style_cues` textarea placeholder:** `"style_cues"` → `"Communication style and tone (e.g. formal, data-driven, sceptical)"`

**`beliefs JSON e.g. {"key": 0.5}` textarea:**
- Change label to: `"Beliefs (JSON, optional)"` rendered as `<span style={{ fontSize: 11, color: "#6B7280" }}>Beliefs (JSON format — leave as {"{ }"}  if none)</span>` above the textarea
- Keep the textarea and monospace font (advanced users need it)

**"Structured attributes" heading:** keep — it's reasonably clear
**"Randomize" button tooltip:** `title="Fill with random plausible values based on role"` — keep
**"LLM Fill" button tooltip:** `title="Ask LLM to suggest attribute values based on this persona's role and style cues"` → `title="Use AI to suggest attribute values for this participant"`
**"LLM Fill" button label:** `"LLM Fill"` → `"AI Fill"`

**Section labels in attribute editor (SECTION_LABELS):**
- Current: `{ identity: "Identity", attitudes: "Attitudes / Stance", personal_history: "Personal History" }`
- No change needed — these are clear

**`+ Add {SECTION_LABELS[sec]} key` buttons → `"+ Add {SECTION_LABELS[sec]} field"`

**"Remove persona" button → `"Remove participant"`**
**"Add persona" button → `"Add participant"`**

---

**Step 3 — Groups:**

**`group_id` input placeholder:** `"group_id"` → `"group-id (e.g. teachers)"`
**`name` input placeholder:** `"name"` → `"Group name"`
**`description` input placeholder:** `"description"` → `"Brief description"`
**"Add group" button** → keep
**"Remove" button** → keep

---

**Step 4 — Knowledge base (formerly RAG):**

**Checkbox label:** Current: `"Enable RAG (bundled corpus paths only)"` → `"Enable knowledge base (uses bundled documents)"`

**Helper text:** Current: `"Select files under scenarios/data (server-enumerated)."` → `"Select reference documents to include. These are pre-loaded documents from the server."`

**RAG paths display:** Currently shows raw file paths as `<code style={{ fontSize: 11 }}>{p}</code>`. Keep the `<code>` but change colour to `#6B7280` to de-emphasise:
`<code style={{ fontSize: 11, color: "#6B7280" }}>{p}</code>`

---

**Step 5 — Review:**

The review step shows a raw JSON `<pre>`. Add a heading above it:
```tsx
<div style={{ fontSize: 13, color: "#6B7280", marginBottom: 8 }}>
  Review the scenario configuration below before saving.
</div>
```

**Save buttons:**
- `"Save (create)"` → `"Save scenario"`
- `"Save (update)"` → `"Save changes"`

**Export YAML link:** `"Export YAML"` → keep (YAML is a standard format and is clear enough)

---

**Message / error / warning display:**

**Success message:** current `color: "#059669"` — add a wrapper:
```tsx
{message ? (
  <div style={{ padding: "10px 14px", background: "#D1FAE5", border: "1px solid #A7F3D0", borderRadius: 8, fontSize: 13, color: "#065F46" }}>
    {message}
  </div>
) : null}
```

**Error message:** current `color: "#b91c1c"` → wrap similarly:
```tsx
{error ? (
  <div style={{ padding: "10px 14px", background: "#FEE2E2", border: "1px solid #FECACA", borderRadius: 8, fontSize: 13, color: "#991B1B" }}>
    {error}
  </div>
) : null}
```

**Outer section border:** current `border: "1px solid #ddd"` → `border: "1px solid #E5E3DC"`; `background: "#FFFFFF"` already set via `cardStyle` intent — apply `background: "#FFFFFF"` if not already present.

**Definition of done:**
- [ ] No `persona_id`, `group_id`, `scenario_id (slug)`, `role_level`, `style_cues`, `beliefs JSON`, `(builtin)`, `(user)`, `RAG`, `POST /`, or `docs/plans/` visible in any user-facing label or placeholder
- [ ] Step active state uses `#EEF3FA` + `#4A6FA5` border (not `#eef`)
- [ ] All `#ddd` borders replaced with `#E5E3DC`
- [ ] All functionality unchanged — save, clone, load, LLM fill all still work
- [ ] `npm run build` passes

**Closeout:** Write `docs/iterations/senna-iter-19-closeout.md`

---

### senna-iter-20 — Final Jargon Sweep

**Files:** `frontend/src/components/ConversationView.tsx`, `frontend/src/App.tsx`

**Goal:** Close out the remaining deferred items from Arcs 3 and 4: one label in `ConversationView`, the experiment UUID fragment in the run list, the naked `<h2>` headings on tab panels, and a style-consistency pass on all remaining off-palette colours.

---

**ConversationView.tsx — "Fidelity tier" label:**

In the Details panel (around line ~328 in Arc 3's output):
```tsx
{turn.fidelity_tier != null ? (
  <div>Fidelity tier: {turn.fidelity_tier}</div>
) : null}
```
→ Change label to `"Detail level:"`:
```tsx
{turn.fidelity_tier != null ? (
  <div>Detail level: {turn.fidelity_tier}</div>
) : null}
```

---

**App.tsx — experiment_id in run list:**

In the run list (Recent discussions), the experiment_id fragment currently shows as:
```tsx
<span style={{ marginLeft: 8, fontSize: 12, opacity: 0.8 }}>
  · experiment {String(r.experiment_id).slice(0, 8)}…
</span>
```
→ Change to:
```tsx
<span style={{ marginLeft: 8, fontSize: 12, color: "#6B7280" }}>
  · part of a comparison run
</span>
```
(We drop the ID fragment — it's meaningless to a layperson and they can see the full experiment in Compare Runs.)

---

**App.tsx — naked `<h2>` headings on tab panels:**

The Watch Live, Conversation, Results, Attitudes, Experiments, Assistant, and Policy Scenarios tab sections still have raw `<h2>` headings that aren't needed since the tab labels already communicate context. Remove or replace:

| Current | Action |
|---------|--------|
| `<h2>Live run dashboard</h2>` in Watch Live section | Remove entirely — the tab label is enough |
| `<h2>Conversation</h2>` in transcript section | Remove entirely |
| `<h2>Results</h2>` in outcomes section | Remove entirely |
| `<h2>Attitudes</h2>` in state section | Remove entirely |
| `<h2 style={{ marginTop: 0 }}>Experiments</h2>` in experiments section | Remove entirely (ExperimentConsole has its own headings) |
| `<h2 style={{ marginTop: 0 }}>Assistant</h2>` in agent section | Remove entirely (AgentConsole has its own headings) |
| `Run Details` h2 in metadata section | Keep — this is a section heading within a larger tab, not a tab-label echo |
| `Quality notes` h2 in validity section | Keep — same reason |

Note: removing these `<h2>` elements may cause small layout shifts (they add top margin). After removal, check if padding is still appropriate — add `paddingTop: 4` to the tab panel wrapper if the top feels cramped.

---

**App.tsx — remaining palette fixes:**

Search for any remaining `#ddd`, `#eee`, `coral`, `#a60`, `#a30` in user-visible style strings and replace:

| Old | New |
|-----|-----|
| `color: "coral"` | `color: "#E05252"` |
| `color: "#a30"` | `color: "#C05000"` |
| `color: "#a60"` | `color: "#92400E"` |

Note: `#a30` / `#a60` are validation warning colours — `#92400E` (amber-dark) matches the amber palette tone used for `running` status.

---

**CLAUDE.md — arc status update:**

Update `docs/` or root `CLAUDE.md` arc status table:
- Arc 4 → `✅ CLOSED`

**Definition of done:**
- [ ] "Fidelity tier" does not appear anywhere in `ConversationView.tsx` user-visible text
- [ ] Experiment ID fragment removed from run list items
- [ ] All raw `<h2>` headings removed from tab panels as listed above
- [ ] `coral`, `#a60`, `#a30` colour strings replaced with palette equivalents
- [ ] `npm run build` passes
- [ ] CLAUDE.md updated: Arc 4 → CLOSED

**Closeout:** Write `docs/iterations/senna-iter-20-closeout.md`

---

## Arc 4 — Architect Instructions

Work through iterations **sequentially**: senna-iter-16 → 17 → 18 → 19 → 20.

For each iteration:
1. Seed Builder with the relevant `###` section from this document
2. Include the standard bootstrap: read `CLAUDE.md` + `docs/handoffs/HANDOFF_TO_BUILDER.md` + this file first
3. Builder implements, runs `npm run build`, writes closeout
4. Architect reviews closeout + build output
5. PASS → seed next. PASS_WITH_ISSUES → resolve before next.

**Builder bootstrap (paste into each new Cursor chat):**

> You are implementing the Senna UX redesign in `mirofish-mvp/frontend/`. Read in order:
> 1. `CLAUDE.md` (project context and design system)
> 2. `docs/handoffs/HANDOFF_SENNA_ARC4.md` (this handoff — full spec for Arc 4)
> 3. Then jump to the **senna-iter-N** section for the current iteration.
>
> Rules: Match existing code style. Frontend changes only (backend untouched). Run `npm run build` in `frontend/` after changes. Write `docs/iterations/senna-iter-N-closeout.md` when done. Do not expand scope beyond the active iteration spec.

---

## Arc 4 — Definition of Arc Complete

All of the following must be true before handing back to Claude for arc review:

- [x] No API endpoint paths (`POST /agent/`, `GET /simulations/`) visible in any user-facing label or description
- [x] No raw snake_case metric names visible in any dropdown, table, or label
- [x] No raw sampling strategy codes visible in any dropdown or list
- [x] No academic validity jargon (`face`, `construct`, `rater id`, `rubric`) visible in Quality Notes
- [x] No `persona_id`, `group_id`, `role_level`, `style_cues`, `beliefs JSON`, `(builtin)`, `RAG` visible in Policy Scenarios
- [x] Step active state in ScenarioWizard uses `#EEF3FA` + `#4A6FA5` border
- [x] All `#ddd` / `#eee` / `coral` / `#a60` colours replaced with palette equivalents **in primary shell / Arc 4–touched surfaces** (see [`senna-iter-20-closeout.md`](../iterations/senna-iter-20-closeout.md) — residual off-palette in a few other components deferred to Arc 5)
- [x] All naked `<h2>` tab panel headings removed (per iter-20 table; Run Details + Quality notes headings kept)
- [x] "Fidelity tier" → "Detail level" in ConversationView
- [x] `npm run build` passes clean

**Arc 4 — Completion record (Architect, 2026-04-22):**

- Iterations **senna-iter-16**–**20** shipped; closeouts in `docs/iterations/senna-iter-*-closeout.md`.
- **Build:** PASS (`frontend/` `npm run build`).
- **CLAUDE.md:** Arc 4 marked ✅ CLOSED.
- **Cowork / Opus arc review (2026-04-22):** **PASS** — no required follow-ups; deferred off-palette strings outside `App.tsx` accepted for Arc 5 (see [`HANDOFF_TO_ARCHITECT.md`](HANDOFF_TO_ARCHITECT.md) § *Senna Arc 4 — Opus arc review*).

---

## What Comes Next (Arc 5 preview)

Arc 5 (Visual Design & Polish) will be the final arc — a comprehensive visual pass that installs a proper design system across the whole app: CSS variables or a shared style object for the full palette, consistent card/panel spacing, polished empty states, a help/tooltip layer for advanced fields, monospace font on all numeric table cells, responsive improvements beyond the current 700px breakpoint, and accessibility improvements (focus rings, ARIA labels, keyboard navigation). Arc 5 is purely visual — no new functionality.

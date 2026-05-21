# Senna UX Redesign — Arc 1 Handoff (to Cursor Architect)

**Prepared by:** Claude (Cowork / UX Design Architect)  
**Date:** 2026-04-20  
**Arc:** 1 of 5 — Brand & Language Foundation  
**Iterations:** senna-iter-1 through senna-iter-5  
**Backend:** Untouched. All changes are frontend-only unless noted under Iter 1 (title tag / package name).

---

## Context

The MiroFish MVP is being renamed and redesigned as **Senna** — a policy simulation platform. MiroFish is an external Chinese research project that inspired this platform; it is not our own and must not appear in the product.

The backend (FastAPI, 29 iterations, 191 tests passing) is feature-complete and stays unchanged for this arc. All work is in `frontend/`.

### The 5 Arcs at a glance

| Arc | Theme | Iterations |
|-----|-------|------------|
| **1** | Brand & Language Foundation | senna-iter-1 – 5 |
| 2 | Run Setup Experience | senna-iter-6 – 10 |
| 3 | Live Experience & Results | senna-iter-11 – 15 |
| 4 | Advanced Features Accessible | senna-iter-16 – 20 |
| 5 | Visual Design & Polish | senna-iter-21 – 25 |

---

## Design Philosophy (applies to all 5 arcs)

**75/25 Rule:**
- **75% Apple design principles** — clean lines, system font stack (`-apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif`), generous whitespace, purposeful restraint, nothing decorative that isn't functional.
- **25% practical warmth** — labels, helper text, and contextual descriptions stay visible where they genuinely help the user act confidently. Don't strip everything into tooltips.

**Palette:**
- Background: `#F7F6F2` (warm off-white / quality paper feel)
- Card / panel surface: `#FFFFFF`
- Primary text: `#1A1A1A`
- Secondary / helper text: `#6B7280`
- Primary accent (interactive): `#4A6FA5` (calm slate-blue)
- Success / completed: `#4CAF82` (soft green)
- In-progress / amber: `#F59E0B`
- Error: `#E05252`
- Border: `#E5E3DC` (warm light grey)

> **Arc 1 note:** The design system is not fully installed until Arc 5. In Arc 1, make changes conservatively — correct the language and rename the brand, but don't try to rebuild the visual design yet. Where you touch styling incidentally, nudge toward the palette above, but don't refactor styles wholesale. That is Arc 5's job.

---

## Arc 1 Goal

By the end of Arc 1, a user opening the app for the first time will:
- See **Senna** — not MiroFish — everywhere
- Read plain-English labels on every form field and tab
- Get friendly, readable status messages while a run is in progress
- See a proper product header with name and tagline

They will not yet see a redesigned layout, a new visual design, or restructured navigation — those come in later arcs.

---

## Arc 1 — Iterations

---

### senna-iter-1 — Rename: MiroFish → Senna

**Goal:** Every reference to MiroFish (and "MVP") is replaced with Senna throughout the codebase.

**Scope — files to touch:**

| File | What to change |
|------|---------------|
| `frontend/index.html` | `<title>` tag: "MiroFish MVP Simulation" → "Senna" |
| `frontend/package.json` | `"name"` field: change to `"senna-frontend"` |
| `frontend/src/App.tsx` | `<h1>MiroFish MVP Simulation</h1>` → `<h1>Senna</h1>` (interim; Arc 1 Iter 5 will replace with proper header component) |
| `frontend/src/components/*.tsx` | Grep for "MiroFish" or "mirofish" — replace all occurrences in user-visible strings |
| `docs/handoffs/HANDOFF_TO_BUILDER.md` | Update bootstrap paragraph: "You are implementing MiroFish MVP" → "You are implementing Senna (formerly MiroFish MVP)" |
| `docs/SESSION_STATE.md` | Update project name field: MiroFish → Senna |

**Out of scope:** Backend package names (`mirofish_backend`) — leave untouched. The backend rename is a separate future task and would require pyproject.toml / import path changes that risk breaking 191 passing tests.

**Definition of done:**
- [ ] `grep -r "MiroFish" frontend/src/` returns zero results in user-visible strings (comments OK)
- [ ] `grep -r "MiroFish" frontend/index.html` returns zero results
- [ ] Browser tab shows "Senna"
- [ ] App heading shows "Senna"
- [ ] `npm run build` passes

**Closeout:** Write `docs/iterations/senna-iter-1-closeout.md`

---

### senna-iter-2 — Controls Tab: Plain-English Relabeling

**Goal:** Every form field in the Controls tab gets a plain-English label and, where helpful, a one-line description. Technical developer notes are removed from visible UI copy. An "Advanced options" collapsible section hides low-priority fields.

**Current labels → new labels:**

| Current label | New label | Helper text (shown beneath field, small) |
|---------------|-----------|------------------------------------------|
| Scenario | Policy scenario | — (the card picker in Arc 2 will handle this; for now keep dropdown but rename label) |
| Total rounds | Discussion rounds | "Each round, participants share their views. More rounds = richer deliberation." |
| Agent limit | Number of participants | "How many participants take part in the simulation." |
| Interaction mode | How participants take turns | — |
| `full_round_robin` option | Everyone speaks each round | — |
| `sample_k_per_round` option | Rotating speakers | — |
| Speakers per round (K) | Speakers per round | "How many participants speak in each round when using rotating mode." |
| LLM routing (optional) | AI model | — |
| `lmstudio` option | Local model | — |
| `anthropic` option | Claude (Anthropic) | — |
| `hybrid` option | Mixed (local + Claude) | — |
| `Server default` option | Server default | — |
| Random seed | Reproducibility seed | Move to Advanced options |
| Roster CSV (optional) | Custom participant list (CSV) | "Optional. Upload a CSV to specify exactly who participates." — Move to Advanced options |
| Population pool CSV (optional, Iteration 11) | Participant pool (CSV) | "Optional. Upload a pool of participants for Senna to sample from." — Move to Advanced options |
| Population sample mode | How to select participants | Move to Advanced options |
| `Weighted (within full pool)` | Weighted random | — |
| `Stratified (by stratum column)` | Stratified by group | — |
| Convergence stop (optional, Iteration 28) | Auto-stop when consensus is reached | Move to Advanced options |
| Threshold (0–1, empty = off) | Sensitivity (0.01 = very sensitive, 0.1 = loose) | "Leave blank to run all rounds regardless of consensus." |
| Patience (consecutive rounds) | Rounds to confirm consensus | "Senna will stop after this many rounds of stable opinion." |
| Start simulation | Start discussion | — |

**Advanced options collapsible:**
Fields to move inside a collapsed `<details><summary>Advanced options</summary>…</details>` section:
- Reproducibility seed
- Custom participant list (CSV)
- Participant pool (CSV)
- How to select participants
- Auto-stop when consensus is reached (the entire convergence block)

**Remove from visible UI copy entirely:**
- All "Iteration N" references in labels and helper text (e.g. "API cap 50 (Iteration 9)", "Iteration 10.", "Iteration 11")
- The `docs/plans/SCALE_LIMITS_AND_COST.md` link in the agent limit helper text — replace with: "For large simulations (over 20 participants), expect longer run times."
- The `config_snapshot` reference in the warnings block — replace with: "The run started, but check Run Details for the full configuration."
- `code` tags used as inline jargon (e.g. `` `agent_limit` ``, `` `random_seed` ``, `` `round_participants_only` ``) — remove from all user-visible copy

**Definition of done:**
- [ ] No "Iteration N" text visible in the Controls tab
- [ ] No raw field names (snake_case) visible in any label or helper text
- [ ] Advanced options section collapses/expands correctly
- [ ] All form fields still function identically
- [ ] `npm run build` passes

**Closeout:** Write `docs/iterations/senna-iter-2-closeout.md`

---

### senna-iter-3 — Navigation: Tab Relabeling & Grouping

**Goal:** All 10 tab labels are renamed to plain English. Tabs are visually grouped into primary (what most users need) and secondary (researcher/advanced tools).

**Current tab labels → new labels:**

| Tab ID | Current label | New label |
|--------|--------------|-----------|
| `controls` | Run | Set Up & Run |
| `live` | Live | Watch Live |
| `transcript` | Transcript | Conversation |
| `outcomes` | Outcomes | Results |
| `state` | State | Attitudes |
| `metadata` | Run metadata | Run Details |
| `validity` | Validity | Quality Notes |
| `experiments` | Experiments | Compare Runs |
| `agent` | Agent | Assistant |
| `scenarios` | Scenarios | Policy Scenarios |

**Visual grouping:**
Render the tab list in two groups, with a subtle visual separator (a small gap or a thin divider line) between them. Do not add labels like "Primary" / "Secondary" — just the spacing difference.

- **Primary tabs** (left / first group): Set Up & Run · Watch Live · Conversation · Results · Attitudes
- **Secondary tabs** (right / second group): Compare Runs · Assistant · Policy Scenarios · Quality Notes · Run Details

> The tab *order* is a UX judgment — primary tabs are what a first-time user needs in sequence. Secondary tabs are researcher tools or advanced views.

**Definition of done:**
- [ ] All 10 tabs show new labels
- [ ] Two visual groups are distinguishable (gap, divider, or subtle style difference)
- [ ] All tab switching still works correctly
- [ ] No `TabId` type values changed (internal IDs stay the same — only display labels change)
- [ ] `npm run build` passes

**Closeout:** Write `docs/iterations/senna-iter-3-closeout.md`

---

### senna-iter-4 — Status Messages: Plain-English Run State

**Goal:** Replace raw status strings with friendly, contextual messages throughout the Controls / Set Up & Run tab.

**Status string mapping:**

| Raw status | User-visible message |
|------------|---------------------|
| `idle` | "Ready to start a new discussion." |
| `starting` | "Starting up…" |
| `running` | "Discussion in progress — Round {currentRound} of {totalRounds} underway." |
| `completed` | "Finished! All {totalRounds} rounds completed." (if converged: "Finished! Consensus reached at Round {convergedAtRound}.") |
| `failed` | "Something went wrong. See Run Details for more information." |
| `timeout` | "The run timed out after too long without a response. Check your AI model connection." |
| any string starting with `error:` | "Error: {message after 'error: '}." |

**Progress copy:**
- Current: "Progress (rounds completed): {currentRound}"
- New: "Round {currentRound} of {totalRounds} complete" — or "Not started yet" when currentRound is 0 and status is `idle`

**Running footnote:**
- Current: "This counter moves after each round completes (after all scheduled turns in that round). In sample-K mode, fewer turns run per round. While it stays at 0, the model is still working — open the Transcript tab to see each turn appear as it completes."
- New: "Senna updates after each full round. If the counter hasn't moved yet, the first round is still in progress — open Conversation to watch turns appear live."

**Turns-in-transcript line (shown while running):**
- Current: "Turns in transcript: {n} · polling ~750ms while running — open Live for charts"
- New: "{n} exchanges recorded — open Watch Live for charts"

**Start button:**
- `status === "starting"` → button text: "Starting…"
- `status === "running"` → button text: "Running…" + disabled
- otherwise → "Start discussion"

**Open run by ID:**
- `<input placeholder="simulation id" />` → `<input placeholder="Paste a run ID to reload a previous session" />`

**Definition of done:**
- [ ] No raw status strings (`running`, `starting`, `failed`, `timeout`) visible to user
- [ ] Convergence message shows correctly when `convergedAtRound` is set
- [ ] Error messages strip the `error:` prefix and display cleanly
- [ ] `npm run build` passes

**Closeout:** Write `docs/iterations/senna-iter-4-closeout.md`

---

### senna-iter-5 — Senna Header Component

**Goal:** Replace the bare `<h1>Senna</h1>` with a proper product header component that establishes Senna as a product, not a script.

**Header component spec (`SennaHeader.tsx`):**

```
┌─────────────────────────────────────────────────────────┐
│  ● Senna                    [status pill]               │
│    Policy simulation platform                           │
└─────────────────────────────────────────────────────────┘
```

- **Logo mark:** A small filled circle (●) in the primary accent colour (`#4A6FA5`) — 10px diameter, inline before the wordmark. This is the placeholder for a future logo. Do not use an SVG icon library — just a CSS circle (`border-radius: 50%`, `background: #4A6FA5`, `width: 10px`, `height: 10px`).
- **Wordmark:** "Senna" in `-apple-system` (or system font stack), `font-size: 22px`, `font-weight: 600`, `color: #1A1A1A`, `letter-spacing: -0.3px`
- **Tagline:** "Policy simulation platform" in `font-size: 13px`, `color: #6B7280`, `font-weight: 400`, on the line below the wordmark
- **Status pill:** Right-aligned. A small pill (`border-radius: 999px`, `padding: 3px 10px`, `font-size: 12px`) showing the current run status in plain English (from Iter 4 mapping). Colour:
  - idle / ready → grey background (`#E5E3DC`), dark text
  - running → amber background (`#FEF3C7`), amber-dark text (`#92400E`)
  - completed → soft green background (`#D1FAE5`), green-dark text (`#065F46`)
  - failed / error / timeout → soft red background (`#FEE2E2`), red-dark text (`#991B1B`)
- **Separator:** A 1px bottom border in `#E5E3DC` below the header, with `margin-bottom: 20px`
- **Background:** `#F7F6F2` (matches page background — header is not a different colour block)

**In `App.tsx`:**
- Import and render `<SennaHeader status={status} currentRound={currentRound} totalRounds={totalRounds} convergedAtRound={convergedAtRound} />` at the top, replacing the old `<h1>`
- The status prop should use the same mapping as Iter 4 to produce the pill label

**Definition of done:**
- [ ] `SennaHeader.tsx` created in `frontend/src/components/`
- [ ] Header renders correctly with logo mark, wordmark, tagline, and status pill
- [ ] Status pill colour changes correctly across all states (test by starting a run and watching it progress)
- [ ] Old `<h1>MiroFish MVP Simulation</h1>` (or `<h1>Senna</h1>`) removed from App.tsx
- [ ] `npm run build` passes

**Closeout:** Write `docs/iterations/senna-iter-5-closeout.md`

---

## Arc 1 — Architect Instructions

Work through iterations **sequentially**: senna-iter-1 → 2 → 3 → 4 → 5.

For each iteration:
1. Seed Builder with the iteration spec from this document (the relevant `###` section)
2. Include the standard bootstrap: read `docs/SESSION_STATE.md` + `docs/handoffs/HANDOFF_TO_BUILDER.md` + this file first
3. Builder implements, runs `npm run build`, writes closeout
4. Architect reviews closeout + build output
5. If PASS → seed next iteration. If PASS_WITH_ISSUES → resolve follow-ups before next iteration.

**Builder bootstrap (paste into each new Cursor chat):**

> You are implementing the Senna UX redesign in `mirofish-mvp/frontend/`. Read in order:
> 1. `docs/SESSION_STATE.md`
> 2. `docs/handoffs/HANDOFF_SENNA_ARC1.md` (this handoff — full spec for Arc 1)
> 3. Then jump to the **senna-iter-N** section for the current iteration.
>
> Rules: Match existing code style. Frontend changes only (backend untouched). Run `npm run build` in `frontend/` after changes. Write `docs/iterations/senna-iter-N-closeout.md` when done. Do not expand scope beyond the active iteration spec.

---

## Arc 1 — Definition of Arc Complete

All five of the following must be true before handing back to Claude (Cowork) for arc review:

- [ ] `grep -r "MiroFish" frontend/src/` returns zero user-visible string matches
- [ ] Browser tab reads "Senna"
- [ ] All form field labels are in plain English (no snake_case, no "Iteration N" references)
- [ ] All 10 tabs have new plain-English labels, in two visual groups
- [ ] All status messages are plain English and contextually accurate
- [ ] `SennaHeader` component renders with correct logo mark, tagline, and live status pill
- [ ] `npm run build` passes clean

---

## Arc 1 — Summary Template (Architect fills on completion)

```
Arc 1 complete — [date]
Iterations shipped: senna-iter-1, 2, 3, 4, 5
Build: PASS / FAIL
Deferred items: [list anything deferred or out of scope]
Notes for Claude review: [anything the UX architect should pay attention to]
```

---

## What Comes Next (Arc 2 preview)

Arc 2 (Run Setup Experience) will restructure the Controls tab into a proper guided setup flow — scenario cards, Quick Setup vs Advanced tiers, a step-by-step launch wizard, and a redesigned participant configuration UI. Arc 2 handoff will be produced by Claude (Cowork) after Arc 1 is reviewed and approved.

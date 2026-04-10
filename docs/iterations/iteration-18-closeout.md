# Iteration 18 closeout — Minister / Agent UI (ask-first)

**Date:** 2026-04-02 (initial ship)  
**Status:** Shipped  
**Closeout amended:** reflects post-ship UI fixes and behaviour notes (extend this file when Iteration 18 changes again; if work belongs to a new gate, add **`iteration-19-closeout.md`** instead).

## Shipped

### 1. Agent console (`frontend/src/components/AgentConsole.tsx`)

- **Primary:** single **Ask** flow — research question (API min 8 chars) → **`POST /agent/ask`** (JSON) → per-run **results** (status, errors, key findings, narrative, follow-ups).
- **Expandable plan:** after a successful ask, **Show execution plan (JSON)** reveals the planner output without leaving the page.
- **Advanced (collapsed by default):** optional **constraints**; **wait timeout per run** (30–7200s); optional **planner temperature** and **plan max tokens**; **Plan only** (`POST /agent/plan`) fills the execute JSON editor; **Execute JSON plan** (`POST /agent/execute`) for paste/edit **`ExecutionPlan`** workflows.

### 2. Run result cards (`frontend/src/components/RunResultCard.tsx`)

- Shared **per-run** layout for **Ask** and **Execute** (status, sim id, errors, queue/generate warnings, findings, narrative, follow-ups).

### 3. API client (`frontend/src/lib/api.ts`)

- Types: **`ExecutionPlan`**, **`AgentRunReport`**, **`AgentAskResponse`**, request shapes.
- **`agentPlan`**, **`agentExecute`**, **`agentAsk`** — same-origin **`/agent/*`**; optional **`AgentFetchInit`** / **`AbortSignal`** for cancel.

### 4. App shell (`frontend/src/App.tsx`)

- Tab **Agent** (after **Run**).
- **All tabs stay mounted** when switching: **`tabPanelStyle` / `tabPanelHidden`** on each panel (**`display: none`** when inactive, **`aria-hidden`**). Avoids losing **Agent** in-flight **`fetch`**, **Run** form state, **Live**/**Scenario** local state, and half-filled forms (e.g. Validity).
- **Agent vs Run (UX):** **`POST /agent/ask`** persists runs like **`POST /simulations/run`** — they appear under **Recent runs** (**`GET /simulations`**). **Current run** / **Live** / **Transcript** in **Run** only track runs started or **loaded** from that tab (or load-by-ID); Agent does not push **`runId`** into that shell state unless we add wiring later.

## Definition of done

- [x] Ask-first UI + optional advanced plan/execute (review-friendly layout).
- [x] `npm run build` passes; backend `pytest` unchanged.
- [x] This closeout; `SESSION_STATE.md`; `HANDOFF_TO_ARCHITECT.md` updated.

## Architect PASS follow-ups (post–review UI polish)

- **`RunResultCard`** — Execute path uses structured cards (not raw JSON only).
- **Cancel request** + **`AbortSignal`** on all three agent **`fetch`** calls.
- **Question** field: empty default + **placeholder** (no pre-filled essay).
- **Elapsed** seconds during in-flight agent requests.
- **Advanced** tuning: numeric inputs, **min/max**, inline range warnings; buttons disabled when invalid.
- Documented in **`HANDOFF_TO_BUILDER.md`** § *Iteration 18 — PASS* as addressed (item 6 SSE still deferred).

## Deferred

- SSE live log in the browser (Iteration 17 SSE remains **`curl`** / manual).
- Promoting Plan/Execute to top-level tabs if product prefers pipeline-first UX.
- Optional: auto-**load** Agent-returned **`simulation_id`** into **Current run** / **poll** for Live+Transcript parity.

## Operational note (analyze / local LLM)

- **`/agent/ask`** ends with **`/simulations/{id}/analyze`**; **LM Studio** with small **`n_ctx`** (e.g. 4096) can return **502** if the analyze bundle exceeds context. **Anthropic** (or larger local context) is the usual fix; clipping budgets in **`api/simulations.py`** remain tuned for larger models — not a plan-JSON issue.

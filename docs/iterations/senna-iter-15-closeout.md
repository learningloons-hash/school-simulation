# senna-iter-15 closeout — Run Details & export: plain language

**Date:** 2026-04-20  
**Scope:** `docs/handoffs/HANDOFF_SENNA_ARC3.md` § senna-iter-15 and § *Architect / reviewer emphasis* (3).

## Shipped

### Run Details (`App.tsx` — `tabPanelStyle("metadata")`)

- **Session ID** line (monospace value) replacing bare “Run id”.
- **Download** block at top (when `runId` and status is `completed`, `failed`, or `running`): primary **Download full report** (ZIP via `exportZipUrl`), secondary **Export as JSON** (`downloadExportJson`), helper line under actions.
- **AI usage** card: total tokens (`~` + `toLocaleString()`), estimated cost with `$` when `estimated_cost_usd > 0`, else **Free (local model)** when `llm_provider` is `lmstudio` or `""`, else **—**; tier line in plain English (Full / Simplified / Rule-based turns).
- Placeholder copy when a run is loaded but economics are not yet available.
- **Technical configuration** `<details>`: JSON `configSnapshot` in `#F7F6F2` `<pre>`, empty message when no snapshot; **Sampling report** link moved inside (completed/failed only).
- Removed **`state_audit_enabled`** paragraph and standalone config / sampling layout.

### Quality Notes (`validity` tab)

- Intro paragraph in plain English (no API paths / export jargon).
- **Noting quality for session:** truncated id when `runId` set; otherwise **Load a run first to add notes.**

### Downloads consolidated (§5)

- **`RunStatusCard`:** removed **Download report** link and **`exportZipUrl` / `onDownloadJson`** props.
- **Recent discussions:** removed per-row **Download** control; **Open** remains.

## Post-change search (export entry points)

Intended commands: `rg exportZipUrl frontend/src` and `rg downloadExportJson frontend/src` (or equivalent search under `frontend/src/`).

**Matches (verified):**

- `frontend/src/lib/api.ts` — definitions only.
- `frontend/src/App.tsx` — imports plus **Run Details** (`href={exportZipUrl(runId)}`, `downloadExportJson(runId)` in the Download section).

No `RunStatusCard`, recent-list, or other UI call sites remain. Simulation ZIP/JSON for loaded runs is offered **only** from Run Details.

## Verification

- `npm run build` in `frontend/` — PASS

## Not in scope

- Arc 4 and later.

# Handoff to builder (implementation agent)

Copy this into a **new Cursor chat** when starting work on an iteration or slice. Fill every bracketed field. The human pastes architect notes below if needed.

## Bootstrap (paste first message)

You are implementing MiroFish MVP in `mirofish-mvp`. Read in order:

1. `docs/SESSION_STATE.md`
2. **`docs/handoffs/BRIEF_FOR_JOAN.md`** — architect briefing (scale, UX sequencing, iterations 8–12 outline); read before deep UX or large-N work.
3. `docs/handoffs/HANDOFF_TO_BUILDER.md` (this file)
4. **Previous gate closeout** — e.g. starting **Iteration 18** → [`docs/iterations/iteration-17-closeout.md`](../iterations/iteration-17-closeout.md)
5. **Active starter** — jump to **[Iteration 18 starter](#iteration-18-starter-pre-filled--2026-04-05)** below (or the matching § for your slice)
6. [Optional] Custom scope in the **empty template** § only if there is no pre-filled starter for this slice

**Rules:** Match existing code style; do not expand scope beyond the active starter; run **`uv run pytest`** from `backend/` (or `PYTHONPATH=src pytest tests/` if you are not using `uv`); run **`npm run build`** in `frontend/` when the UI changes; update `SESSION_STATE.md` and add `iteration-N-closeout.md` at the end.

---

## Where to start in this file

| If you are starting… | Go to |
|----------------------|--------|
| ~~**Pre-21 housekeeping**~~ (done) | ~~`export_version` fix~~ — shipped in Iteration 21. |
| ~~**Iteration 21**~~ (done) | ~~Generic engine cleanup~~ — shipped, PASS. |
| ~~**Pre-22 fixes**~~ (done) | ~~3 fixes from Iter 21 review~~ — applied in Iteration 22. |
| ~~**Iteration 22**~~ (done) | ~~Sampling strategy contract~~ — shipped, PASS. |
| ~~**Pre-23 fixes**~~ (done) | ~~2 test gaps from Iter 22 review~~ — applied in Iteration 23. |
| ~~**Iteration 23**~~ (done) | ~~Tier-aware orchestrator~~ — shipped, PASS. |
| ~~**Pre-24 fix**~~ (centralize `EXPORT_VERSION`) | **Applied** — `export_bundle.EXPORT_VERSION`; see [`iteration-23-closeout.md`](../iterations/iteration-23-closeout.md) § Post–Architect follow-up |
| ~~**Iteration 24**~~ (done) | ~~Heuristic + hybrid + 300~~ — shipped; see [`iteration-24-closeout.md`](../iterations/iteration-24-closeout.md) |
| ~~**Iteration 26**~~ (done) | ~~posture_maxvar + sampling report~~ — [`iteration-26-closeout.md`](../iterations/iteration-26-closeout.md) |
| ~~**Post-Iteration 26 hardening**~~ (done) | ~~Architect PASS_WITH_ISSUES follow-ups~~ — applied 2026-04-07 (SESSION_STATE, E2E test, roster comment, sampling-report UI link) |
| ~~**Iteration 25**~~ (done) | ~~Network + ADR-002 visibility~~ — [`iteration-25-closeout.md`](../iterations/iteration-25-closeout.md) |
| ~~**Post-Iteration 25 hardening**~~ (done) | ~~Architect follow-ups~~ — applied 2026-04-07; see [`iteration-25-closeout.md`](../iterations/iteration-25-closeout.md) § Post–Iteration 25 hardening |
| ~~**Iteration 27**~~ (done) | ~~Experiments framework~~ — [`iteration-27-closeout.md`](../iterations/iteration-27-closeout.md) |
| ~~**Post-Iteration 27 hardening**~~ (done) | ~~Architect PASS_WITH_ISSUES follow-ups~~ — applied 2026-04-07; see [`iteration-27-closeout.md`](../iterations/iteration-27-closeout.md) § Post–Iteration 27 hardening |
| ~~**Iteration 28**~~ (done) | ~~**Convergence stopping criterion**~~ — [`iteration-28-closeout.md`](../iterations/iteration-28-closeout.md) |
| ~~**Post-Iteration 28 hardening**~~ (done) | ~~Architect PASS_WITH_ISSUES follow-ups~~ — applied 2026-04-08; see [`iteration-28-closeout.md`](../iterations/iteration-28-closeout.md) § Post–Iteration 28 hardening |
| ~~**Iteration 29**~~ (done) | ~~**Run economics dashboard**~~ — [`iteration-29-closeout.md`](../iterations/iteration-29-closeout.md) |
| **Next slice** | Backlog / next numbered iteration (see [`SESSION_STATE.md`](../SESSION_STATE.md)) |
| An older numbered slice (11–20) | **Historical starters** below + matching **PASS** notes under **Architect reviews** |
| A one-off / unnumbered slice | Empty **template** § below (fill brackets, then paste into a new chat) |

**Execution order (Opus-approved):** 21 → 22 → 23 → 24 → **26** → **25** → **27** → **28** → **29**. All **shipped** (post-27 / post-28 hardening applied; Iteration **29** 2026-04-08).

**ADR-002** (Interaction Visibility Policy) is filed at `docs/adr/ADR-002-interaction-visibility.md`. Read before Iteration 25.

**Architect reviews (PASS)** are sign-off records (Iterations 10–20). They are **not** the task spec — the **starter** for your iteration is.

---

## Scope *(ad-hoc template — prefer a pre-filled starter below)*

- **Iteration / slice:** [e.g. Iteration 5 — RAG scaffold + second scenario]
- **In scope:** [bullets]
- **Out of scope / defer:** [bullets]

## Definition of done

- [ ] [Concrete outcomes, e.g. second scenario selectable in UI; RAG block in user prompt when flag on]
- [ ] `uv run pytest` from `backend/` passes (or `PYTHONPATH=src pytest tests/` with project venv)
- [ ] `npm run build` in `frontend/` passes (if UI touched)
- [ ] `docs/SESSION_STATE.md` updated (Current Status, Completed Work, Gate Evidence)
- [ ] `docs/iterations/iteration-N-closeout.md` added for this gate
- [ ] Fill `docs/handoffs/HANDOFF_TO_ARCHITECT.md` (or paste equivalent summary for architect chat)

## Key files (hints)

[Paths the architect cares about — e.g. orchestrator, new `rag/` package, `api/simulations.py`]

## Decisions already made

[Architecture choices — e.g. embeddings via LM Studio `/v1/embeddings`, SQLite `rag_chunks`]

## Risks / watch

[e.g. n_ctx budget; don’t log API keys]

---

## Architect notes (optional paste)

[Human pastes short steering from architect chat here]

---

## Architect reviews (sign-off records)

### Iteration 10 — PASS (reviewed 2026-04-04)

**Theme:** Thin `AgentContextV1` + interaction `simulation_mode` (`full_round_robin` | `sample_k_per_round`).

**What's good:** `AgentContextV1` is a clean versioned contract. Deterministic sampling via seed-stable RNG. Non-speaker agents documented (state unchanged). `spoke_this_round` traceability on snapshots. ADR-001 Interface section concrete.

**Non-blocking improvements noted:**

1. No record of *who was silent* in the transcript (only snapshots have `spoke_this_round`).
2. `_build_interaction_plan` uses the sampled subset for `turn_index` assignment — correct, but worth a comment explaining that turn indices are relative to the speaking cohort, not the full roster.
3. `interaction_last_k` for first turn of round > 1 uses full roster size even in `sample_k_per_round` — addressed in Iteration 12.
4. `effective_provider` not yet persisted — addressed in Iteration 12.
5. `speakers_per_round` default of 2 shows in `config_snapshot` even for `full_round_robin` — addressed (stores `null` for full RR).

---

### Iteration 11 — PASS (reviewed 2026-04-04)

**Theme:** Single population-table contract — pool CSV, weighted/stratified draw, `AgentContextV1` alignment, `config_snapshot` provenance.

**What's good:** Clean contract boundary (`population/` module). Deterministic draw with isolated RNG. Stratified largest-remainder allocation is correct. Layered merge precedence (population → roster) is explicit and auditable. Comprehensive provenance in `config_snapshot` (`population_draw` trace, merge order, thesis note). ADR amended with concrete population contract section.

**Non-blocking improvements noted:**

1. No test for per-stratum oversubscription error (global pool-too-small is tested, stratum-level is not).
2. `_row_to_dummy_roster_row` creates `ParsedRosterRow(slot=0)` — adapter works but mild code smell; shared merge function would be cleaner.
3. Unknown group IDs accepted silently in API response (only in `config_snapshot`) — addressed in Iteration 12 with `warnings[]`.
4. Weighted sampling is O(k*n) — fine for current scale, note for 10k+ pools.
5. Closeout self-check could match checklist item wording more exactly.

---

### Iteration 12 — PASS (reviewed 2026-04-05)

**Theme:** Per-turn LLM traceability (`effective_provider` / `effective_model`), run `warnings[]`, export v3, sample-K `interaction_last_k` tweak, stress test.

**What's good:** End-to-end traceability from orchestrator → DB → poll API → export JSON/ZIP. Non-breaking API evolution (`warnings` default-empty). Additive `export_version` bump (3). `interaction_last_k` for sample-K now cohort-scaled. Defensive export defaults for empty transcripts. Hybrid persistence test well-structured (verifies alternating providers across rounds + export bundle path).

**Non-blocking improvements noted:**

1. Stress test ceiling too generous (30s for 40 fake-LLM turns that complete in <1s) — tighten to ~5s.
2. No test for population CSV warnings (only roster warnings tested).
3. `effective_model_id` falls back to bare provider name on empty model string — pragmatic but consider validation.
4. `interaction_last_k` formula magic numbers (`* 3`, cap `120`) not documented outside code — added to ADR in Iteration 13 amendment.
5. Parallel LLM deferral from brief not called out as deviation in handoff — added in Iteration 13 handoff.

**Hybrid semantics confirmed:** `resolve_effective_provider` sends `turn_index == 1` to Anthropic, all others to LM Studio. Deterministic and replay-friendly. Thesis can describe as "frontier model anchors each round's opening broadcast."

---

### Iteration 13 — PASS (reviewed 2026-04-05)

**Theme:** Structured persona attributes (`identity`, `attitudes`, `personal_history`) on `AgentContextV1` (version 2), population CSV schema v2, prompts, persistence (`attribute_sections_json`), export v4.

**What's good:** Clean contract extension — three new `dict[str, Any]` fields with backward-compatible defaults. Population CSV v2 is additive (old v1 rows still parse). Two-layer validation (scenario `validate.py` + `_parse_json_object_cell`). Prompt integration uses existing `_profile_lines` helper. End-to-end test verifies YAML → context → prompt content → DB → API. ADR updated with complete interface table. Documentation thorough.

**Non-blocking improvements noted:**

1. `demographic_overrides` parameter now carries non-demographic data (identity/attitudes/personal_history) — name is misleading; consider renaming to `slot_overrides` in a future cleanup.
2. Shallow merge semantics (`dict.update()`) not documented for analysts — suggest one-liner in population CSV template or help text.
3. No export bundle test for `attribute_sections` (poll API path tested, ZIP/JSON export path not).
4. No single `export_version` changelog (v1→v2→v3→v4 spread across closeouts) — suggest table in ADR or `export_bundle.py`.
5. Only principal persona has example attributes in PSLE YAML (HoD and teacher have none).
6. No test for valid-JSON-but-not-an-object in population CSV column (e.g., array `[1,2]`).

**Iteration 14 priority recommendation:** UI-first (sectioned editor in Scenario Wizard), then constrained randomize / LLM fill. Parallel LLM stays backlog unless wall-clock pain emerges on real runs.

---

## Historical starters (Iterations 11–17)

The blocks below are **archive / cold-start reference** for completed gates. For **new work**, use **[Iteration 18 starter](#iteration-18-starter-pre-filled--2026-04-05)** (or the empty template § above if unnumbered).

---

## Iteration 11 starter (pre-filled — 2026-04-04)

Copy the block below into a **new** Cursor chat when starting Iteration 11. Replace bracketed items after architect sign-off.

### Scope

- **Iteration / slice:** Iteration 11 — **Population table contract** (single importer) + **weighted/stratified sampling** + **`config_snapshot` provenance**; keys aligned to **`AgentContextV1`** per [`docs/adr/ADR-001-iteration-10-11-contracts.md`](../adr/ADR-001-iteration-10-11-contracts.md).
- **In scope:** Versioned population artefact (CSV or agreed format); column → context field mapping; deterministic draw given `random_seed` (+ document interaction with `simulation_mode`); provenance on run record; tests; `iteration-11-closeout.md`.
- **Out of scope / defer:** Full attribute schema UI (13+); IAD rules in code; group-based visibility graph; second parallel import format.

### Definition of done

- [ ] One population path documented and implemented; no duplicate “other” importer for the same role.
- [ ] `PYTHONPATH=src pytest tests/` passes; `npm run build` if UI touched.
- [ ] `docs/SESSION_STATE.md` + `docs/iterations/iteration-11-closeout.md` updated; [`HANDOFF_TO_ARCHITECT.md`](HANDOFF_TO_ARCHITECT.md) refreshed for Iter 12 prep.
- [ ] [`ARCHITECT_SIGNOFF_CHECKLIST_ITER10_11.md`](ARCHITECT_SIGNOFF_CHECKLIST_ITER10_11.md) Iter 11 rows satisfied or explicitly waived.

### Key files (hints)

`backend/src/mirofish_backend/simulation/agent_context.py`, `orchestrator.py`, `api/simulations.py`, roster/csv modules, export builders, `frontend` Run tab if new controls.

### Decisions already made

Iteration 10 shipped **`AgentContextV1`** and **`simulation_mode`**; Iteration 11 extends **the same** contract family per ADR-001.

### Risks / watch

Precedence when **roster_csv**, **YAML personas**, and **population table** all exist; keep **one** resolution order documented in ADR or closeout.

---

## Iteration 12 starter (pre-filled — 2026-04-04)

### Scope

- **Iteration / slice:** Iteration 12 — **`effective_provider`** (± model id) **persisted per turn**; **export** bundle + CSV; minimal **stress / perf** note or harness; optional **`interaction_last_k`** scaling review (Iteration 10 architect note); optional **`warnings[]`** on **`POST /simulations/run`** for roster/population **unknown `group_ids`** (and similar) so analysts see issues without reading `config_snapshot` first.

### Definition of done

- [ ] DB + API + exports carry per-turn routing field(s); `iteration-12-closeout.md`; `SESSION_STATE.md` updated.
- [ ] Brief / architect items above **confirmed or explicitly waived** in closeout.
- [ ] `pytest` + `npm run build` (if UI touched).
- [ ] `HANDOFF_TO_ARCHITECT.md` refreshed for Iteration 13 / attributes arc.

### Key files (hints)

`db/schema.py`, `db/repo.py` (`insert_agent_turn`, export queries), `llm/router.py`, `simulation/orchestrator.py`, `export_bundle.py`, `frontend` if run metadata displays provider.

---

## Iteration 13 starter (pre-filled — 2026-04-04)

Use after architect signs off **Iteration 12** and defines the first **13+** slice (rich attributes / UI).

### Scope

- **Iteration / slice:** **Iteration 13+** — survey-like persona sections, validation, sectioned UI, constrained randomize, optional LLM fill — **only** as extensions of **`AgentContextV1`** / ADR-001 (no parallel context type without ADR bump).
- **In scope:** Architect-approved subset from [`docs/plans/agent-attributes-roadmap.md`](../plans/agent-attributes-roadmap.md).
- **Out of scope / defer:** Unless explicitly added — parallel LLM batching, network/edges import, scenario marketplace.

### Definition of done

- [ ] Contract/version bump documented (ADR + `config_snapshot` if needed).
- [ ] `pytest` + `npm run build` if UI touched.
- [ ] `SESSION_STATE.md` + `iteration-13-closeout.md` (or named slice closeout).
- [ ] `HANDOFF_TO_ARCHITECT.md` refreshed.

### Key files (hints)

`simulation/agent_context.py`, roster/population merge, prompts, `api/simulations.py`, `frontend` Run / persona editors.

### Decisions already made

**Iteration 13** shipped per `iteration-13-closeout.md` — **`AgentContext`** section maps, population CSV **v2**, export **v4**.

---

## Iteration 14 starter (pre-filled — 2026-04-04)

### Scope

- **Iteration / slice:** **14+** — UI for **`identity` / `attitudes` / `personal_history`** (scenario wizard or new panel); optional **constrained randomize**; optional **LLM fill** with validation; optional roster CSV **`_json`** columns.
- **Out of scope unless added:** Parallel LLM batching; network/edges.

### Definition of done

- [ ] Architect-approved scope; `pytest` + `npm run build` if UI touched.
- [ ] `SESSION_STATE.md` + `iteration-14-closeout.md`; ADR bump if contract changes.
- [ ] `HANDOFF_TO_ARCHITECT.md` refreshed.

### Key files (hints)

`frontend` Scenario wizard / forms, `scenarios/validate.py`, `population/csv_population.py`, `simulation/agent_context.py`.

---

### Iteration 14 — PASS (reviewed 2026-04-05)

**Theme:** Researcher persona UX — sectioned attribute editor (identity / attitudes / personal_history), LLM fill, constrained randomize, roster CSV `_json` columns.

**What's good:** All three sections (identity, attitudes, personal_history) wired end-to-end: roster CSV parses them, `merge_persona_for_slot` applies shallow-merge correctly (roster wins on conflict, same semantics as population CSV v2). `POST /scenarios/{id}/llm-fill` endpoint is a clean addition — uses the existing LLM router, lenient JSON parsing, returns `raw_llm_text` for debugging. Frontend key-value editor is usable and non-destructive (Show/Edit toggle, Randomize local, LLM Fill async). `toSectionMap` normalises any server shape to `Record<string, string>` safely.

**Non-blocking improvements noted:**

1. `ROSTER_CSV_TEMPLATE` now has a comment line starting with `#` — the CSV parser must handle `#`-prefixed rows gracefully (it does via the existing comment-row guard; confirmed in test).
2. `randomizeSections` uses a fixed vocabulary — fine for MVP; a schema-driven option list would be more robust longer term.
3. `LlmFillRequest.sections` defaults to all three sections — if the user only wants one, they pass a list; this is not yet exposed in the wizard UI (always fills all three).
4. `POST /scenarios/{id}/llm-fill` proxies to LM Studio by default even in hybrid mode — acceptable for a fill utility but worth noting in docs.
5. Closeout test counts drift as the suite grows — use **`SESSION_STATE.md` § Gate Evidence** as the canonical “tests passed” line for any gate.

**Gate confirmed:** Researcher can add structured attributes to a persona through the wizard UI without touching YAML or JSON directly. Roster CSV schema now matches population CSV v2.

---

### Iteration 15 — PASS (reviewed 2026-04-05)

**Theme:** IAD interaction rules + network topology — named policy objects (`ChannelType`, `TurnOrderPolicy`, `VisibilityPolicy`, `InteractionOverlay`), turn order, visibility graph, Trinidad overlay, wired into orchestrator and API.

**What's good:** Clean architecture — all ad-hoc strings replaced with named enums in a single module (`interaction_policy.py`). `build_interaction_policy()` factory validates inputs and applies the upgrade rule (Trinidad → hierarchical) in one place. `apply_turn_order` is a pure function (no mutation). `visible_turns_for_agent` correctly handles the broadcast / group / own-turn cases and has a sensible fallback (no groups → full visibility). `channel_for_turn` Trinidad path is well-specified. All policy parameters flow through to `config_snapshot` under `interaction_policy` sub-object with `policy_version = "1"` — reproducible and auditable. `ScenarioConfig.interaction_overlay` allows YAML authors to bake the overlay into a scenario without requiring researchers to know to pass it at run time. Strong targeted test coverage; total suite size — see **`SESSION_STATE.md`** Gate Evidence for the current run.

**Non-blocking improvements noted:**

1. `ADR-002` referenced in closeout but not written yet — create it as a follow-up (the code is the primary contract for now).
2. `MEETING` channel still broadcasts to `"all"` in `_build_interaction_plan` — group-scoped meeting notes are the next natural step; document the gap in ADR-002.
3. Researcher UI has no controls for `turn_order_policy` / `visibility_policy` yet — these are API-only parameters. Add to Run form in a future slice (no urgency; defaults are safe).
4. `interaction_overlay` is read from `scenario.interaction_overlay` inside `run_simulation_task` as the "effective overlay" when the API field is `"none"` — this logic is correct but the precedence rule (API field > scenario field) should be documented explicitly.
5. `apply_turn_order` result replaces `round_agents` after `_agents_for_round` sampling — confirm that `sample_k_per_round` interacts correctly (sampling happens first, then the sampled subset is reordered; this is the right behaviour).

**Gate confirmed:** Full parameter space for interaction rules locked in code as a versioned contract. Agent layer (Iteration 17) can now safely encode this vocabulary without expecting a refactor.

---

## Iteration 16 starter (pre-filled — 2026-04-05)

### Scope

- **Iteration / slice:** **Iteration 16** — **Agent-ready API surface**: three new meta-endpoints (`POST /scenarios/generate-from-brief`, `GET /capabilities`, `POST /simulations/{id}/analyze`) and a **"Generate from brief"** button in the Scenario Wizard.
- **In scope:**
  - `POST /scenarios/generate-from-brief` — plain-English brief → validated scenario document (calls LLM, runs through `validate_scenario_document`, returns for review/save).
  - `GET /capabilities` — returns the full current parameter space in structured form (interaction modes, simulation modes, population draw modes, attribute section schema, export version, IAD overlay options). Schema-driven; agent reads this at runtime.
  - `POST /simulations/{id}/analyze` — after a run completes, calls LLM with export bundle + `research_question`; returns structured analysis (`key_findings`, `per_agent_summary`, `trajectory_narrative`, `suggested_follow_ups`). Stateless — caller saves.
  - Scenario Wizard: **"Generate from brief"** button calls the new endpoint and hydrates the wizard form.
- **Out of scope / defer:** Agent orchestration layer (Iteration 17); Minister UI (Iteration 18); parallel LLM.

### Definition of done

- [x] All three endpoints implemented and tested.
- [x] "Generate from brief" button in Scenario Wizard calls `POST /scenarios/generate-from-brief` and populates the form.
- [x] `GET /capabilities` response is schema-driven — no hard-coded strings that will go stale.
- [x] `pytest` passes; `npm run build` passes.
- [x] `iteration-16-closeout.md` written; `SESSION_STATE.md` updated.

### Key files (hints)

`backend/src/mirofish_backend/api/` (new files: `scenarios_generate.py`, `capabilities.py`; extend `simulations.py` for `/analyze`), `backend/src/mirofish_backend/main.py` (router registration), `frontend/src/components/ScenarioWizard.tsx`, `frontend/src/lib/api.ts`.

### Decisions already made

- `validate_scenario_document` is the single validation path — the generate-from-brief endpoint must pass through it.
- `GET /capabilities` must reflect `interaction_policy.py` enums at runtime (not hard-coded lists).
- `/analyze` is stateless and does not write to the DB — the agent/Minister layer caches what it needs.

### Risks / watch

- LLM-generated scenario documents may fail `validate_scenario_document` — return the validation errors to the caller with a `422` so the agent can retry with a prompt correction.
- `/analyze` passes the full export bundle to the LLM — watch context length; clip or summarise transcript if bundle is large.

---

### Iteration 16 — PASS (reviewed 2026-04-05)

**Theme:** Agent-ready API surface — `POST /scenarios/generate-from-brief`, `GET /capabilities`, `POST /simulations/{id}/analyze`, wizard "Generate from brief" button.

**What's good:** `GET /capabilities` is genuinely schema-driven — enum values from `interaction_policy.py` and run-parameter frozensets from `simulations.py` at runtime; no duplicate string lists. `generate-from-brief` runs through `validate_scenario_document` (single validation path); 422 returns `errors` + `warnings` + `raw_llm_text` for agent retry. `/analyze` has solid context control: two-layer clipping (head+tail turns + per-turn response truncation → 180k hard budget), strips `raw_prompt`, traces clipping in `_bundle_notes`. Genuinely stateless (no DB writes). Frontend "Generate from brief" correctly hydrates the wizard form and sets create mode. Router registration correct. 5 new tests covering capabilities shape, generate success/failure, analyze 409/200.

**Non-blocking improvements noted (most addressed post-gate — see bullets below):**

1. ~~`{{` / `.format()` on scenario template~~ — **done:** comment on `_GENERATE_SYSTEM_TEMPLATE` in `scenarios_generate.py`.
2. ~~`/analyze` stage-1 vs stage-2 caps~~ — **done:** named constants together in `api/simulations.py`.
3. ~~Second-stage shrink test gap~~ — **done:** `tests/test_iteration16.py` covers both reclipping paths.
4. ~~`bundled_rag_paths` environment note~~ — **done:** `GET /capabilities` docstring.
5. **`hybrid` → LM Studio** for authoring utilities — **documented** in endpoint docstrings (optional future: use Anthropic when hybrid).
6. ~~Closeout / `SESSION_STATE` ordering~~ — **tidied** in follow-up pass.

**Gate confirmed:** An external AI agent (or researcher) can now generate a scenario from a brief, run a simulation, and get a structured analysis report using only API calls. Foundation for Iteration 17 orchestration layer is solid.

---

## Iteration 17 starter (pre-filled — 2026-04-05)

### Scope

- **Iteration / slice:** **Iteration 17** — **Agent orchestration layer**: three new endpoints (`POST /agent/plan`, `POST /agent/execute`, `POST /agent/ask`) with SSE streaming support.
- **In scope:**
  - `POST /agent/plan` — natural language research question + optional constraints → structured run plan (scenarios to create, parameter variants, comparisons).
  - `POST /agent/execute` — takes a run plan, executes runs sequentially, calls `/analyze` on each, returns combined report.
  - `POST /agent/ask` — stateless single-call: brief in → final report out (internally plan → execute → analyze).
  - SSE streaming for progress updates so a frontend can show status without polling.
  - The orchestration layer is a **thin wrapper** over Iterations 14–16 endpoints — it does NOT contain simulation logic.
- **Out of scope / defer:** Minister UI (Iteration 18); parallel LLM (Iteration 19); population scale (Iteration 20).

### Definition of done

- [x] All three `/agent/*` endpoints implemented and tested.
- [x] SSE streaming works for `/agent/ask` (at minimum).
- [x] Orchestrator uses the **same in-process handlers** as HTTP: `generate_scenario_from_brief`, `queue_simulation_run` (same body as `POST /simulations/run`), `wait_for_simulation_terminal`, `analyze_simulation_export` — **no duplicate simulation logic**, no HTTP self-calls.
- [x] **`build_capabilities_dict()`** (same payload as `GET /capabilities`) embedded in planner prompts — not hard-coded parameter lists.
- [x] A test script can send one English sentence to `/agent/ask` and receive a complete simulation report.
- [x] `pytest` passes; `npm run build` passes.
- [x] `iteration-17-closeout.md` written; `SESSION_STATE.md` updated.

### Key files (hints)

New: `backend/src/mirofish_backend/agent/orchestrator.py`, `backend/src/mirofish_backend/api/agent.py`. Existing: `llm/router.py`, `api/simulations.py`, `api/scenarios_generate.py`, `api/capabilities.py`, `main.py` (router registration).

### Decisions already made *(design intent)*

- Orchestrator is a **thin wrapper** — no simulation engine logic; reuses the same Python entrypoints the routers call.
- **Capabilities JSON** at plan time — authoritative vocabulary for the planner (via `build_capabilities_dict()`).
- **`/analyze` is stateless** at the API — orchestration returns analysis in the **`/agent/execute`** / **`/agent/ask`** JSON payload (not persisted by the agent layer).

### As implemented (builder record)

- **In-process calls:** `queue_simulation_run` + `wait_for_simulation_terminal` + `generate_scenario_from_brief` + `analyze_simulation_export` (same functions the HTTP routes use; **no HTTP self-calls**).
- **Capabilities in prompts:** `build_capabilities_dict()` (shared with `GET /capabilities`).
- **SSE:** `POST /agent/ask?stream=true` uses an async queue + background task; automated `TestClient.stream` coverage was flaky — manual `curl` documented in `iteration-17-closeout.md`.

### Risks / watch

- Planner LLM may emit invalid JSON or out-of-vocabulary fields — **`validate_plan_against_capabilities`** rejects before execute (422).
- Long **`/agent/ask`** runs — **`wait_timeout_seconds`** is per simulation wait loop; multi-run JSON calls can sum to a long wall-clock; SSE helps UX.
- Per-step **`HTTPException`** from **`generate_scenario_from_brief`** / **`queue_simulation_run`** is caught in **`execute_plan`** (**`generate_failed`** / **`queue_failed`**) so multi-run plans continue.

---

### Iteration 17 — PASS (architect review 2026-04-05)

**Theme:** Agent orchestration — `POST /agent/plan`, `POST /agent/execute`, `POST /agent/ask` (+ SSE), thin layer over generate / queue run / wait / analyze.

**What's good:** Thin-wrapper design is correct — orchestrator calls `queue_simulation_run`, `generate_scenario_from_brief`, `analyze_simulation_export` (the same functions the HTTP routes use). Zero simulation logic duplicated. `queue_simulation_run` refactor is clean: `POST /simulations/run` now delegates in one line. `wait_for_simulation_terminal` uses lightweight `get_simulation_run_status_only` (5 columns, no transcript). Planner prompt embeds `build_capabilities_dict()` JSON at runtime — no hard-coded strings; future parameters are automatically available. `validate_plan_against_capabilities` is a proper guard that validates every field in every run step. SSE via `asyncio.Queue` + background task cleanly separates work from event generation. `PlanRunStep` validator enforces exactly-one-of `scenario_id`/`scenario_brief`. Demo script is zero-dependency (`urllib` only). 5 new tests; full suite **108 passed**.

**Non-blocking improvements noted:**

1. SSE path not exercised in CI — `TestClient.stream` is flaky with async generators. **`pytest.mark.manual`** placeholder + `curl` checklist in `iteration-17-closeout.md`. Not blocking.
2. **Addressed in repo:** `generate_scenario_from_brief` / queue **`HTTPException`** caught per step → **`analysis_error`**, **`generate_failed`** / **`queue_failed`**, continue to next run.
3. **Addressed in repo:** optional **`plan_temperature`** on **`AgentPlanRequest`** / **`AgentAskRequest`** (default **0.35**).
4. **Documented:** `wait_timeout_seconds` applies **per run**; an 8-run JSON `/agent/ask` can block for a long wall-clock. SSE path helps UX.
5. Multi-run plans are strictly sequential — parallel runs remain a product decision (Iteration 19+).
6. `HANDOFF_TO_ARCHITECT.md` was stale at Iteration 14 — refreshed in same pass.

**Gate confirmed:** One English sentence → `POST /agent/ask` can plan, run, and return structured per-run analysis (with live LLM + backend). Foundation for **Minister UI (Iteration 18)** is in place.

---

## Iteration 18 starter (pre-filled — 2026-04-05)

### Scope

- **Iteration / slice:** **Iteration 18** — **Minister UI** (researcher-facing console for agent orchestration): surface **`/agent/plan`**, **`/agent/execute`**, **`/agent/ask`** (and optional SSE log pane) without requiring `curl` or raw JSON.
- **In scope (typical):** New or extended React panel; calls same-origin **`/agent/*`** (Vite proxy already includes **`/agent`**); loading / error states; display of **`plan`** + **`runs[].analysis`** (and failures).
- **Out of scope / defer:** Parallel LLM (Iteration 19); population scale (Iteration 20); backend orchestration logic changes unless blocking the UI.

### Definition of done

- [x] Minister (or **Agent**) UI ships in `frontend/` with at least **ask** and **plan+execute** flows **or** a single **ask** flow with expandable plan. *(Shipped: **ask-first** + **Advanced** plan/execute.)*
- [x] `npm run build` passes; `pytest` unchanged or extended only if API contract fixes are required.
- [x] `iteration-18-closeout.md`; `SESSION_STATE.md` updated.
- [x] `HANDOFF_TO_ARCHITECT.md` refreshed for the next gate.

### As implemented (builder record — 2026-04-02)

- **`frontend/src/components/AgentConsole.tsx`** — primary **Ask**; **Show execution plan (JSON)** after success; **Advanced** → constraints, timeout/temperature/tokens, **Plan only**, **Execute** JSON; **Cancel** + elapsed timer; placeholder question; client-side tuning validation.
- **`frontend/src/components/RunResultCard.tsx`** — shared per-run cards for Ask + Execute responses.
- **`frontend/src/lib/api.ts`** — **`agentAsk`**, **`agentPlan`**, **`agentExecute`** (optional **`AbortSignal`**).
- **`frontend/src/App.tsx`** — tab **Agent**.

### Key files (hints)

`frontend/src/` (new component + tab or route), `frontend/vite.config.ts` (proxy already has `/agent`), `docs/iterations/iteration-17-closeout.md` for API shapes.

### Decisions already made

- Backend agent layer is **Iteration 17** — UI is presentation + wiring only.
- SSE is optional for MVP UI — polling **`/agent/ask`** JSON mode is acceptable for a first slice.

### Risks / watch

- Long **`/agent/ask`** wall-clock — show spinner + cancel story (browser cancel only unless backend adds abort).
- Never send secrets from the browser; server **`Settings`** hold LLM keys.

---

### Iteration 18 — PASS (architect review 2026-04-05)

**Theme:** Minister / Agent UI — `AgentConsole` wrapping `/agent/ask`, `/agent/plan`, `/agent/execute` behind an ask-first interface.

**What's good:** Ask-first design is correct for the Minister persona — one textarea, one button, plain language in, structured results out. Advanced section collapsed by default keeps the primary flow clean. API client layer (`agentPlan`, `agentExecute`, `agentAsk` in `api.ts`) is well-typed — `AgentPlanRunStep`, `ExecutionPlan`, `AgentRunReport`, `AgentAskResponse` mirror backend models accurately. Results rendering is nicely structured — per-run cards with label/status/sim ID/key findings/narrative/follow-ups; `analysis_error` displayed inline. Plan introspection ("Show execution plan JSON") after a successful Ask lets the researcher audit the plan and pre-loads the Execute editor for manual tweaking. Input validation (8-char minimum) matches the API contract with inline feedback. No backend changes — purely presentation + wiring. Frontend builds clean; backend suite unchanged (110 passed, 1 skipped). Documentation fully updated across all three handoff docs.

**Non-blocking improvements noted:**

1. ~~**Execute results render as raw JSON**~~ — **Addressed:** shared **`RunResultCard`** for Ask and Execute result lists (`frontend/src/components/RunResultCard.tsx`).
2. ~~**No cancel / abort**~~ — **Addressed:** **`AbortController`** on **`agentAsk` / `agentPlan` / `agentExecute`** + **Cancel request** button.
3. ~~**Default value vs placeholder**~~ — **Addressed:** question field starts empty with **`placeholder`** (PSLE example as hint text).
4. ~~**No elapsed-time indicator**~~ — **Addressed:** **Elapsed: Ns** while any agent request is in flight.
5. ~~**Client-side range validation on Advanced fields**~~ — **Addressed:** **`type="number"`** with **`min`/`max`**, inline warnings, and disabled Ask/Plan/Execute when values are out of API range.
6. **SSE explicitly deferred** — correct for MVP. JSON path works. First UX upgrade candidate in a future polish slice.

**Gate confirmed:** A non-technical user can type a research question, click Ask, and receive a structured analysis report — the complete "Minister flow" from the roadmap. Foundation for Iteration 19 (parallel LLM / scale) is unchanged.

---

## Iteration 19 starter (pre-filled — 2026-04-05)

### Scope

- **Iteration / slice:** **Iteration 19** — **Parallel LLM execution** within rounds, concurrency controls, updated stress tests.
- **In scope (typical):**
  - Replace sequential per-turn LLM calls within a round with `asyncio.gather` (or similar) for independent turns within the same round.
  - Concurrency cap (configurable, default ~4) to avoid overwhelming LM Studio / Anthropic.
  - Stress test updates for parallel paths (verify determinism with `random_seed`, state correctness, error handling per-turn).
  - `config_snapshot` records concurrency settings.
- **Out of scope / defer:** Population >50 / aggregation mode (Iteration 20); UI changes unless required by new API fields.

### Definition of done

- [ ] Parallel LLM within rounds implemented with configurable concurrency cap.
- [ ] Stress tests pass with parallel execution; determinism verified via `random_seed`.
- [ ] `pytest` passes; `npm run build` passes (if UI touched).
- [ ] `iteration-19-closeout.md` written; `SESSION_STATE.md` updated.
- [ ] `HANDOFF_TO_ARCHITECT.md` refreshed.

### Key files (hints)

`backend/src/mirofish_backend/simulation/orchestrator.py` (turn execution loop), `api/simulations.py` (new config fields), `db/repo.py` (concurrent writes), tests.

### Decisions already made

- Turns within a round are currently sequential; rounds remain sequential (round N depends on round N-1 state).
- `interaction_last_k` and `visible_turns_for_agent` filter only previously-completed turns — parallel turns in the same round see only prior-round context (correct by design).

### Risks / watch

- **Turn ordering within a round**: parallel execution means `turn_index` assignment must happen before dispatch, not during. Verify `_build_interaction_plan` assigns indices up front.
- **DB write contention**: `aiosqlite` serializes writes — parallel turns completing simultaneously will queue. Acceptable at current scale; note for future.
- **Error isolation**: one turn failure should not abort the entire round — catch per-turn and mark failed turns.

---

### Iteration 19 — PASS (architect review 2026-04-06)

**Theme:** Parallel LLM within rounds — `asyncio.gather` + `asyncio.Semaphore`, concurrency cap, determinism, error isolation.

**What's good:** Core design is correct — `asyncio.gather` + `Semaphore(llm_concurrency_cap)` within rounds; rounds remain sequential (round N depends on round N-1 state). The critical correctness detail — pre-assigning `turn_assignments = list(enumerate(round_agents, start=1))` before dispatch — ensures interaction plans, `interaction_last_k`, and `_build_interaction_plan` are all deterministic regardless of execution order. `_run_one_turn` closure safety is well-documented. Error isolation is two-layered: inner try/except records `[LLM error]` response strings, outer `return_exceptions=True` catches anything that escapes. `cap=1` cleanly reproduces pre-Iteration-19 sequential behaviour. The determinism test (cap=1 vs cap=4, same seed → identical turn order) is the most important test in the suite and it passes. Config follows the established pattern (env var, optional API field with `ge=1, le=16`, `config_snapshot`). 7 well-targeted tests; full suite 117 passed, 1 skipped. Joan also addressed all 6 non-blocking items from the Iteration 18 review (`RunResultCard` extraction, `AbortController` + Cancel, `placeholder` text, elapsed-time counter, `min`/`max` on Advanced inputs, `AbortSignal` on API functions) — nice work.

**Non-blocking improvements noted:**

1. **`GET /capabilities` does not expose `llm_concurrency_cap`** — `build_capabilities_dict()` is the single source of truth for the planner LLM's vocabulary, but it currently has no entry for `llm_concurrency_cap` (range 1–16, default 4). The planner can't include concurrency tuning in generated plans. Add it under `simulation_run` in `build_capabilities_dict()`.
2. **Agent orchestrator doesn't forward `llm_concurrency_cap`** — `PlanSimulationParams` has no `llm_concurrency_cap` field and `_simulation_run_request` doesn't set it. Runs via `/agent/ask` always use the server default. Add the field to `PlanSimulationParams` (optional, same `ge=1, le=16`) and pass it through in `_simulation_run_request`. Non-urgent: server default is sensible.
3. **No per-round timing metric** — individual turn `latency_ms` is tracked, but there's no round-level wall-clock log line. With parallelism, round wall-clock should be ~max(turn latencies) instead of sum — logging this would help validate parallelism is working in production. A single `logger.info("round_complete ... wall_ms=%d", ...)` after `asyncio.gather` returns.
4. **Catastrophic `return_exceptions=True` errors lose the turn** — if an exception escapes the inner try/except (e.g., `insert_agent_turn` DB write failure), the turn is logged but no row is written. The transcript will have fewer rows than expected. Document that `len(transcript) <= agents × rounds` (not `==`) when DB-level errors occur.
5. **`aiosqlite` write batching at scale** — correctly noted in closeout as acceptable at ≤50 agents. For Iteration 20+ population scale, consider collecting turn rows for a round and using `executemany` after gather instead of N individual writes.

**Gate confirmed:** Within-round parallelism is live with correct determinism, error isolation, and configurable concurrency. Foundation for Iteration 20 (population scale / aggregation) is solid.

---

## Iteration 20 starter (pre-filled — 2026-04-06)

### Scope

- **Iteration / slice:** **Iteration 20** — **Population >50 with aggregation mode**, cohort-level exports, thesis-grade 500-agent notes.
- **In scope (typical):**
  - Lift `agent_limit` ceiling above 50 (soft limit with warning retained; hard max TBD by architect — 100–200 range).
  - **Aggregation mode** — when population exceeds a threshold, aggregate outcomes at group/cohort level rather than rendering full per-agent transcripts (which become unwieldy and expensive at 100+ agents).
  - Cohort-level export additions in `export.json` and/or ZIP (e.g., per-group averages for support/resistance/workload, group-level narrative summaries).
  - `config_snapshot` records aggregation settings.
  - Thesis notes on 500-agent feasibility (cost, token budget, wall-clock, DB write patterns, recommended `llm_concurrency_cap` at scale).
- **Out of scope / defer:** Full 500-agent live runs (cost-prohibitive without batching/caching); network-edges import; SSE in browser; scenario marketplace.

### Definition of done

- [ ] `agent_limit` ceiling raised; aggregation mode implemented for large-population runs.
- [ ] Cohort-level summary in export bundle when aggregation mode is active.
- [ ] Thesis feasibility note written (cost/scale/recommendations).
- [ ] `pytest` passes; `npm run build` passes (if UI touched).
- [ ] `iteration-20-closeout.md` written; `SESSION_STATE.md` updated.
- [ ] `HANDOFF_TO_ARCHITECT.md` refreshed.

### Key files (hints)

`backend/src/mirofish_backend/simulation/orchestrator.py`, `api/simulations.py`, `export_bundle.py`, `population/csv_population.py`, `frontend` Live/State tabs if aggregation changes display, tests.

### Decisions already made

- Parallel LLM within rounds (Iteration 19) makes large-N runs feasible at `cap=4–16`. Rounds remain sequential.
- Population sampling (`weighted`/`stratified`) already supports large pool CSVs — the bottleneck is LLM calls per round, not the draw.
- `aiosqlite` serializes writes — acceptable at current scale but noted for batch optimization.

### Risks / watch

- **Cost at 100+ agents**: even with parallelism, 100 agents × 4 rounds = 400 LLM calls. Use `sample_k_per_round` mode aggressively. Document recommended configurations.
- **Context length**: 100+ agents produce long transcripts in `interaction_last_k` — verify `peer_context_max_chars` clipping is effective. May need to reduce `interaction_last_k` at scale.
- **Aggregation vs full transcript**: decide whether aggregation mode replaces per-agent turns or runs alongside. Recommended: aggregation is a **post-processing view** (full transcript is always written; aggregation is computed at export/display time).

---

### Iteration 20 — PASS (architect review 2026-04-06)

**Theme:** Population scale — `agent_limit` raised to 200, cohort aggregation in export bundle (`export_version` 5), `aggregation_threshold` convenience flag, thesis-grade 500-agent feasibility note.

**What's good:** `compute_cohort_summary` is a clean pure function — no DB query, operates on the already-fetched snapshots list. Correct design: full transcript is always written, cohort aggregation is post-processing at export time. Multi-group agents contributing to both cohort buckets is the right call — mirrors how group membership works in the visibility policy. `aggregation_mode` as a convenience flag in `config_snapshot` (not a behavior switch) is the right abstraction. `export_version` 5 is additive — `cohort_summary` is new data, old fields unchanged. `agent_limit` and `speakers_per_round` both raised to 200 consistently. Agent orchestrator (`PlanSimulationParams`, planner prompt) correctly updated with `aggregation_threshold`. Capabilities endpoint includes new ranges. The feasibility note is thorough and thesis-grade — wall-clock projections at four scale tiers, Anthropic cost analysis (hybrid vs full-cloud), DB write patterns, recommended configs per tier, hard limits table. 8 well-targeted tests covering the pure function, export shape, ZIP, API limits, config_snapshot, and capabilities. Full suite 125 passed, 1 skipped. Joan also addressed prior non-blocking items from Iterations 18 and 19 reviews (capabilities `llm_concurrency_cap`, `PlanSimulationParams` forwarding).

**Improvements (1 fix recommended, rest non-blocking):**

1. **`export_version` stale in `capabilities.py`** (fix): `build_capabilities_dict()` line 37 still returns `"export_version": "4"` but the actual export is now version `"5"`. The planner LLM reads this value — it will generate plans referencing the wrong export version. **Change to `"5"`.**
2. **No test for multi-group agents in cohort summary**: design note correctly says multi-group agents contribute to both buckets, but no test verifies this. Add a test with an agent in `["leadership", "teachers"]` and confirm it appears in both group aggregations.
3. **`import json` inside function body**: `compute_cohort_summary` has `import json as _json` inside the loop guard (line 36-37 of `export_bundle.py`). Move it to the top of the function or use the module-level `import json` that already exists on line 14. Micro-optimization but also cleaner.
4. **Feasibility note editorial**: Section 4 line 73 starts with a wrong formula (`anthropic_turns = agent_count × 1 = agent_count per round`) then self-corrects. Clean up to just show the correct formula (1 Anthropic call per round under hybrid routing).
5. **`cohort_summary` not in poll API**: `GET /simulations/{id}` returns transcript, state_timeline, etc. but not `cohort_summary`. It's only in the export JSON. Fine for now (cohort is a post-processing view), but worth noting for future frontend integration if the Live tab wants to show cohort trends.

**Gate confirmed:** Population scale infrastructure is solid. `agent_limit` 200 with parallel LLM (cap 8-16) and cohort aggregation makes thesis-scale runs feasible. Foundation for Iteration 21 (generic engine cleanup) is ready.

---

### Iteration 21 — PASS (architect review 2026-04-06)

**Theme:** Generic engine cleanup — remove school-specific hardcoding from core paths; drive initial agent state from persona YAML; domain-agnostic demographics and scenario generation prompts; `domain-packs.md` documentation.

**What's good:** The core goal is cleanly achieved — `_initial_state_for_role()` is gone and replaced with `_initial_state_from_persona()` that reads directly from persona YAML. Neutral defaults (0.50/0.35/0.45/neutral) when the block is absent are sensible. Both PSLE and FSBB YAMLs migrated with `initial_state` blocks that exactly match the former hardcoded values, and the embedded fallback scenarios carry `initial_state` too — no regression path exists. `_build_demographics()` is now role-name-free: age scales from `role_level` + `idx`, sex cycles, ethnicity/ses default to `"unspecified"`. `_merge_demographics` takes `role_level` instead of `role`. The generate-from-brief prompt in `scenarios_generate.py` is properly domain-agnostic — "any organisational role relevant to the scenario domain", "1 = highest authority", "matching the brief's domain". Validation in `validate.py` correctly accepts any positive-integer `role_level`. `merge_persona_for_slot` copies `initial_state` from base persona (line 177). `domain-packs.md` is concise and well-written — exactly what Opus requested for grant reviewers. Pre-gate `export_version` fix confirmed ("5"). 6 well-targeted regression tests: PSLE and FSBB initial-state match, neutral default, demographics formula, validation positive/negative. Full suite 131 passed, 1 skipped. Clean iteration — nothing extraneous.

**Improvements (2 recommended fixes, 1 non-blocking):**

1. **Age formula goes negative for high `role_level`** (fix before Iter 22): `_build_demographics` uses `age = 49 - (role_level-1)*8 + idx%3`. For `role_level=7, idx=0` → age = 1. For `role_level=8` → age = -7. The generic engine now accepts any positive integer `role_level`, so a non-school scenario with 8+ hierarchy levels will generate negative ages. **Fix:** clamp to a sensible floor, e.g. `age = max(22, 49 - (min(role_level, 6) - 1) * 8 + idx % 3)`. This caps the age spacing at 6 levels and floors at 22.
2. **`initial_state` values not validated for numeric range** (fix): `_initial_state_from_persona` calls `float(raw.get("support_level", ...))` with no range check. A YAML author who writes `support_level: 1.5` or `support_level: "high"` gets either an out-of-range value silently propagated or a runtime `ValueError` crash during simulation. **Fix:** add validation in `validate.py` — when `initial_state` is present, warn if `support_level`, `resistance_level`, or `workload_stress` are present and not in `[0.0, 1.0]`. No code change needed in the orchestrator — the validator catches it at scenario creation time.
3. **Module docstring in `interaction_policy.py` still uses school-specific example** (non-blocking): Line 15–16 says `"hierarchical (principal → HoDs → teachers, matching Trinidad's authority structure)"`. This is the module-level docstring, visible to anyone reading the file. The `HIERARCHICAL` enum docstring may have been updated, but the module overview still uses school terminology. **Suggested:** change to `"hierarchical (highest role_level first → lowest, matching authority structure)"` and keep the school example in a parenthetical if desired.

**Not issues (reviewed and confirmed correct):**
- Population CSV path does not carry `initial_state` — correct, `initial_state` describes simulation starting conditions, not demographics.
- Roster `merge_persona_for_slot` always copies from base (no roster CSV column for `initial_state`) — correct for current scope; Iteration 22's `fidelity_tier` column is the next roster extension, not `initial_state`.
- `_SCENARIOS_FALLBACK` comment ("School-specific demo scenario. Engine is domain-agnostic") is clear and appropriate.

**Gate confirmed:** Generic engine foundation is solid. All school-specific hardcoding removed from core paths. Domain-agnostic scenario generation, validation, and documentation in place. Ready for Iteration 22 (sampling strategy contract).

---

### Iteration 22 — PASS (architect review 2026-04-06)

**Theme:** Sampling strategy contract (metadata only) — `sampling_strategy` (`full_census` | `role_stratified`), roster `fidelity_tier` override, `AgentInstance.fidelity_tier`, `config_snapshot.sampling_audit`, capabilities + agent planner wiring. No LLM execution change (all agents full LLM until Iteration 23).

**Pre-Iteration 22 fixes confirmed:** All three fixes from the Iteration 21 review were applied — age floor clamp in `_build_demographics` (line 198), `initial_state` numeric validation in `validate.py`, and generalized `interaction_policy.py` module docstring. Test count rose from 131 → 134 before Iteration 22 work began.

**What's good:** `sampling_strategy.py` is a clean, focused module — pure functions, no side effects, no import of heavy dependencies. `compute_fidelity_tiers` correctly implements the resolution hierarchy (roster > strategy > default) with clear separation of concerns. `_role_stratified_for_indices` dynamically collects roles from the scenario YAML (not hardcoded — per Opus's non-negotiable requirement) and only assigns Tier 1 representatives among non-roster-overridden slots. The remainder split (higher `role_level` → Tier 3, lower → Tier 2) matches the spec and is research-sensible: low-authority agents are more numerous and less individually influential, so they get cheaper fidelity. `build_sampling_audit_extended` adds `scenario_roles_not_represented` — important for runs where `agent_limit` < number of distinct roles, so the researcher knows which voices are missing. Roster CSV parsing validates `fidelity_tier` strictly (1/2/3 only) with a clear error. API validation uses Pydantic `field_validator` with normalization. `config_snapshot` includes both `sampling_strategy` and the full `sampling_audit` — full reproducibility. Agent orchestrator (`PlanSimulationParams`, validation, `_simulation_run_request`) correctly wires `sampling_strategy` end-to-end. Capabilities endpoint includes `sampling_strategies` and `fidelity_tiers`. **12** tests in `test_iteration22.py` (including pre–Iter 23 degenerate-role + `scenario_roles_not_represented` coverage). Full suite **146** passed, 1 skipped.

**Follow-ups from review:**

1. **All-agents-same-role test** — **done** (pre–Iter 23): `test_role_stratified_all_same_role` in `tests/test_iteration22.py`.
2. **`scenario_roles_not_represented` test** — **done** (pre–Iter 23): `test_sampling_audit_reports_missing_roles` in `tests/test_iteration22.py`.
3. **`build_sampling_audit` vs `build_sampling_audit_extended`** (non-blocking): Could merge into one function with optional `personas_for_run`. Not urgent — current design is clear enough.

**Not issues (reviewed and confirmed correct):**
- `tier_counts` uses string keys after JSON/SQLite round-trip — correctly documented in closeout; tests normalize with `int(k)`. This is a SQLite JSON serialization artefact, not a code bug.
- `roles_in_run` in `_role_stratified_for_indices` iterates all personas (including roster-overridden ones) — this is correct because it determines which scenario roles exist in the run, not which are available for strategy assignment.
- Roster override of a Tier 1 representative role (e.g., forcing principal to Tier 3) correctly means no strategy-assigned Tier 1 for that role among the remaining slots — the researcher is explicitly controlling this.
- `full_census` assigns all agents Tier 1 — identical to pre-Iteration 22 behavior. Zero regressions.

**Gate confirmed:** Sampling contract is solid metadata-only infrastructure. Resolution hierarchy is clean, audit trail is complete, agent planner is wired. Foundation for Iteration 23 (tier-aware orchestrator) is ready.

---

### Iteration 23 — PASS (architect review — final 2026-04-06)

**Theme:** Tier-aware orchestrator — Tier 1 full LLM (unchanged), Tier 2 `simplified_persona_prompt` + halved peer context, Tier 3 no LLM (heuristic marker, state unchanged placeholder until Iteration 24). `fidelity_tier` on `agent_turns`. `export_version` 6.

**Pre-Iteration 23 fixes confirmed:** Both test gaps from the Iteration 22 review were filled — same-role degenerate case and `scenario_roles_not_represented` tests. Test count rose from 144 → 146 before Iteration 23 work began.

**What's good:** `simplified_persona_prompt()` matches Opus's spec — role, style cues, beliefs/policy position, current belief state; omits psych profile, biographical blocks (identity, attitudes, history, implementation), and groups. Round context still comes through `build_user_prompt` (policy event + peers). Tier 2 halves `peer_context_max_chars` for memory and recent interactions. Tier 3: no LLM, marker row, `heuristic` / `none`, `latency_ms` 0, state unchanged. `fidelity_tier` on `agent_turns` with default 1; poll + export bundle + empty-ZIP transcript headers. Frontend transcript line shows fidelity tier. Three tests in `test_iteration23.py` cover prompt shape, mixed tiers under `asyncio.gather`, and Tier-3-only state stability. Suite **149 passed, 1 skipped** (per closeout).

**Post–architect follow-up (shipped with Iteration 23 gate — see `iteration-23-closeout.md`):**

1. **`EXPORT_VERSION` centralized** — `EXPORT_VERSION = "6"` in `export_bundle.py`; `api/simulations.py` and `api/capabilities.py` import it; `test_iteration16.py` / `test_iteration20.py` assert against `EXPORT_VERSION` (no duplicate literals).
2. **Mixed-tier test assertion hardened** — `test_mixed_tiers_llm_only_for_one_and_two` now asserts **`Persona identity and stance:`** on Tier 1 system prompt instead of **`Psychological profile`**, because the latter is **omitted when the persona has an empty psych block** (e.g. PSLE HoD). Tier 1 is still the full template; the test now keys off a section that is always present for real bundled personas.

**Optional improvements — applied** (see [`iteration-23-closeout.md`](../iterations/iteration-23-closeout.md) § *Optional backlog from HANDOFF*):

1. ~~**Simplify tier read in orchestrator**~~ — Uses `tier_raw = agent.fidelity_tier or 1` + int clamp (no redundant `getattr`).
2. ~~**Named Tier-1 regression test**~~ — `test_tier_one_uses_full_system_prompt` in `test_iteration23.py`.
3. ~~**Build artefact hygiene**~~ — `build/` in `backend/.gitignore`; mixed-tier test asserts on prompt **content**, not `llm_calls` order (parallel `gather`).

**Not issues (confirmed):**
- Tier 2 shares Tier 1 user prompt — correct (round + policy context).
- Tier 2 omits demographics in system prompt — correct per Opus.
- Parallel mixed-tier round — covered by integration test.

**Gate confirmed:** Iteration 23 is **Architect PASS** and follow-ups are merged. Tier 3 remains a placeholder until Iteration 24's heuristic. Proceed per roadmap (Iteration 24+).

---

### Iteration 26 — PASS_WITH_ISSUES (architect review — 2026-04-07)

**Theme:** `implementation_posture`, `posture_maxvar`, extended `sampling_audit` (`role` + posture on `per_agent`), `GET /simulations/{id}/sampling-report`.

**Full write-up:** [`docs/reviews/review-iteration-26.md`](../reviews/review-iteration-26.md).

**What's good:** Opaque posture labels are domain-agnostic; tier assignment and fallback when no tags match the HANDOFF spec; sampling report is pure reshape of persisted audit; HTTP codes 404 / 409 / 400 are correct; suite **163 passed, 1 skipped** at review time.

**Follow-ups for builder** — **done** via [Post-Iteration 26 hardening](#post-iteration-26-hardening-pre-filled--2026-04-07) (2026-04-07):

1. ~~Reconcile **`docs/SESSION_STATE.md`**~~ — Gate Evidence **164** tests; **§ Iteration 26 (Completed)**; **Next Iteration** → **25** only.
2. ~~Optional **integration test**~~ — `test_posture_maxvar_queued_run_audit_and_sampling_report`.
3. ~~Optional **frontend**~~ — Run tab + Run metadata link **Sampling report (JSON)** (completed/failed).
4. ~~**Minor:** roster CSV template comment~~ — empty `implementation_posture` preserves YAML posture.

**Gate:** Ship is **accepted**; hardening complete before Iteration 25.

---

### Iteration 25 — PASS_WITH_ISSUES (architect review — 2026-04-07)

**Theme:** Network CSV, degree centrality, `network_centrality` strategy, `round_participants_only` + `network_bounded` visibility (ADR-002), `config_snapshot` network provenance, sampling report `centrality` map.

**Full write-up:** [`docs/reviews/review-iteration-25.md`](../reviews/review-iteration-25.md).

**What's good:** `simulation/network.py` is clean (parse, validate, centrality, neighbor map). `visible_turns_for_agent` expanded with optional kwargs — existing callers unchanged. ADR-002 fallback (`network_bounded` without CSV → `broadcast` + warning) implemented correctly. Pydantic guard blocks `network_centrality` without `network_csv`. `config_snapshot` records full network provenance (`network_csv_applied`, edge/node count, per-agent `degree_centrality`, `visibility_effective`, `network_visibility_fallback`). Sampling report populates `centrality` map from audit. Agent planner validates visibility against capabilities. Suite **172 passed, 1 skipped** at review time.

**Follow-ups for builder** — **done** via [Post-Iteration 25 hardening](#post-iteration-25-hardening-pre-filled--2026-04-07) (2026-04-07):

1. ~~**Integration test**~~ — `test_network_queued_run_audit_sampling_report_and_node_count` in `test_iteration25.py`.
2. ~~**`network_node_count`**~~ — count of distinct endpoints in parsed edges (not roster size).
3. ~~**Capabilities / `full`**~~ — `GET /capabilities` omits legacy `full`; agent plan validation normalizes `full` → `broadcast`.
4. ~~**`round_participants_only` + broadcast**~~ — broadcast turns pass through; test + docstring in `interaction_policy.py`.
5. ~~**`SESSION_STATE.md`**~~ — Iteration 25 + post-hardening noted; gate **174** tests.
6. ~~**Minor**~~ — test rename, `parse_network_csv` duplicate-edge docstring, `network_csv` Field + capabilities description.

**Gate:** Ship is **accepted**; post-25 hardening complete before Iteration 27.

---

### Iteration 27 — PASS_WITH_ISSUES (architect review — 2026-04-07)

**Theme:** Multi-run experiments — `experiments` / `experiment_runs` tables, `POST /experiments` (sequential child runs), comparison table + exports, `ExperimentConsole` UI tab.

**Full write-up:** [`docs/reviews/review-iteration-27.md`](../reviews/review-iteration-27.md).

**What's good:** Clean separation — experiments are a persistence + comparison layer over `queue_simulation_run`; zero simulation logic duplicated. `_merge_to_simulation_request` elegantly merges base + per-step overrides. Comparison table (round × series) reshapes existing `global_state_snapshots` + `round_outcomes`. Export ZIP is well-structured (`comparison.csv` + per-run bundles). `experiment_id` backward-compatible (nullable). E2E test covers full lifecycle. Suite **180 passed, 1 skipped** (after post-27 hardening).

**Follow-ups for builder** — **done** (2026-04-07); see [Post-Iteration 27 hardening](#post-iteration-27-hardening-pre-filled--2026-04-07) and [`iteration-27-closeout.md`](../iterations/iteration-27-closeout.md) § Post–Iteration 27 hardening.

1. ~~**`POST /experiments` blocks HTTP connection**~~ — documented in `api/experiments.py` module docstring; background task + polling remains backlog.
2. ~~**Experiment failure path**~~ — tested; handler sets **`failed`** + **`completed_at`**, returns **HTTP 500** via **`HTTPException`**.
3. ~~**`_series_key` duplication**~~ — **`_deduplicate_key`** shared helper.
4. ~~**Frontend cancel**~~ — **`AbortController`**, Cancel, elapsed seconds on create.
5. ~~**Minor**~~ — **`set_experiment_status`** branch collapsed; **`run_count`** on list + UI; sparkline metric select + details table for all five metrics. **`DELETE /experiments`** still backlog.

**Gate:** Ship **accepted**; post-27 hardening **complete**.

---

### Iteration 28 — PASS_WITH_ISSUES (architect review — 2026-04-07) — hardening complete 2026-04-08

**Theme:** Convergence stopping criterion — `convergence_threshold` / `convergence_patience`, per-round `convergence_delta`, `converged_at_round`, `export_version` 7, Live dashboard sparkline + banner.

**Full write-up:** [`docs/reviews/review-iteration-28.md`](../reviews/review-iteration-28.md).

**What's good:** `_population_convergence_delta` is a clean pure function. Round 1 skip is correct (no prior snapshot). Fully opt-in — omitting threshold preserves existing behaviour exactly. `merge_simulation_config_snapshot` updates only the convergence field in persisted JSON. Frontend clean: optional Run form inputs, sparkline, green banner with threshold/patience values. Known Tier-3 dampening limitation documented for thesis interpretation. Suite **186 passed, 1 skipped** (after post-28 hardening).

**Follow-ups for builder** — **done** (2026-04-08); see [Post-Iteration 28 hardening](#post-iteration-28-hardening-pre-filled--2026-04-07) and [`iteration-28-closeout.md`](../iterations/iteration-28-closeout.md) § Post–Iteration 28 hardening.

1. ~~**Experiments**~~ — `ExperimentCreateRequest` + merge + E2E test.
2. ~~**Agent orchestrator**~~ — `PlanSimulationParams`, validation, planner template, `_simulation_run_request`.
3. ~~**Streak-reset test**~~ — varying fake LLM; patience after high-delta rounds.
4. ~~**Minor**~~ — `convergence_delta` in comparison + CSV; `converged_at_round` in experiment UI; defensive skip in `_population_convergence_delta`.

**Gate:** Ship **accepted**; post-28 hardening **complete** — proceed to **Iteration 29**.

---

### Iteration 29 — PASS (architect review — 2026-04-08)

**Theme:** Run economics — per-turn token tracking, run totals, `estimated_cost_usd` from `PROVIDER_PRICE_MAP` (Anthropic list prices; env-overridable), `export_version` 8, `comparison.csv` cost columns, frontend economics panel + experiment totals.

**Full write-up:** [`docs/reviews/review-iteration-29.md`](../reviews/review-iteration-29.md).

**What's good:** `simulation/economics.py` is a standalone pure-function module with no DB imports — clean boundary. `LLMCompletion` dataclass is the right abstraction; both LLM clients extract usage defensively. Token accumulation is round-level (single DB write per round, not per turn). `_turn_cost_usd` uses `effective_provider` not `llm_provider`, so hybrid runs correctly bill only Anthropic turns. Experiment aggregate is derived on read (no denormalisation). Env-overridable pricing with snapshot date for thesis citation. `comparison.csv` includes per-run token/cost columns — direct data source for RQ2.

**Minor follow-ups** — **done** (2026-04-08); see [`review-iteration-29.md`](../reviews/review-iteration-29.md) § *Follow-up resolution* and [`iteration-29-closeout.md`](../iterations/iteration-29-closeout.md) § Post–architect review.

1. ~~**M1**~~ — `_per_mtok_rates(pk)` in `estimate_cost_usd`.
2. ~~**M2**~~ — Comment on `hybrid` map entry.
3. ~~**M3**~~ — `test_economics_pure_functions`.
4. ~~**M4**~~ — Denormalised totals invariant in closeout.
5. ~~**M5**~~ — Anthropic E2E test for non-zero `estimated_cost_usd`.

**Gate:** Ship **accepted** — clean PASS. Suite **191 passed, 1 skipped** after review follow-ups.

---

# Strategic Plan: Iterations 21–27 — Research Design Layer

> **Context (from architect):** This plan was developed after a strategic session between the project lead (Mark), Opus (architect-reviewer), and Cursor (architect). Read `docs/handoffs/HANDOFF_OPUS_TO_CURSOR_2026-04-06.md` for the research motivation (agent sampling for GABM, MOE grant study).
>
> **Critical design principle:** MiroFish is a **domain-agnostic** GABM simulation engine. The school/education use case (PSLE, FSBB, Trinidad's model) is one scenario pack — not baked into the engine. Any policy domain (healthcare, urban planning, public opinion) must be expressible through scenario YAML + interaction overlays without touching engine code. Iteration 21 enforces this before the sampling work begins.
>
> **Dependency chain:** 20 → 21 → 22 → 23 → 24 → 26 → 25 → 27. (Opus priority: `hybrid_core_remainder` first, then `posture_maxvar` for October 2026 MOE conference demo, then network.)
>
> **Pre-Iteration 21 housekeeping:** Fix `export_version` in `build_capabilities_dict()` from `"4"` to `"5"` (1-line fix in `api/capabilities.py` line 37). Do this before starting Iteration 21.
>
> **ADR-002** (Interaction Visibility Policy): authored by Opus, filed at `docs/adr/ADR-002-interaction-visibility.md`. Defines `broadcast` (default), `round_participants_only`, and `network_bounded` policies. Implementation: `round_participants_only` + `network_bounded` in Iteration 25; interface designed to slot in cleanly.
>
> **Conference target (October 2026):** Iterations 21–26 must ship before the demo. **All shipped** (21–29 inclusive). **Iteration 27** — PASS_WITH_ISSUES; hardening closed. **Iteration 28** — PASS_WITH_ISSUES; hardening closed. **Iteration 29** — clean **PASS** — [`review-iteration-29.md`](../reviews/review-iteration-29.md). Platform gaps for thesis study are now closed (convergence + economics). Next: backlog or thesis scenario prep.

---

## Iteration 21 starter (pre-filled — 2026-04-06)

### Scope

- **Iteration / slice:** **Iteration 21** — **Generic engine cleanup**. Remove all school-specific hardcoding so that Iterations 22–27 build on a domain-agnostic foundation.
- **In scope:**
  1. **`initial_state` on `PersonaTemplate`** — new optional `initial_state` block in persona YAML:
     ```yaml
     personas:
       - persona_id: principal_001
         role: principal
         initial_state:
           support_level: 0.62
           resistance_level: 0.30
           workload_stress: 0.40
           belief_posture: strategic_support
     ```
     If absent, use a **neutral default** (support 0.50, resistance 0.35, workload 0.45, belief_posture "neutral"). Delete `_initial_state_for_role()` and its hardcoded `principal`/`middle_manager`/`teacher` switch in `orchestrator.py` (lines 203–208).
  2. **Demographics fallback** — rewrite `_build_demographics()` in `orchestrator.py` (lines 182–200) to remove hardcoded Singapore ethnicity cycle, SES-by-role, and age-by-role. Replacement: age derived from `role_level`-based offset (higher level → older), sex cycles, SES defaults to `"unspecified"`, ethnicity defaults to `"unspecified"`. No role-name strings in the function.
  3. **LLM scenario generation prompt** — in `scenarios_generate.py` (lines 34–54), replace `"role (one of: principal, middle_manager, teacher)"` with `"role (string — any organisational role relevant to the scenario)"` and `"role_level (1=principal, ...)"` with `"role_level (integer — 1 = highest authority, higher = lower authority)"`. Remove `"produce a minimal coherent 3-persona school policy scenario"` — replace with `"produce a minimal coherent 3-persona policy scenario matching the brief's domain"`.
  4. **Scenario validation** — in `validate.py` (lines 73–75), remove or soften the `role_level not in (1, 2, 3)` warning. Accept any positive integer. Change to: `"role_level should be a positive integer (1 = highest authority)"`.
  5. **Update existing YAML scenarios** — add `initial_state` blocks to all personas in `psle_reform_mvp.yaml` and `fsbb_comparator.yaml`, migrating the values currently hardcoded in `_initial_state_for_role()`. This ensures existing school scenarios keep identical behavior.
  6. **Overlay documentation** — update docstrings in `interaction_policy.py` to clarify that `school_trinidad` is a **domain-specific overlay plug-in** for school hierarchy scenarios. Add a brief comment showing how another domain overlay (e.g. `corporate_hierarchy`, `public_forum`) would follow the same pattern.
  7. **Embedded fallback personas** — add a comment on `_EMBEDDED_SCENARIO_PSLE` in `registry.py`: `"School-specific demo scenario. Engine is domain-agnostic; create scenario YAML for other domains."` No behavior change.
  8. **Domain packs documentation** — create `docs/domain-packs.md` (one-pager) explaining the generic engine / domain-specific scenario pack pattern. Reference `school_trinidad` as the canonical example. This helps grant reviewers and future contributors understand the architecture. *(Opus request.)*
- **Out of scope / defer:** No new features. No sampling strategies. No tier system. Pure cleanup and migration.

### Definition of done

- [ ] `_initial_state_for_role()` deleted; `initial_state` read from persona YAML; neutral default when absent.
- [ ] `_build_demographics()` contains no role-name strings (no `"principal"`, `"middle_manager"`, `"teacher"`).
- [ ] `scenarios_generate.py` LLM prompt is domain-agnostic; no hardcoded role vocabulary.
- [ ] `validate.py` accepts any positive-integer `role_level`.
- [ ] PSLE and FSBB YAMLs have `initial_state` blocks; produce identical simulation behavior as before (regression test).
- [ ] `docs/domain-packs.md` exists (one-pager explaining generic/domain-specific pattern, references `school_trinidad`).
- [ ] `pytest` passes; `npm run build` passes (if UI touched).
- [ ] `iteration-21-closeout.md` written; `SESSION_STATE.md` updated.
- [ ] `HANDOFF_TO_ARCHITECT.md` refreshed.

### Key files (hints)

- `backend/src/mirofish_backend/simulation/orchestrator.py` — `_initial_state_for_role()` (delete), `_build_demographics()` (rewrite), `_build_agent_instances()` (read `initial_state` from persona)
- `backend/src/mirofish_backend/scenarios/registry.py` — `PersonaTemplate` (add `initial_state` field), `_persona_from_mapping()` (parse it from YAML)
- `backend/src/mirofish_backend/scenarios/data/psle_reform_mvp.yaml`, `fsbb_comparator.yaml` — add `initial_state` blocks
- `backend/src/mirofish_backend/api/scenarios_generate.py` — rewrite `_GENERATE_SYSTEM_TEMPLATE`
- `backend/src/mirofish_backend/scenarios/validate.py` — relax `role_level` warning
- `backend/src/mirofish_backend/simulation/interaction_policy.py` — docstring updates only

### Decisions already made

- `role` stays a free string (already is). `role_level` stays an integer (already is). No enum restriction.
- The `school_trinidad` overlay is correctly scoped behind a flag — no behavior change needed; it uses `role_level` generically (1/2/3) which any domain can use.
- State dimensions (`support_level`, `resistance_level`, `workload_stress`, `belief_posture`) are domain-agnostic and stay as-is.

### Risks / watch

- **Regression**: the PSLE and FSBB scenarios must produce **identical** initial states after migration. Write a test that compares the new YAML-driven path against the old hardcoded values.
- **`_build_demographics()` fallback**: some tests may rely on deterministic demographics from the old hardcoded function. Verify test fixtures and update as needed.
- **Scenario generation**: LLM may produce school-specific scenarios by default (trained on existing examples). The prompt change steers it to be domain-flexible but doesn't guarantee it. Acceptable for MVP.

---

## Pre-Iteration 22 fixes (from Iteration 21 architect review)

> **Do these before starting Iteration 22.** They are small, targeted fixes from the Iteration 21 PASS review. No new features — just hardening the generic engine foundation.

### Fix 1: Clamp age floor in `_build_demographics()` (orchestrator.py)

**Problem:** `age = 49 - (role_level - 1) * 8 + (idx % 3)` goes negative when `role_level >= 8`. The generic engine now accepts any positive-integer `role_level`, so a non-school scenario with 8+ hierarchy tiers generates impossible ages (e.g. role_level 8 → age -7).

**Fix:** In `simulation/orchestrator.py`, `_build_demographics()` (~line 190), change:
```python
age = 49 - (max(1, role_level) - 1) * 8 + (idx % 3)
```
to:
```python
age = max(22, 49 - (min(role_level, 6) - 1) * 8 + (idx % 3))
```
This caps the age-spacing at 6 levels and floors at 22. Existing role_level 1/2/3 behavior is unchanged (49/41/33 baseline).

**Test:** Add a test in `test_iteration21.py`:
```python
def test_build_demographics_high_role_level_clamps_age():
    dem = _build_demographics(role_level=10, idx=0)
    assert dem["age"] >= 22
```

### Fix 2: Validate `initial_state` numeric ranges in `validate.py`

**Problem:** `_initial_state_from_persona` calls `float()` on YAML values with no range check. `support_level: 1.5` silently propagates an out-of-range value; `support_level: "high"` crashes at runtime with `ValueError`.

**Fix:** In `scenarios/validate.py`, inside the persona loop (after the existing `initial_state` type check on ~line 78), add:
```python
if "initial_state" in p and isinstance(p["initial_state"], dict):
    for dim in ("support_level", "resistance_level", "workload_stress"):
        v = p["initial_state"].get(dim)
        if v is not None:
            try:
                fv = float(v)
                if not (0.0 <= fv <= 1.0):
                    warnings.append(
                        f"personas[{i}].initial_state.{dim} should be between 0.0 and 1.0 (got {fv})"
                    )
            except (TypeError, ValueError):
                errors.append(
                    f"personas[{i}].initial_state.{dim} must be a number (got {v!r})"
                )
```

**Test:** Add two tests in `test_iteration21.py`:
```python
def test_validate_warns_initial_state_out_of_range():
    # support_level: 1.5 → warning
    ...

def test_validate_errors_initial_state_non_numeric():
    # support_level: "high" → error
    ...
```

### Fix 3 (non-blocking): Generalize `interaction_policy.py` module docstring

**Problem:** Module docstring line 15–16 still says `"hierarchical (principal → HoDs → teachers, matching Trinidad's authority structure)"`. The enum-level docstring was generalized in Iteration 21 but the module overview was not.

**Fix:** In `simulation/interaction_policy.py`, change the module docstring line from:
```
hierarchical (principal → HoDs → teachers, matching Trinidad's authority structure)
```
to:
```
hierarchical (lowest role_level first → highest, i.e. highest authority speaks first)
```

---

## Iteration 22 starter (pre-filled — 2026-04-06)

### Scope

- **Iteration / slice:** **Iteration 22** — **Sampling strategy contract (metadata only)**. Introduce `sampling_strategy` as a formal, auditable parameter. No orchestrator behavior change — all agents still get full LLM calls.
- **In scope:**
  1. New module `simulation/sampling_strategy.py` with enum-like `SAMPLING_STRATEGY_VALUES`: `full_census` | `role_stratified`.
  2. New field `sampling_strategy: str = "full_census"` on `SimulationRunRequest` (validated).
  3. **`role_stratified` engine** — pure function: takes agent list + scenario personas, **collects unique `role` values dynamically from the scenario YAML** (not from any hardcoded list — this is non-negotiable for the generic engine), ensures at least 1 agent per role at Tier 1. Remaining agents assigned Tier 2/3 in descending `role_level` order (higher number → lower tier). Returns `dict[agent_id, TierAssignment]` with per-agent rationale strings. **No hardcoded role names** — works with whatever roles the scenario defines. *(Opus: "role values must be collected dynamically from the scenario YAML, not from any hardcoded list.")*
  4. **`full_census` engine** — assigns all agents Tier 1 (current behavior, backward compatible).
  5. Optional `fidelity_tier` column (int 1/2/3) on roster CSV — overrides strategy assignment. Resolution: roster > strategy > default. *(Opus: this is important for the FSBB validation study — forces specific personas like principal/VP to Tier 1 regardless of strategy.)*
  6. **Sampling audit trail** in `config_snapshot.sampling_audit`: `sampling_strategy`, `tier_counts`, `per_agent` list with `agent_id`, `tier`, `rationale`.
  7. New field `fidelity_tier: int = 1` on `AgentInstance` — set by strategy engine, readable by orchestrator later.
  8. `GET /capabilities` updated: `sampling_strategies` list, `fidelity_tiers` description.
  9. `PlanSimulationParams` + `_simulation_run_request` updated with `sampling_strategy`.
- **Out of scope / defer:** No orchestrator behavior change (all agents still get full Tier-1 LLM calls regardless of assigned tier). Tier-aware execution comes in Iteration 23.

### Definition of done

- [x] `full_census` assigns all agents Tier 1; `role_stratified` assigns tiers by role diversity.
- [x] Roster `fidelity_tier` column overrides strategy.
- [x] `config_snapshot.sampling_audit` populated; `GET /capabilities` includes sampling strategies.
- [x] Default `full_census` produces identical behavior to pre-Iteration-22 runs (regression).
- [x] `pytest` passes; `npm run build` passes.
- [x] `iteration-22-closeout.md`; `SESSION_STATE.md` updated; `HANDOFF_TO_ARCHITECT.md` refreshed.

### Key files (hints)

New: `backend/src/mirofish_backend/simulation/sampling_strategy.py`. Existing: `api/simulations.py`, `api/capabilities.py`, `agent/orchestrator.py` (`PlanSimulationParams`), `roster/csv_roster.py`, `simulation/orchestrator.py` (`AgentInstance`).

### Risks / watch

- Ensure `role_stratified` works when all agents have the same role (degenerate case — all get Tier 1).
- Ensure it works when `agent_limit` < number of distinct roles (some roles will have no agent — not an error, but should be noted in sampling audit).

---

## Pre-Iteration 23 fixes (from Iteration 22 architect review)

> **Status: applied** in repo (`tests/test_iteration22.py`). Two missing tests from the Iteration 22 PASS review — no new features.

### Fix 1: Test for all-agents-same-role degenerate case — [x] done

**Problem:** The spec's "Risks / watch" flagged this case; logic was correct but untested.

**Shipped:** `test_role_stratified_all_same_role` — four PSLE teacher personas under `role_stratified`; first slot Tier 1, remainder in `{2, 3}`; all rationales non-empty.

### Fix 2: Test for `scenario_roles_not_represented` — [x] done

**Problem:** `build_sampling_audit_extended` was untested for missing scenario roles.

**Shipped:** `test_sampling_audit_reports_missing_roles` — one principal-only run; audit lists `middle_manager` and `teacher` in `scenario_roles_not_represented`, not `principal`.

---

## Iteration 23 starter (pre-filled — 2026-04-06)

### Scope

- **Iteration / slice:** **Iteration 23** — **Tier-aware orchestrator**. Make the orchestrator behave differently based on fidelity tier.
- **In scope:**
  1. **Tier 2 (simplified prompt)**: create a `simplified_persona_prompt()` function (Opus's naming suggestion). When building the Tier-2 prompt:
     - **Include:** role, current belief state (support/resistance/stress/posture), basic position on the policy, round context (prior turns).
     - **Omit:** psychological profile, biographical detail, `identity`, `attitudes`, `personal_history`, `implementation_profile`, influence network edges.
     - Use `peer_context_max_chars // 2` for shorter context.
     This gives Tier 2 **structural participation** without expensive per-persona depth.
  2. **Tier 3 (no LLM, placeholder)**: in `_run_one_turn`, if `fidelity_tier == 3`, skip the LLM call. Write turn row with `raw_response = "[Tier 3 — heuristic state update]"`, `effective_provider = "heuristic"`, `latency_ms = 0`. State update: **copy prior round's state unchanged** (placeholder — real heuristic in Iteration 24).
  3. **`fidelity_tier` on `agent_turns`** table + export bundle + transcript API.
  4. Tier-1 behavior must be **identical** to pre-Iteration-23 (regression).
- **Out of scope / defer:** Real Tier-3 heuristic (Iteration 24). No new strategies.

### Definition of done

- [x] Tier-1 behavior unchanged (regression test).
- [x] Tier-2 prompts omit attribute sections; shorter peer context.
- [x] Tier-3 skips LLM call; writes heuristic marker; latency 0; state unchanged.
- [x] `fidelity_tier` visible in export bundle and transcript API.
- [x] Mixed-tier round (Tier-1 + Tier-2 + Tier-3 in parallel gather) works correctly.
- [x] `pytest` passes; `npm run build` passes.
- [x] `iteration-23-closeout.md`; `SESSION_STATE.md` updated; `HANDOFF_TO_ARCHITECT.md` refreshed.

### Key files (hints)

`simulation/orchestrator.py` (`_run_one_turn` branching), `llm/prompt_templates.py` (`simplified_persona_prompt`), `db/schema.py` + `db/repo.py` (`fidelity_tier` column), `export_bundle.py` (`EXPORT_VERSION`), `api/simulations.py` + `api/capabilities.py` (import `EXPORT_VERSION`).

### Risks / watch

- `_run_one_turn` is already a complex closure. Keep the tier branching clean — check tier at the top, early-return for Tier 3 before prompt building.
- Tier-3 turns still need `insert_agent_turn` (they appear in the transcript with a marker, not silently dropped).

---

## Pre-Iteration 24 fix (historical — applied)

> **Done** as part of the Iteration 23 gate (see [`iteration-23-closeout.md`](../iterations/iteration-23-closeout.md) § *Post–Architect follow-up*). **`EXPORT_VERSION`** lives in `export_bundle.py`; `api/simulations.py` and `api/capabilities.py` import it; capabilities/export stay in sync on every bump.

---

## Iteration 24 starter (pre-filled — 2026-04-06)

### Scope

- **Iteration / slice:** **Iteration 24** — **Tier-3 heuristic engine + `hybrid_core_remainder` + raise `agent_limit` to 300**.
- **In scope:**
  1. **Real Tier-3 heuristic** in new module `simulation/heuristic.py`: after each round's `asyncio.gather`, Tier-3 agents update state based on the mean state delta of Tier-1/2 agents:
     ```
     delta = mean(tier1_2_support_after - tier1_2_support_before)
     new_support = clamp(old_support + dampening * delta + N(0, noise_std))
     ```
     Same for resistance, workload_stress. `belief_posture` unchanged (no text to parse). Noise seeded from `random_seed + round_number` for determinism.
  2. **`remainder_config`** optional JSON on `SimulationRunRequest`:
     ```json
     {
       "remainder_count": 270,
       "tier_3_dampening": 0.6,
       "tier_3_noise_std": 0.02,
       "initial_support_distribution": {"mean": 0.52, "std": 0.1},
       "initial_resistance_distribution": {"mean": 0.35, "std": 0.1},
       "initial_workload_stress_distribution": {"mean": 0.6, "std": 0.08}
     }
     ```
  3. **Synthetic remainder agents**: generated without YAML personas. Generic role string (e.g. `"remainder"`), `role_level` = scenario max `role_level` + 1, Tier 3. Demographics drawn from distributions. They participate in state aggregation but produce no transcript text (Tier-3 marker only).
  4. **`hybrid_core_remainder` strategy** in `sampling_strategy.py`: agents with the **lowest `role_level` values** (highest authority) get Tier 1; next tier gets Tier 2; remaining + synthetic remainders get Tier 3. **No hardcoded role names** — uses `role_level` as a generic hierarchy.
  5. **Raise `agent_limit` to 300** (from 200). Raise `speakers_per_round` ceiling accordingly. *(Opus: fold this into Iteration 24's stress test — not a separate hardening slice. 500 deferred to post-Iteration 27 based on actual stress test results.)*
  6. `config_snapshot` records `remainder_config`, heuristic parameters, synthetic agent count.
- **Out of scope / defer:** Network adjacency. Posture tagging. Experiments.

### Definition of done

- [ ] Tier-3 heuristic updates state with dampened mean shift + seeded noise.
- [ ] `hybrid_core_remainder` selects by `role_level` hierarchy (no hardcoded role names).
- [ ] Synthetic remainder agents created from distributions; produce Tier-3 marker turns.
- [ ] `remainder_config` stored in `config_snapshot`.
- [ ] `agent_limit` raised to 300; `speakers_per_round` ceiling raised to 300.
- [ ] Stress test: 30 Tier-1 + 270 Tier-3 agents, 2 rounds, fake LLM, completes < 10s. *(Opus: exact split for stress test.)*
- [ ] `pytest` passes; `npm run build` passes.
- [ ] `iteration-24-closeout.md`; `SESSION_STATE.md` updated; `HANDOFF_TO_ARCHITECT.md` refreshed.

### Key files (hints)

New: `simulation/heuristic.py`. Existing: `simulation/sampling_strategy.py`, `simulation/orchestrator.py` (post-gather heuristic step, synthetic agent creation), `api/simulations.py` (`remainder_config`).

### Risks / watch

- Heuristic noise must be deterministic for `random_seed` reproducibility. Use `random.Random(seed ^ round_number)` — same pattern as `_agents_for_round`.
- 270 synthetic agents × 5 rounds = 1,350 Tier-3 turn rows. DB writes are cheap (no LLM) but verify `aiosqlite` handles the volume.

---

## Post-Iteration 26 hardening (pre-filled — 2026-04-07)

> **Status:** **Complete** (2026-04-07). No further Iteration **26** items from this slice.  
> **When (historical):** Before starting Iteration **25**, or bundled in the first Iteration 25 PR.  
> **Why:** Architect review **PASS_WITH_ISSUES** — code is sound; docs and optional UX/tests need alignment.  
> **Spec:** [`docs/reviews/review-iteration-26.md`](../reviews/review-iteration-26.md).

### Scope

- **Slice name:** Post-Iteration **26** hardening (not a new numbered iteration unless Mark wants a separate gate).
- **In scope:**
  1. **`docs/SESSION_STATE.md`** — make the file internally consistent with the **Iteration 26** gate:
     - **Gate Evidence (Latest):** `uv run pytest` → **164 passed, 1 skipped** (from `backend/`); mention **`test_iteration26.py`** where relevant.
     - **Completed Work:** add **`### Iteration 26 (Completed)`** with bullets aligned to [`iteration-26-closeout.md`](../iterations/iteration-26-closeout.md) (persona/roster/population posture, `posture_maxvar`, extended audit, sampling-report endpoint, templates, YAML examples, capabilities, planner).
     - **Gate Evidence / `config_snapshot` bullets:** note **`sampling_audit.per_agent`** now includes **`role`** and **`implementation_posture`** on new runs.
     - **Next Iteration Focus:** state clearly that **Iteration 25** (network adjacency + visibility) is next; **remove** any remaining text that says “build Iteration **26** before **25**”.
  2. **Integration test (recommended):** In `backend/tests/test_iteration26.py` (or a dedicated test module), add one test that **queues** a simulation with **`sampling_strategy=posture_maxvar`**, completes under **fake LLM** (minimal rounds / small `agent_limit`), then asserts **`config_snapshot.sampling_audit`** and **`GET /simulations/{id}/sampling-report`** reflect expected posture / tier breakdown.
  3. **Frontend (optional):** On **Run** or **Run metadata** UI, add a way to open or fetch **`GET /simulations/{id}/sampling-report`** for a **completed** loaded run (link, button, or collapsible JSON). If skipped, add a **one-line** hint in the UI or keep API-only and rely on docs.
  4. **Roster template (minor):** In `backend/src/mirofish_backend/api/simulations.py`, extend **`ROSTER_CSV_TEMPLATE`** comment text: an **empty** or whitespace-only **`implementation_posture`** cell does **not** override away a persona’s YAML posture — only a **non-empty** cell overrides (`merge_persona_for_slot` behavior).
- **Out of scope:** Changing **`posture_maxvar`** tier rules, ADR-002, or Iteration **25** network features (except bundling in same PR).

### Definition of done

- [x] `SESSION_STATE.md` — Current Status, Gate Evidence, Completed Work (**§ Iteration 26**), and Next Iteration Focus all agree (**25** next, **164** tests).
- [x] Integration test added and passing **if** included (recommended).
- [x] Frontend or template comment per scope above.
- [x] `uv run pytest` from `backend/` passes; `npm run build` in `frontend/` if UI touched.
- [x] Short note in **`HANDOFF_TO_ARCHITECT.md`** (post-26 hardening paper trail).

### Key files (hints)

- `docs/SESSION_STATE.md`
- `backend/tests/test_iteration26.py` (integration test)
- `frontend/src/` — whichever tab shows run id / metadata (discover via search for `sampling-report` or export links)
- `backend/src/mirofish_backend/api/simulations.py` — `ROSTER_CSV_TEMPLATE`

---

## Iteration 25 starter (pre-filled — 2026-04-06)

> **Status:** **Shipped** — see [`iteration-25-closeout.md`](../iterations/iteration-25-closeout.md). Architect **PASS_WITH_ISSUES** follow-ups: **done** ([Post-Iteration 25 hardening](#post-iteration-25-hardening-pre-filled--2026-04-07), 2026-04-07).

### Scope

- **Iteration / slice:** **Iteration 25** — **Network adjacency + `network_centrality` strategy + `network_bounded` + `round_participants_only` visibility**.
- **In scope:**
  1. **`network_csv`** optional field on `SimulationRunRequest` (max 500k chars). Format: `source_agent_id,target_agent_id,influence_weight` (float 0.0–1.0). Parsed in new module `simulation/network.py`.
  2. **Degree centrality** computation: sum of influence weights per agent. Pure Python dict aggregation — no external graph library.
  3. **`network_centrality` strategy** in `sampling_strategy.py`: select top-K by degree centrality at Tier 1; next tier at Tier 2; remainder at Tier 3. **Requires** `network_csv` — return 422 if missing.
  4. **New `VisibilityPolicy` value: `network_bounded`** in `interaction_policy.py`: agent sees turns only from agents with a shared non-zero edge (plus broadcasts, own turns). Falls back to `broadcast` with a logged warning if `network_csv` is absent. *(See ADR-002: `docs/adr/ADR-002-interaction-visibility.md`.)*
  5. **New `VisibilityPolicy` value: `round_participants_only`**: agent sees only turns from agents selected to speak in the current round. Natural companion to `sample_k_per_round` mode. *(ADR-002.)*
  6. Refactor existing `visible_turns_for_agent()` to accept `(policy, network_graph, ...)` — single dispatch point for all three policies (`broadcast`, `round_participants_only`, `network_bounded`). Record `interaction_visibility` in `config_snapshot`.
  7. `config_snapshot` records: `network_csv_applied`, `network_node_count`, `network_edge_count`, per-agent `degree_centrality` in sampling audit.
  8. `GET /capabilities` updated: `network_bounded` and `round_participants_only` in visibility policies, `network_centrality` in sampling strategies.
- **Out of scope / defer:** Betweenness centrality (too heavy for MVP). Influence propagation in state updates (future). Experiments.
- **Pre-requisite:** ADR-002 must be committed before this iteration starts. File already exists at `docs/adr/ADR-002-interaction-visibility.md`.

### Definition of done

- [x] Network CSV parses and validates (unknown agent IDs → warning, not error).
- [x] Degree centrality computed correctly.
- [x] `network_centrality` strategy selects by centrality; requires non-empty `network_csv` (Pydantic validation).
- [x] `network_bounded` visibility filters by edge existence; falls back to `broadcast` with warning if no network CSV.
- [x] `round_participants_only` visibility filters to current-round speakers only.
- [x] `visible_turns_for_agent()` refactored to single dispatch for all visibility modes (ADR-002 + legacy `group_bounded`).
- [x] `interaction_visibility` / `visibility_effective` / `network_visibility_fallback` recorded in `config_snapshot`.
- [x] `pytest` passes; `npm run build` passes.
- [x] `iteration-25-closeout.md`; `SESSION_STATE.md` updated; `HANDOFF_TO_ARCHITECT.md` refreshed.

### Key files (hints)

New: `simulation/network.py`. Existing: `simulation/sampling_strategy.py`, `simulation/interaction_policy.py`, `api/simulations.py`.

---

## Iteration 26 starter (pre-filled — 2026-04-06)

> **Status:** **Shipped and closed** — see [`iteration-26-closeout.md`](../iterations/iteration-26-closeout.md). Architect **PASS_WITH_ISSUES** follow-ups: **done** ([Post-Iteration 26 hardening](#post-iteration-26-hardening-pre-filled--2026-04-07), 2026-04-07). `posture_maxvar` maps to Trinidad-style archetype **labels** in scenarios (e.g. `active_sense_maker`, `compliant_implementer`, `selective_adopter`). **Do not re-open** unless a new defect is filed.

### Scope

- **Iteration / slice:** **Iteration 26** — **Implementation posture + `posture_maxvar` strategy + sampling report endpoint**. Completes all five sampling strategies from the research requirements.
- **In scope:**
  1. **`implementation_posture`** field on `PersonaTemplate` — optional **free string** (not an enum). The scenario author defines posture labels (e.g. `active_sense_maker` for schools, `enthusiast` for public opinion). Engine treats them as opaque grouping labels.
  2. Add `implementation_posture` to population CSV and roster CSV as optional columns.
  3. Update PSLE and FSBB YAMLs with example posture tags on at least 2 personas.
  4. **`posture_maxvar` strategy**: collect unique posture values from the roster, ensure at least 1 agent per posture at Tier 1. Fill remaining by role diversity. Falls back to `role_stratified` if posture tags are absent on all personas.
  5. **`GET /simulations/{id}/sampling-report`**: returns researcher-readable JSON derived from `config_snapshot.sampling_audit` — tier summary, by-role breakdown, by-posture breakdown, centrality scores (if applicable), per-agent list. Not a new data store — reshapes existing data.
  6. `GET /capabilities` updated: posture field documented, `posture_maxvar` in strategies.
- **Out of scope / defer:** Experiments.

### Definition of done

- [x] `implementation_posture` accepted on persona YAML, population CSV, roster CSV.
- [x] `posture_maxvar` covers all posture categories; falls back gracefully without tags.
- [x] Sampling report endpoint returns structured JSON for any completed run.
- [x] `pytest` passes; `npm run build` passes (no UI change this slice).
- [x] `iteration-26-closeout.md`; `SESSION_STATE.md` updated; `HANDOFF_TO_ARCHITECT.md` refreshed.

### Key files (hints)

`scenarios/registry.py` (`PersonaTemplate`), `simulation/sampling_strategy.py`, `population/csv_population.py`, `roster/csv_roster.py`, `api/simulations.py` (new endpoint), `api/capabilities.py`.

---

## Post-Iteration 25 hardening (pre-filled — 2026-04-07)

> **When:** Before starting Iteration **27**, or bundled in the **first Iteration 27 PR** if Joan prefers one branch.
> **Why:** Architect review **PASS_WITH_ISSUES** — code is correct; tests, docs, and two design confirmations needed.
> **Spec:** [`docs/reviews/review-iteration-25.md`](../reviews/review-iteration-25.md).

### Scope

- **Slice name:** Post-Iteration **25** hardening (not a new numbered iteration unless Mark wants a separate gate).
- **In scope:**
  1. **Integration test (recommended):** In `backend/tests/test_iteration25.py`, add one test that **queues** a simulation with `network_csv` + `sampling_strategy=network_centrality` + `visibility_policy=network_bounded`, completes under **fake LLM** (1 round, 3 agents), then asserts:
     - `config_snapshot.network_csv_applied == True`
     - `config_snapshot.network_edge_count > 0`
     - `sampling_audit.per_agent[*].degree_centrality` populated (non-zero for connected agents)
     - `GET /simulations/{id}/sampling-report` → `centrality` map non-null
     - `config_snapshot.interaction_policy.visibility_effective == "network_bounded"`
  2. **Fix `network_node_count`:** In `api/simulations.py` (~line 724), change from `len(agent_ids_for_audit)` to the count of agents that appear as source or target in at least one parsed edge. E.g.:
     ```python
     "network_node_count": len({s for s, _, _ in net_parse.edges} | {t for _, t, _ in net_parse.edges}) if net_parse else 0,
     ```
  3. **`VisibilityPolicy.FULL` cleanup:** Either remove `FULL` from the enum (keep `full → broadcast` normalization in `build_interaction_policy`) or filter it from `_enum_values` in `capabilities.py` so `GET /capabilities` doesn't list both `broadcast` and `full`. If existing `config_snapshot` values store `"full"`, keep the normalization path.
  4. **`round_participants_only` broadcast design call:** Confirm whether broadcast-type turns should pass through under `round_participants_only` (like they do for `network_bounded` and `group_bounded`). If yes, add a `turn.get("interaction_type") == ChannelType.BROADCAST.value` passthrough in the `ROUND_PARTICIPANTS_ONLY` branch of `visible_turns_for_agent`. If no (strict cohort isolation is intended), add a one-line docstring comment stating the design choice.
  5. **`docs/SESSION_STATE.md`:** Update Current Status (Iteration **25** last gate, **172** tests), add **Completed Work § Iteration 25**, update **Gate Evidence**, point **Next Iteration Focus** at **Iteration 27**.
  6. **Minor fixes:**
     - Rename `test_samling_strategy_values_contains_network_centrality` → `test_sampling_strategy_values_contains_network_centrality` (missing "p").
     - Add one-line docstring to `parse_network_csv`: duplicate `(source, target)` pairs are kept — `degree_centrality` sums both weights; `undirected_neighbor_map` deduplicates.
     - In `SimulationRunRequest.network_csv` description, expand `persona_id_NNN` to: `"Agent ids use the format persona_id_NNN (e.g. principal_001_000); check sampling_audit.per_agent[].agent_id for exact run ids."`.
- **Out of scope:** Changing `network_centrality` tier rules, new visibility policies, or Iteration **27** experiment features (except bundling in same PR).

### Definition of done

- [x] Integration test added and passing (recommended).
- [x] `network_node_count` reflects connected agents, not total roster.
- [x] `GET /capabilities` does not list duplicate `full` / `broadcast` visibility values.
- [x] `round_participants_only` broadcast behavior confirmed (code or docstring).
- [x] `SESSION_STATE.md` consistent with Iteration 25 + post-25 hardening (**174** tests, **27** next).
- [x] Minor test typo + docstring + description fixes.
- [x] `uv run pytest` from `backend/` passes; `npm run build` in `frontend/` if UI touched.

### Key files (hints)

- `backend/tests/test_iteration25.py` (integration test)
- `backend/src/mirofish_backend/api/simulations.py` — `network_node_count` line, `network_csv` description
- `backend/src/mirofish_backend/simulation/interaction_policy.py` — `VisibilityPolicy` enum, `round_participants_only` branch
- `backend/src/mirofish_backend/api/capabilities.py` — `_enum_values` or filter
- `backend/src/mirofish_backend/simulation/network.py` — docstring on duplicate edges
- `docs/SESSION_STATE.md`

---

## Post-Iteration 27 hardening (pre-filled — 2026-04-07)

> **Status:** **Done** (2026-04-07) — gate evidence in [`iteration-27-closeout.md`](../iterations/iteration-27-closeout.md) § Post–Iteration 27 hardening.
>
> **When:** Before starting the next numbered iteration, or bundled in the first post-27 PR.
> **Why:** Architect review **PASS_WITH_ISSUES** — core design is sound; blocking POST, missing failure test, and duplicated helpers need attention.
> **Spec:** [`docs/reviews/review-iteration-27.md`](../reviews/review-iteration-27.md).

### Scope

- **Slice name:** Post-Iteration **27** hardening (not a new numbered iteration unless Mark wants a separate gate).
- **In scope:**
  1. **Experiment failure test (recommended):** In `backend/tests/test_iteration27.py`, add a test that monkeypatches `queue_simulation_run` to raise an exception after the first run is queued, then asserts:
     - `get_experiment_row` returns `status == "failed"` and `completed_at` is not None.
     - The HTTP response is 500.
  2. **Unify `_series_key` helpers:** In `api/experiments.py`, extract a shared `_deduplicate_key(base: str, used: set[str]) -> str` helper. Both `_series_key` and `_series_key_for_link` should compute their `base` string and delegate deduplication to this single function.
  3. **Frontend cancel + elapsed timer:** In `ExperimentConsole.tsx`, add `AbortController` on the `createExperiment` fetch call + a **Cancel** button + elapsed-time display while `busy`. Same pattern as `AgentConsole`.
  4. **Background experiment execution (recommended — defer if tight):** In `api/experiments.py`, change `create_experiment_endpoint` to return `{ experiment_id }` immediately. Move the sequential run loop into `asyncio.create_task`. The frontend should poll `GET /experiments/{id}` on a 2-second interval to show per-run progress. **Deferred** — blocking limitation documented in **`api/experiments.py`** module docstring.
  5. **Minor fixes:**
     - Collapse `set_experiment_status` `completed`/`failed` branches into one (identical SQL).
     - Add `run_count` to `list_experiments` (JOIN or subquery on `experiment_runs`) and surface in `ExperimentConsole` recent list.
     - Add a toggle or table view for all 5 comparison metrics in the frontend (currently sparklines show only `implementation_readiness`).
- **Out of scope:** Parallel multi-run execution (separate backlog item). `DELETE /experiments` endpoint (backlog). LLM-powered cross-experiment analysis.

### Definition of done

- [x] Experiment failure test added and passing.
- [x] `_series_key` helpers unified into shared deduplication function.
- [x] Frontend cancel + elapsed timer working on experiment creation.
- [x] Background experiment execution implemented **or** blocking limitation documented (module docstring; background task backlog).
- [x] Minor fixes applied (`set_experiment_status` collapse, `run_count`, multi-metric sparkline + details table).
- [x] `uv run pytest` from `backend/` passes; `npm run build` in `frontend/` passes.

### Key files (hints)

- `backend/tests/test_iteration27.py` (failure test)
- `backend/src/mirofish_backend/api/experiments.py` — `_series_key`, `_series_key_for_link`, `create_experiment_endpoint`
- `backend/src/mirofish_backend/db/repo.py` — `set_experiment_status`, `list_experiments`
- `frontend/src/components/ExperimentConsole.tsx` — cancel/abort, elapsed timer, multi-metric view
- `frontend/src/lib/api.ts` — `createExperiment` (add `AbortSignal` support)

---

## Iteration 27 starter (pre-filled — 2026-04-06)

> **Status:** **Shipped** — [`iteration-27-closeout.md`](../iterations/iteration-27-closeout.md). Architect **PASS_WITH_ISSUES** follow-ups: **done** ([Post-Iteration 27 hardening](#post-iteration-27-hardening-pre-filled--2026-04-07), 2026-04-07).

> **Prerequisite (historical):** **Iteration 25** + **post-25 hardening** ([`iteration-25-closeout.md`](../iterations/iteration-25-closeout.md)).

### Scope

- **Iteration / slice:** **Iteration 27** — **Multi-run experiment framework**. Enable the core research use case: run the same scenario with different sampling strategies side by side and compare outcomes.
- **In scope:**
  1. **New SQLite table `experiments`**: `id` (TEXT PK), `name`, `scenario_id`, `base_random_seed`, `base_total_rounds`, `status` (pending/running/completed/failed), `created_at`, `completed_at`.
  2. **New nullable column `experiment_id`** on `simulation_runs` (FK to `experiments`; NULL for standalone runs — backward compatible).
  3. **`POST /experiments`**: accepts `name`, `scenario_id`, `random_seed`, `total_rounds`, and `runs[]` array (each with `sampling_strategy`, `agent_limit`, optional `remainder_config`, `network_csv`). Queues all runs via existing `queue_simulation_run`. Returns `experiment_id`.
  4. **`GET /experiments/{id}`**: metadata + per-run status + comparison table (round × strategy matrix of `implementation_readiness`, `alignment_index`, `adoption_momentum`, `conflict_events`, `consistency_index`).
  5. **`GET /experiments/{id}/export.json`** and **`.zip`**: individual run exports bundled + a `comparison.csv` with columns `run_label, round, implementation_readiness, alignment_index, adoption_momentum, conflict_events, consistency_index`.
  6. **Frontend Experiments tab**: create form (scenario picker + seed + add-strategy rows). Status view (per-run progress). Comparison chart (SVG line chart, one series per strategy, reusing existing sparkline approach). Absorb the existing Compare tab's functionality.
  7. `GET /capabilities` updated: experiment parameter space.
  8. Runs are dispatched **sequentially** via existing `queue_simulation_run` + `wait_for_simulation_terminal` infrastructure (parallel multi-run is a future optimization).
- **Out of scope / defer:** Parallel multi-run execution. LLM-powered cross-experiment analysis.

### Definition of done

- [x] `POST /experiments` creates experiment and queues all runs with shared seed.
- [x] `GET /experiments/{id}` returns status + comparison table.
- [x] Experiment export includes `comparison.csv`.
- [x] Standalone runs have NULL `experiment_id` (backward compat).
- [x] Frontend Experiments tab: create, status, comparison chart.
- [x] `pytest` passes; `npm run build` passes.
- [x] `iteration-27-closeout.md`; `SESSION_STATE.md` updated; `HANDOFF_TO_ARCHITECT.md` refreshed.

### Key files (hints)

`db/schema.py` + `db/repo.py` (new table + FK), new: `api/experiments.py`, `export_bundle.py` (experiment export), `frontend/src/components/ExperimentConsole.tsx` (or similar), `frontend/src/App.tsx` (new tab).

### Design decision: experiments vs agent orchestrator

`POST /experiments` is a **thin DB-backed wrapper** — it creates an experiment record, loops over runs calling `queue_simulation_run`, and tags each `simulation_runs` row with the `experiment_id`. It does NOT duplicate the agent orchestrator. The agent orchestrator (`POST /agent/ask`) remains the **stateless** path for ad-hoc multi-run plans. Experiments add **persistence** and **cross-run comparison**.

### Risks / watch

- DB migration: adding `experiment_id` FK to `simulation_runs` must be backward-compatible (nullable, no constraint on existing rows). Use the same `_ensure_column` pattern from prior migrations.
- Experiment status: track as `completed` only when ALL runs reach terminal state (completed/failed). If any run fails, experiment status = `completed` (not failed) — individual run statuses tell the story.


---

## Post-Iteration 28 hardening (pre-filled — 2026-04-07)

> **Status:** **Done** (2026-04-08) — [`iteration-28-closeout.md`](../iterations/iteration-28-closeout.md) § Post–Iteration 28 hardening.
>
> **When:** Before starting Iteration **29**, or bundled in the first Iteration 29 PR.
> **Why:** Architect review **PASS_WITH_ISSUES** — convergence logic is correct but not wired through the experiment or agent orchestrator APIs, and the streak-reset path is untested.
> **Spec:** [`docs/reviews/review-iteration-28.md`](../reviews/review-iteration-28.md).

### Scope

- **Slice name:** Post-Iteration **28** hardening (not a new numbered iteration unless Mark wants a separate gate).
- **In scope:**
  1. **Wire convergence into experiments (required):** Add `convergence_threshold: float | None = Field(default=None, ge=0.0, le=1.0)` and `convergence_patience: int = Field(default=2, ge=1, le=25)` to `ExperimentCreateRequest` in `api/experiments.py`. These are base-level fields shared across all runs in the experiment (convergence parameters should be identical for fair cross-strategy comparison). `_merge_to_simulation_request` already forwards base fields to `SimulationRunRequest`, so no additional merge logic is needed. Add a test: create an experiment with `convergence_threshold` set; verify child runs converge.
  2. **Wire convergence into agent orchestrator (required):** Add both fields to `PlanSimulationParams` in `agent/orchestrator.py` (optional, same validators). Forward them through `_simulation_run_request`. Update `validate_plan_against_capabilities` to accept these fields. The planner LLM already sees them in `GET /capabilities`; this just lets the plan validation accept them.
  3. **Streak-reset test (required):** Add a test in `test_iteration28.py` with a fake LLM that returns **varying** state for the first few rounds (deltas above threshold), then stabilises. Verify that the simulation runs past the first sub-threshold round and only converges after `convergence_patience` consecutive sub-threshold rounds. This tests the `conv_streak = 0` reset path.
  4. **Minor improvements (recommended):**
     - Add `convergence_delta` to `get_merged_round_metrics` query in `db/repo.py` and include it in `_build_comparison_table` + `_flatten_comparison_for_csv` in `experiments.py`. Add it to `experiment_comparison_csv_bytes` in `export_bundle.py`. This lets experiment comparison CSVs show convergence speed per strategy.
     - Show `converged_at_round` in the experiment per-run status list in `ExperimentConsole.tsx` (e.g. "Converged at R14" or "Full 18 rounds").
- **Out of scope:** Per-group convergence. Convergence on `belief_posture`. Automatic re-run on premature convergence.

### Definition of done

- [x] `ExperimentCreateRequest` includes convergence fields; experiment with convergence tested.
- [x] `PlanSimulationParams` includes convergence fields; forwarded + validated.
- [x] Streak-reset test added and passing.
- [x] `convergence_delta` in experiment comparison table and CSV.
- [x] `converged_at_round` shown in experiment per-run list.
- [x] `uv run pytest` from `backend/` passes; `npm run build` in `frontend/` passes.

### Key files (hints)

- `backend/src/mirofish_backend/api/experiments.py` — `ExperimentCreateRequest`
- `backend/src/mirofish_backend/agent/orchestrator.py` — `PlanSimulationParams`, `_simulation_run_request`, `validate_plan_against_capabilities`
- `backend/tests/test_iteration28.py` — streak-reset test
- `backend/src/mirofish_backend/db/repo.py` — `get_merged_round_metrics`
- `backend/src/mirofish_backend/api/experiments.py` — `_build_comparison_table`, `_flatten_comparison_for_csv`
- `backend/src/mirofish_backend/export_bundle.py` — `experiment_comparison_csv_bytes`
- `frontend/src/components/ExperimentConsole.tsx` — per-run `converged_at_round`

---

## Iteration 28 starter (pre-filled — 2026-04-07)

> **Status:** **Shipped** — [`iteration-28-closeout.md`](../iterations/iteration-28-closeout.md). Architect **PASS_WITH_ISSUES** follow-ups: **done** ([Post-Iteration 28 hardening](#post-iteration-28-hardening-pre-filled--2026-04-07), 2026-04-08).
>
> **Prerequisite:** Post-Iteration 27 hardening complete.
> **Why this matters:** The thesis methodology explicitly commits to a convergence stopping rule — auto-stopping when mean attitude change falls below a threshold for two consecutive rounds. Without this, every run must be cut manually and the "round count as a research variable" claim lacks rigour.

### Scope

- **Iteration / slice:** **Iteration 28** — **Convergence stopping criterion**. Add an evidence-based stopping rule so simulations auto-terminate when the agent population has stabilised, rather than running a fixed number of rounds.
- **In scope:**
  1. **`convergence_threshold`** (float, default `0.01`) and **`convergence_patience`** (int, default `2`) on `SimulationRunRequest` — optional fields; when absent the simulation runs to `total_rounds` as before (fully backward compatible).
  2. **Per-round convergence delta** computation in `simulation/orchestrator.py`: after each round's state snapshots are written, compute the mean absolute change across all agents' `support_level`, `resistance_level`, and `workload_stress` compared to the prior round. Record this as `convergence_delta` on the `global_state_snapshots` row (new nullable column via `_ensure_column`).
  3. **Stopping logic**: if `convergence_delta < convergence_threshold` for `convergence_patience` consecutive rounds, set a flag and do not start the next round. Write `converged_at_round` (int | null) to the `simulation_runs` row.
  4. **`config_snapshot`** records `convergence_threshold`, `convergence_patience`, and `converged_at_round` (null when not triggered).
  5. **Poll API** (`GET /simulations/{id}`): expose `converged_at_round` and the per-round `convergence_delta` series in `state_timeline` entries.
  6. **Export bundle**: `converged_at_round` in run metadata; per-round `convergence_delta` in `global_state_snapshots.csv`.
  7. **Frontend Live tab**: show convergence delta per round on the state chart (secondary axis or tooltip); when `converged_at_round` is set, display a banner: _"Converged at round N"_.
  8. **`GET /capabilities`**: document `convergence_threshold` and `convergence_patience` ranges under `simulation_run`.
- **Out of scope / defer:** Per-role or per-group convergence (thesis requires only population-level). Convergence on `belief_posture` string (skip — non-numeric). Automatic re-run if convergence is too fast.

### Definition of done

- [x] `convergence_threshold` / `convergence_patience` accepted on `POST /simulations/run`; omit threshold = full `total_rounds`.
- [x] Per-round `convergence_delta` written to `global_state_snapshots`.
- [x] `converged_at_round` written to `simulation_runs` when triggered; null otherwise.
- [x] Simulation stops early when criterion is met; does not over-run.
- [x] `config_snapshot` includes convergence parameters and outcome.
- [x] Poll API and export bundle surface the new fields (`export_version` **7**).
- [x] Frontend Live tab shows convergence delta sparkline and convergence banner; Run tab optional fields.
- [x] `pytest` passes; `npm run build` passes.
- [x] `iteration-28-closeout.md`; `SESSION_STATE.md` updated.

### Key files (hints)

- `backend/src/mirofish_backend/simulation/orchestrator.py` — round loop, post-gather convergence check
- `backend/src/mirofish_backend/db/schema.py` — `_ensure_column` for `convergence_delta` on `global_state_snapshots`, `converged_at_round` on `simulation_runs`
- `backend/src/mirofish_backend/db/repo.py` — update `insert_global_state_snapshot`, `get_simulation_export_bundle`, `get_merged_round_metrics`
- `backend/src/mirofish_backend/api/simulations.py` — new request fields, `config_snapshot`, poll API response
- `backend/src/mirofish_backend/api/capabilities.py` — document new parameters
- `frontend/src/components/LiveRunDashboard.tsx` — convergence delta display, convergence banner

### Decisions already made

- Convergence is measured on **numeric attitude dimensions only** (`support_level`, `resistance_level`, `workload_stress`). `belief_posture` is a string — exclude it.
- Mean absolute change across **all agents** (not per-group) — matches the thesis methodology description.
- When `convergence_patience = 2` (default), the simulation must see two consecutive sub-threshold rounds before stopping. This prevents premature termination from a temporarily quiet round.
- The convergence check runs **after** the round's state is persisted — it reads from the newly written snapshots, not from in-memory state.

### Risks / watch

- First round has no prior round to diff against — skip the convergence check for `round_number == 1`.
- Tier-3 synthetic remainder agents do not change state via LLM (only via heuristic). Their deltas still count toward the population mean — this is correct and consistent.
- If `agent_limit` is large and many agents are Tier-3, the heuristic's dampened deltas may cause premature convergence. Document this in the closeout as a known limitation.

---

## Iteration 29 starter (pre-filled — 2026-04-07)

> **Status:** **Shipped** — [`iteration-29-closeout.md`](../iterations/iteration-29-closeout.md) (2026-04-08).
>
> **Prerequisite:** Iteration **28** + **post–Iteration 28 hardening** complete (2026-04-08).
> **Why this matters:** The thesis RQ2 explicitly compares computational cost across sampling strategies (token usage, API cost, processing time). Without instrumented cost tracking, this analysis must be done manually from provider dashboards — fragile and incomplete. This iteration makes cost a first-class output of every run.

### Scope

- **Iteration / slice:** **Iteration 29** — **Run economics dashboard**. Track token usage and estimate API cost per simulation run and per experiment, surfacing this data in the API, exports, and frontend.
- **In scope:**
  1. **Token tracking in orchestrator**: in `_run_one_turn`, capture `input_tokens` and `output_tokens` returned by the LLM client (LM Studio and Anthropic both return usage in their response). Accumulate totals after each round's `asyncio.gather` returns. Persist as two new nullable columns on `simulation_runs`: `total_input_tokens` (INTEGER) and `total_output_tokens` (INTEGER) via `_ensure_column`.
  2. **Per-turn token columns** on `agent_turns`: `input_tokens` and `output_tokens` per turn (also via `_ensure_column`). Allows per-agent, per-round cost breakdown in the export CSV.
  3. **`simulation/economics.py`** (new module): `PROVIDER_PRICE_MAP` constant + `estimate_cost_usd` pure function:
     ```python
     PROVIDER_PRICE_MAP = {
         "anthropic": {"input_per_mtok": 3.00, "output_per_mtok": 15.00},
         "lmstudio":  {"input_per_mtok": 0.00, "output_per_mtok": 0.00},
         "hybrid":    {"input_per_mtok": 3.00, "output_per_mtok": 15.00},
     }
     ```
     Prices are overridable via env vars (`ANTHROPIC_INPUT_PRICE_PER_MTOK` etc.) for future changes. Note the pricing snapshot date in the module docstring.
  4. **`economics` object** on `GET /simulations/{id}` response:
     ```json
     {
       "total_input_tokens": 42000,
       "total_output_tokens": 8400,
       "estimated_cost_usd": 0.252,
       "llm_provider": "anthropic",
       "tier_breakdown": {"tier_1_turns": 180, "tier_2_turns": 0, "tier_3_turns": 0}
     }
     ```
  5. **Experiment detail** (`GET /experiments/{id}`): add `economics` per run row (token totals + estimated cost); aggregate `total_estimated_cost_usd` across all runs in the experiment.
  6. **Export bundle**: include `economics` in run metadata of `export.json`; add `input_tokens`, `output_tokens` columns to `agent_turns.csv`.
  7. **`comparison.csv`** in experiment ZIP: add `input_tokens`, `output_tokens`, `estimated_cost_usd` columns per run row — this is the direct data source for the RQ2 cost comparison table in the thesis.
  8. **Frontend Experiments tab**: cost column in the per-run status list and comparison table; `total_estimated_cost_usd` shown for the experiment.
  9. **Frontend Run metadata tab**: show the `economics` object for the loaded run.
  10. **`GET /capabilities`**: document `economics` support; note that cost estimates use `PROVIDER_PRICE_MAP` defaults and the pricing snapshot date.
- **Out of scope / defer:** Real-time cost ticker during a live run (backlog). Hard cost cap before a run starts. Actual invoice reconciliation.

### Definition of done

- [x] `total_input_tokens` / `total_output_tokens` accumulated per run and persisted.
- [x] Per-turn `input_tokens` / `output_tokens` on `agent_turns`.
- [x] `estimated_cost_usd` computed from `PROVIDER_PRICE_MAP`; zero for `lmstudio`.
- [x] `economics` object in `GET /simulations/{id}` and `GET /experiments/{id}`.
- [x] Export bundle and CSVs include token / cost fields (including `comparison.csv`).
- [x] Frontend Run metadata tab and Experiments tab surface cost data.
- [x] `pytest` passes; `npm run build` passes.
- [x] `iteration-29-closeout.md`; `SESSION_STATE.md` updated.

### Key files (hints)

New: `backend/src/mirofish_backend/simulation/economics.py`. Existing:
- `backend/src/mirofish_backend/simulation/orchestrator.py` — capture usage per turn, accumulate after gather
- `backend/src/mirofish_backend/db/schema.py` + `db/repo.py` — new columns, accumulate totals, expose in export
- `backend/src/mirofish_backend/api/simulations.py` — `SimulationStatusResponse` economics field, poll API
- `backend/src/mirofish_backend/api/experiments.py` — experiment detail + per-run economics
- `backend/src/mirofish_backend/export_bundle.py` — run metadata + CSV columns + `comparison.csv`
- `frontend/src/components/ExperimentConsole.tsx` — cost column in comparison table + experiment total
- `frontend/src/App.tsx` — Run metadata section economics block

### Decisions already made

- Tier-3 heuristic turns generate **zero LLM tokens** — store as `0` in per-turn columns, which correctly reflects their cost advantage. This is the key data point for the thesis RQ2 cost comparison (e.g. hybrid-core-remainder vs full-census will show a dramatic token reduction from the Tier-3 majority).
- `lmstudio` cost is **$0** — local model, no API charge. This is intentional and meaningful for the thesis: a researcher can run the full study locally for free if using an open-source model.
- Token accumulation must be **thread-safe**: `asyncio.gather` dispatches turns concurrently. Collect per-turn `(input_tokens, output_tokens)` results after the gather returns (not inside the concurrent closures) to avoid race conditions.

### Risks / watch

- LM Studio's API may not always return a `usage` object. Wrap token extraction in a try/except; default to `None` (null in DB) rather than 0, so missing data is distinguishable from zero-cost heuristic turns.
- Anthropic's response includes `usage.input_tokens` and `usage.output_tokens` — check that `claude_client.py` currently surfaces these from the response body; patch if not.
- The `PROVIDER_PRICE_MAP` defaults will go stale. Add a `PRICE_MAP_DATE = "2026-04-07"` constant so the thesis can cite the date of the cost estimate.

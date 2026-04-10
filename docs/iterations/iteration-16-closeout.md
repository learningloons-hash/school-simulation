# Iteration 16 closeout — Agent-ready API surface

**Date:** 2026-04-05 (architect PASS); follow-up polish applied same window  
**Status:** Shipped

## Shipped

### 1. `POST /scenarios/generate-from-brief`

- **Module:** `backend/src/mirofish_backend/api/scenarios_generate.py`
- Plain-English **`brief`** (20–16k chars) → LLM → **`validate_scenario_document`** (same path as catalog CRUD).
- **200:** `{ document, warnings[] }`
- **422:** `detail` includes **`errors`**, **`warnings`**, optional **`raw_llm_text`** (validation failure or unparseable JSON).
- **502:** LLM transport failure.
- System prompt injects **allowed bundled RAG paths** from `list_allowed_corpus_paths()` so agents do not invent corpus paths. Comment above **`_GENERATE_SYSTEM_TEMPLATE`** explains **`{{`/`}}`** escaping for **`.format()`** (not f-strings).

### 2. `GET /capabilities`

- **Module:** `backend/src/mirofish_backend/api/capabilities.py`
- **`export_version`:** `4`; **`agent_context_version`** from `agent_context.AGENT_CONTEXT_VERSION`; **`population_schema_version`** from `POPULATION_SCHEMA_VERSION`; **`interaction_policy_version`** from `interaction_policy.INTERACTION_POLICY_VERSION`.
- **`interaction_policy`:** enum **values** from `ChannelType`, `TurnOrderPolicy`, `VisibilityPolicy`, `InteractionOverlay` at runtime. OpenAPI docstring notes **`bundled_rag_paths`** is filesystem / install dependent.
- **`simulation_run`:** `simulation_modes`, `population_sample_modes`, `llm_providers` from **`SIMULATION_MODE_VALUES`** / **`POPULATION_SAMPLE_MODE_VALUES`** / **`LLM_PROVIDER_VALUES`** in `api/simulations.py` (shared with Pydantic validators — no duplicate string lists).

### 3. `POST /simulations/{simulation_id}/analyze`

- **Module:** `api/simulations.py`
- **Body:** `research_question` (4–8k chars); optional **`max_tokens`**.
- Loads **`get_simulation_export_bundle`**; requires **`run.status == "completed"`** else **409**.
- **Stateless:** no DB writes.
- **Context control:** transcript entries omit **`raw_prompt`**. Two-stage caps are named together in **`api/simulations.py`**: **`ANALYZE_RAW_RESPONSE_MAX_CHARS_FIRST_PASS`** (3000), **`ANALYZE_LLM_JSON_CHAR_BUDGET`** (180_000), then either head+tail reclip (**`ANALYZE_TRANSCRIPT_KEEP_HEAD_TAIL`** × 2 when turn count exceeds **`ANALYZE_TRANSCRIPT_COUNT_FOR_SECOND_RECLIP`**) or **`ANALYZE_RAW_RESPONSE_MAX_CHARS_SECOND_PASS`** (1200) per turn. **`_bundle_notes`** records which path ran.
- **200:** `key_findings`, `per_agent_summary`, `trajectory_narrative`, `suggested_follow_ups`, truncated **`raw_llm_text`**.

### 4. Frontend

- **`ScenarioWizard`:** “Generate from brief” textarea + button → **`generateScenarioFromBrief`** → **`hydrateFromDocument`**; sets create mode and step 0.
- **`api.ts`:** `fetchCapabilities`, `generateScenarioFromBrief`.
- **`vite.config.ts`:** dev proxy **`/capabilities`** → backend.

### 5. Tests

- **`backend/tests/test_iteration16.py`** — capabilities shape, generate success + validation 422, analyze 409 vs 200 (LLM mocked), plus **second-stage shrink** tests (`transcript_reclipped` vs `raw_response_shortened` **`_bundle_notes`** paths).

## Definition of done

- [x] All three endpoints implemented and tested.
- [x] Wizard wired to generate-from-brief.
- [x] `/capabilities` reflects enums + shared run-parameter constants.
- [x] `pytest` passes; `npm run build` passes.
- [x] This closeout + `SESSION_STATE.md` updated.

## Architect review — non-blocking items addressed (post PASS)

- **`.format()` / `{{` braces:** comment on **`_GENERATE_SYSTEM_TEMPLATE`** in **`scenarios_generate.py`**.
- **Analyze thresholds:** shared module constants (see §3) + tests for both second-stage branches.
- **`bundled_rag_paths`:** documented in **`GET /capabilities`** docstring (environment-specific).
- **`hybrid` vs LM Studio for utilities:** docstrings on **`generate-from-brief`**, **`llm-fill`**, **`/analyze`** — use **`anthropic`** in settings for frontier-only authoring/analysis.
- **Docs:** closeout date aligned with Iterations 14–15; **`SESSION_STATE.md`** Completed Work reordered **11 → 12 → 13 → 16**.

## Deferred / follow-ups

- **ADR-002** (interaction policy contract) still not authored (noted in Iteration 15).
- **Retry loop** for failed validation is left to the caller (422 carries errors + raw snippet).
- **Researcher UI** for `/analyze` and **`GET /capabilities`** discovery not in scope.

# Senna session state

This file is the single source of truth for cross-session handoff.
Update it at the end of each iteration gate.

**Who does what (GM vs Architect vs Builder, closeouts, arc review):** [`handoffs/SENNA_AGENT_CYCLE.md`](handoffs/SENNA_AGENT_CYCLE.md).

## Current Status

- Project: `mirofish-mvp` (product name: **Senna**)
- **Senna Arc 8 CLOSED — GM PASS** (2026-05-19) — gates **`senna-iter-35`–`39`** + economics follow-up. **Arc 7 GM PASS**. **Arc 6 CLOSED**.
- Senna Arc 1: [`senna-iter-1-closeout.md`](iterations/senna-iter-1-closeout.md) … [`senna-iter-5-closeout.md`](iterations/senna-iter-5-closeout.md). Arc 2: [`senna-iter-6-closeout.md`](iterations/senna-iter-6-closeout.md) … [`senna-iter-10-closeout.md`](iterations/senna-iter-10-closeout.md). Arc 3: [`senna-iter-11-closeout.md`](iterations/senna-iter-11-closeout.md) … [`senna-iter-15-closeout.md`](iterations/senna-iter-15-closeout.md). Arc 4: [`senna-iter-16-closeout.md`](iterations/senna-iter-16-closeout.md) … [`senna-iter-20-closeout.md`](iterations/senna-iter-20-closeout.md). Arc 5: [`senna-iter-21-closeout.md`](iterations/senna-iter-21-closeout.md) … [`senna-iter-25-closeout.md`](iterations/senna-iter-25-closeout.md). Arc 6: [`senna-iter-26-closeout.md`](iterations/senna-iter-26-closeout.md) … [`senna-iter-29-closeout.md`](iterations/senna-iter-29-closeout.md). Arc 7: [`senna-iter-30-closeout.md`](iterations/senna-iter-30-closeout.md) … [`senna-iter-34-closeout.md`](iterations/senna-iter-34-closeout.md). Arc 8: [`senna-iter-35-closeout.md`](iterations/senna-iter-35-closeout.md) … [`senna-iter-39-closeout.md`](iterations/senna-iter-39-closeout.md). Specs: [`HANDOFF_SENNA_ARC1.md`](handoffs/HANDOFF_SENNA_ARC1.md) … [`HANDOFF_SENNA_ARC8.md`](handoffs/HANDOFF_SENNA_ARC8.md).
- Backend / thesis platform: **Iteration 29** (run economics) **shipped** with **architect PASS** and **review follow-ups applied**. See [`iteration-29-closeout.md`](iterations/iteration-29-closeout.md) and [`review-iteration-29.md`](reviews/review-iteration-29.md) § *Follow-up resolution*.
- **Next (Senna):** Await GM next arc handoff (if any). **Backlog:** parallel dispatch, SSE-in-browser, WAL + batch inserts.
- Last completed Senna work: **Arc 8** (2026-05-19). **Current focus:** thesis / product backlog until next GM arc. Thesis gate: **Iteration 29** (2026-04-08).
- Last verified run id (QA sample): `ad901483b0a840689c71debb771cf0c1` — FSBB, `agent_limit` 4, `full_round_robin`, 2 rounds (all four agents have turns in DB; see `iteration-10-closeout.md` post-gate notes)
- Last update date: **2026-05-20** — **Git:** Arcs 1–8 pushed to `origin/main` (`7f426fc`); runtime data excluded per `.gitignore`. Ritual: push after GM arc PASS — [`handoffs/SENNA_AGENT_CYCLE.md`](handoffs/SENNA_AGENT_CYCLE.md) § *Git push after arc close*.
- Last verified: backend **`uv run pytest` 290 passed, 2 skipped**.

## Environment and Access

- Host machine: Mac mini (always-on server)
- Thin client: Windows laptop over Tailscale
- Backend default: `0.0.0.0:8100`
- Frontend default: `0.0.0.0:3100`
- LLM endpoint: `http://127.0.0.1:1234/v1` (LM Studio on Mac mini)

## Learnings (ops / dev)

| Date | Issue | Prevention |
|------|-------|------------|
| 2026-05-20 | Blank white UI at `:3100` — `modelChoiceOptions` used before `useState` (TDZ `ReferenceError`); build still green | [`.cursor/rules/senna-react-hooks-order.mdc`](../.cursor/rules/senna-react-hooks-order.mdc) — declare state before derived `const` / effects that set it; check browser Console |

## Completed Work

### MVP 1.0

- FastAPI backend + React frontend + SQLite transcript persistence
- Run API (`/simulations/run`) and polling status API (`/simulations/{id}`)
- Transcript export workflow to CSV

### Iteration 1 (Completed)

- Added structured interaction metadata for each turn:
  - `interaction_type`
  - `target_scope`
  - `target_agent_id`
  - `target_agent_name`
  - `intent_tag`
- Added backward-compatible schema migration logic for existing SQLite DBs
- Added deterministic interaction planning in orchestrator
- Added cross-agent interaction memory block in prompts
- Added frontend display of interaction metadata
- Added test coverage for interaction metadata persistence

### Iteration 2 (Completed)

- Added deterministic state engine with per-agent state dimensions:
  - `support_level`
  - `resistance_level`
  - `workload_stress`
  - `belief_posture`
- Added demographic profile fields in state snapshots:
  - `age`, `sex`, `ethnicity`, `ses`
- Added global round state snapshots:
  - `implementation_readiness`
  - `alignment_index`
- Added round outcome indicators:
  - `adoption_momentum`
  - `conflict_events`
  - `consistency_index`
- Extended simulation status API with `state_timeline` and `outcome_indicators`
- Added deterministic replay/state timeline tests

### Iteration 2 Hardening Slice (Completed)

- Introduced versioned prompt templates with explicit `system` + `user` roles.
- Switched runtime prompt version default to `v1`.
- Increased default LLM output limit to `llm_max_tokens=512`.
- Added simulation failure guard so crashed background runs set `status=failed` and persist `failure_reason`.
- Added `config_snapshot` persistence per simulation run for reproducibility.
- Exposed `config_snapshot` and `failure_reason` in simulation status API.

### Iteration 3 (Completed)

- `GET /simulations` — list recent runs (query `limit`, default 50).
- `GET /simulations/{id}/export.json` — full export bundle (`export_version`, run, transcript with `raw_prompt`, flat tables, `state_timeline`, `outcome_indicators`).
- `GET /simulations/{id}/export.zip` — ZIP of CSVs: `simulation_run.csv`, `agent_turns.csv`, `agent_state_snapshots.csv`, `global_state_snapshots.csv`, `round_outcomes.csv`.
- Frontend: tabbed UI (Run, Transcript, Outcomes, State, Run metadata, Compare runs).
- Frontend: recent-run list, load run by ID, ZIP + JSON download links, compare two runs by outcome indicators.
- Tests: export ZIP builder + repo list/export bundle coverage.

### Iteration 4 (Completed)

**Core (review-gap batch)**

- Structured agent state: models must append `<state>{...json...}</state>`; `llm/state_parse.py`; orchestrator prefers parsed JSON, falls back to keyword heuristics if the block is missing or invalid.
- `llm/router.py` + `llm/claude_client.py`: `llm_provider` `lmstudio` | `anthropic` (Anthropic Messages API via httpx).
- Config: default `llm_max_tokens=1024`, `llm_provider`, `anthropic_api_key`, `anthropic_model`, `peer_context_max_chars`; `requires-python = >=3.11,<3.13` and `pyyaml` in `backend/pyproject.toml`.
- API: `SimulationRunRequest` optional `max_tokens`, `llm_provider`; `config_snapshot` records provider, models, `peer_context_max_chars`; `run_simulation_task_guarded` for testable failure handling.
- Scenarios: `scenarios/data/*.yaml` loaded over embedded fallback; PSLE MVP in `psle_reform_mvp.yaml`.
- Tests: prompt shape (incl. round ≥ 2 evolution copy), state parse / orchestrator path, failure guard, YAML registry, context clip; state engine fakes `llm_complete` + `<state>` JSON.
- `backend/.gitignore` for venv and local sqlite.

**Follow-on (LM Studio integration)**

- `lmstudio_client.py`: failed chat/completions return parsed server error text in `RuntimeError` (debuggable transcript lines).
- `llm/context_clip.py`: shrink peer snippets for prompts (strip `<state>`, trim reasoning-to-**Draft:**, tail limit) to avoid `n_ctx` exhaustion when models emit long chain-of-thought.
- Prompts: explicit ban on visible “Thinking Process” / numbered plans; user copy distinguishes working memory vs what others said.
- `get_recent_interactions` includes `round_number`, `turn_index`, `agent_id`; peer lines prefixed `[Round R, turn T]`; current agent excluded from others-block; first turn of round N>1 uses widened interaction window; default policy text for unscheduled rounds references prior stakeholder dialogue.
- Frontend Run tab: explain round counter vs per-turn transcript; show live turn count while `running`.

**Documentation**

- `docs/iterations/iteration-4-closeout.md` — full iteration log and file map.
- `docs/reviews/REVIEW_REQUEST_iteration-4.md` — Opus entry checklist; expected output `docs/reviews/review-iteration-4.md`.

### Iteration 5 (Completed)

- Second YAML scenario **`fsbb_comparator`** (`scenarios/data/fsbb_comparator.yaml`) with FSBB-themed `policy_events`, three personas, and `rag_enabled` + `rag_corpus_paths` pointing at `scenarios/data/corpus/fsbb_comparator/brief.txt`.
- Scenario registry extended with optional **`rag_enabled`** and **`rag_corpus_paths`** (backward compatible; PSLE unchanged).
- RAG scaffold package **`mirofish_backend.rag/`**: character chunking, cosine top‑k retrieval, in-process embedding cache; **`rag/embeddings.py`** calls LM Studio OpenAI-compatible **`POST /v1/embeddings`** (same base URL as chat).
- Orchestrator: when **`rag_effective`**, retrieves top‑k snippets from query = policy event + intent tag and injects a **“Reference excerpts”** block into the **user** prompt via **`build_user_prompt(..., context_snippets=...)`**; failures log a warning and continue without snippets.
- Config / provenance: **`RAG_ENABLED`**, **`EMBEDDING_MODEL`** (empty → `lmstudio_model`), **`RAG_TOP_K`**, **`RAG_CHUNK_SIZE`**, **`RAG_CHUNK_OVERLAP`**, **`RAG_MAX_INJECT_CHARS`**; **`config_snapshot`** includes **`rag_effective`**, **`embedding_model_id`**, server/scenario flags, corpus paths, and RAG tuning fields. **`POST /simulations/run`** optional **`rag_enabled`** forces on/off.
- Frontend: Run tab scenario list includes **FSBB Comparator (MVP)**; `StartSimulationRequest` allows optional **`rag_enabled`**.
- Tests: RAG chunk/similarity/retrieve (mock embeddings), prompt RAG block, FSBB YAML assertions (`backend/tests/test_rag.py`, `test_scenarios_yaml.py`).

### Iteration 6 (Completed)

- SQLite **`validity_notes`** table: optional **`round_number`** (NULL = run-level), **`rater_id`**, three optional scores (**`face_score`**, **`construct_score`**, **`predictive_score`**) and matching **`_*_rubric`** text fields, **`notes`**, **`created_at`**.
- **`POST /simulations/{id}/validity-notes`** — create note (422 if no substantive fields; 400 if `round_number` out of range for that run).
- **`GET /simulations/{id}`** includes **`validity_notes`** array; **`export.json`** **`export_version`** bumped to **`2`** with **`validity_notes`**; ZIP adds **`validity_notes.csv`**. *(Current export version is **`3`** — Iteration 12 — see Gate Evidence.)*
- **`config_snapshot`** (new runs) includes **`state_audit_enabled`** from **`STATE_AUDIT_ENABLED`** env (default false) — reserved for future second-pass state audit; **no LLM behavior** when false.
- Frontend: **Validity** tab — form to save notes and list saved notes for the loaded run.
- Tests: `backend/tests/test_validity_notes.py`.

### Iteration 7 (Completed)

- **Persona YAML**: optional **`psychological_profile`** and **`implementation_profile`** nested maps on any persona; `PersonaTemplate` extended with defaults `{}`; loader backward compatible.
- **Prompts**: `build_system_prompt` renders optional **Psychological profile** and **Implementation profile** sections when non-empty; PSLE principal persona includes sample fields in `psle_reform_mvp.yaml`.
- **Hybrid routing**: `llm_provider` **`hybrid`** — **`resolve_effective_provider`** uses **Anthropic** on **turn_index == 1** each round (broadcast anchor), **LM Studio** for all other turns; **`config_snapshot`** records **`hybrid_routing_policy`**: `frontier_first_turn_of_round` and composite **`model_used`** string.
- **Orchestrator**: explicit **`lmstudio_model`** argument (always real LM Studio model id) for LM calls; per-turn **`logger.info`** line with routing mode and effective provider.
- **Config / API**: **`LLM_PROVIDER=hybrid`** supported; **`POST /simulations/run`** accepts **`hybrid`**; frontend Run tab optional **LLM routing** dropdown.
- **Docs**: `references/ARCHITECTURE.md` added as a short orientation index.
- Tests: `test_hybrid_router.py`, prompt + YAML profile assertions.

### Iteration 8 (Completed)

- **Design note:** `docs/plans/iteration-8-live-dashboard-design.md` (polling vs future SSE, chart behavior at N agents, key-quotes phases A/B).
- **Scale / cost:** `docs/plans/SCALE_LIMITS_AND_COST.md` (`agent_limit` 1–50, soft warning >20, sequential LLM cost shape, hybrid note).
- **Frontend:** **Live** tab — SVG sparklines + tables from existing **`GET /simulations/{id}`** payload (global readiness/alignment, adoption series, per-agent support/resistance/workload); no new chart dependency.
- **Faster poll while running:** ~**750ms** between polls (was ~2s); same endpoint, client-only.
- **Run tab:** link to Live dashboard + pointer to scale doc under agent limit; layout `maxWidth` ~1100px.
- **`references/ARCHITECTURE.md`:** links to observability + scale docs.

### Iteration 9 (Completed)

- **Scenario / YAML:** optional top-level **`groups`** and per-persona **`groups`** (list of `group_id` strings); **`fsbb_comparator.yaml`** carries an example.
- **Roster CSV:** `mirofish_backend.roster` — parse + merge by **1-based `slot`**; **`POST /simulations/run`** body **`roster_csv`** (optional); invalid CSV → **422**.
- **API:** **`agent_limit`** **1–50**; **`GET /simulations/roster-csv-template`**; **`config_snapshot`** adds **`scenario_groups`**, **`scale_warning`**, roster provenance fields, **`roster_unknown_group_ids`**.
- **Persistence:** **`group_ids`** column (JSON text) on **`agent_turns`** and **`agent_state_snapshots`**; transcript + **`state_timeline`** + export bundle include **`group_ids`**.
- **Orchestrator / prompts:** optional **`personas_for_run`**; system prompt lists group affiliations when non-empty.
- **Frontend:** roster textarea + template link; agent limit **50**; UI warning when **> 20** agents.
- **Tests:** `test_roster_csv.py`, extended YAML/repo/export assertions.
- **Docs:** `docs/iterations/iteration-9-closeout.md`; **`SCALE_LIMITS_AND_COST.md`** updated.

### Iteration 10 (Completed)

- **`AgentContextV1`:** versioned per-agent bundle (`slot_index`, `demographics`, `group_ids`); `AgentInstance.context`; prompts via `to_prompt_demographics()`.
- **Interaction modes:** `simulation_mode` **`full_round_robin`** (default) | **`sample_k_per_round`** with `speakers_per_round`; deterministic subset per round from `random_seed` + round index; non-sampled agents skip LLM that round (state unchanged).
- **API / `config_snapshot`:** `agent_context_version`, `simulation_mode`, `speakers_per_round` (**JSON `null`** when `full_round_robin`).
- **Traceability:** `agent_state_snapshots.spoke_this_round` + `state_timeline[].agents[].spoke_this_round` (end of each round; distinguishes non-sampled vs missing row).
- **Frontend:** Run tab interaction controls; Live tab shows mode + K.
- **ADR:** `docs/adr/ADR-001-iteration-10-11-contracts.md` Interface section updated.
- **Tests:** `test_agent_context.py`, `test_interaction_sample_k.py`.
- **Docs:** `docs/iterations/iteration-10-closeout.md`.

### Iteration 11 (Completed)

- **Population contract v1:** [`population/csv_population.py`](../../backend/src/mirofish_backend/population/csv_population.py) — parse pool CSV; **`weighted`** / **`stratified`** draw without replacement (`random_seed`); keys align to **`AgentContextV1`** (demographics, `group_ids` via `persona_id` template + row).
- **API:** `population_csv`, `population_sample_mode` on **`POST /simulations/run`**; **`GET /simulations/population-csv-template`**.
- **Merge order:** population draw → optional roster overlay per slot (roster wins on conflicts).
- **Orchestrator:** **`slot_overrides`** parallel list (demographics + optional attribute section dicts from population); `_merge_demographics` overlays CSV fields on synthetic base.
- **`config_snapshot`:** `population_schema_version`, `population_draw` trace, `population_thesis_note`, `population_merge_order`, etc.
- **Frontend:** Run tab population controls; Live tab population summary.
- **Tests:** `test_population.py`.
- **Docs:** `docs/iterations/iteration-11-closeout.md`.

### Iteration 12 (Completed)

- **`effective_provider` / `effective_model`** on each **`agent_turns`** row; poll transcript + **`export.json`** / ZIP **`agent_turns.csv`**.
- **`export.json` `export_version`:** **`3`** (additive transcript fields).
- **`POST /simulations/run`:** returns **`{ id, warnings[] }`** for unknown roster/population **`group_ids`** vs scenario **`groups`**.
- **`sample_k_per_round`:** **`interaction_last_k`** for “first turn of round 2+” scales with **`len(round_agents)`** (capped 120); exact formula in **ADR-001** § Iteration 12.
- **Tests:** `tests/test_iteration12.py` (hybrid + export, roster + population **`warnings`** API, fake-LLM stress **&lt; 5s** for 40 turns).
- **Docs / handoff:** `iteration-12-closeout.md`; ADR-001; **`HANDOFF_TO_ARCHITECT.md`** refreshed for **Iteration 13** forward focus + brief **parallel-LLM deferral** note.

### Iteration 13 (Completed)

- **`AgentContext` v2** (`AGENT_CONTEXT_VERSION` **`"2"`**): **`identity`**, **`attitudes`**, **`personal_history`** on each agent; YAML personas + optional population **`identity_json`** / **`attitudes_json`** / **`personal_history_json`** (schema **v2**).
- **Prompts:** structured sections in **`build_system_prompt`** when non-empty.
- **SQLite:** **`agent_state_snapshots.attribute_sections_json`**; **`state_timeline`** exposes **`attribute_sections`**; **`export.json` `export_version`:** **`4`**.
- **`config_snapshot`:** **`agent_context_version`:** **`"2"`**; **`population_schema_version`:** **`2`** when pool CSV is used.
- **Frontend:** State tab shows JSON for attribute sections; validity text references export **v4**.
- **Tests:** `tests/test_iteration13_attributes.py` + prompt/context extensions.
- **Docs:** `iteration-13-closeout.md`; ADR-001 updated.

### Iteration 16 (Completed)

- **`POST /scenarios/generate-from-brief`** — brief → LLM → **`validate_scenario_document`**; **422** with errors + optional **`raw_llm_text`** on failure.
- **`GET /capabilities`** — versions + **`interaction_policy`** enum values + run parameter lists (**schema-driven** via `interaction_policy` enums and **`SIMULATION_MODE_VALUES`** / **`POPULATION_SAMPLE_MODE_VALUES`** / **`LLM_PROVIDER_VALUES`** in `api/simulations.py`).
- **`POST /simulations/{id}/analyze`** — completed runs only (**409** otherwise); stateless LLM analysis; transcript/bundle **clipping** for context limits (two-stage caps documented in `api/simulations.py`).
- **Frontend:** Scenario Wizard **Generate from brief**; Vite proxy **`/capabilities`**.
- **Tests:** `tests/test_iteration16.py`.
- **Docs:** `iteration-16-closeout.md`.

### Iteration 17 (Completed)

- **`POST /agent/plan`**, **`POST /agent/execute`**, **`POST /agent/ask`** — planner LLM uses **`build_capabilities_dict()`** (same as **`GET /capabilities`**); execute chains generate (optional) → **`queue_simulation_run`** → **`wait_for_simulation_terminal`** → **`analyze_simulation_export`**; **`/agent/ask?stream=true`** SSE progress.
- **Resilience:** **`HTTPException`** from **`generate_scenario_from_brief`** or **`queue_simulation_run`** is caught **per step** (**`generate_failed`** / **`queue_failed`**, **`analysis_error`**); later runs in a multi-step plan still execute.
- **API:** optional **`plan_temperature`** (0–2, default **0.35**) on plan/ask bodies; **`wait_timeout_seconds`** on ask is **per run** (multi-run JSON wall-clock can be large).
- **`queue_simulation_run`** + **`wait_for_simulation_terminal`** in **`api/simulations.py`**; **`get_simulation_run_status_only`** in **`db/repo.py`**.
- **Tests:** `tests/test_iteration17.py` (includes resilience + temperature forwarding); **`pytest.mark.manual`** placeholder for SSE; **`[tool.pytest.ini_options]`** **`manual`** marker in **`backend/pyproject.toml`**.
- **Demo:** `scripts/agent_ask_demo.py`.
- **Docs:** `iteration-17-closeout.md`; architect PASS notes reconciled in **`HANDOFF_TO_BUILDER.md`**.

### Iteration 19 (Completed)

- **Parallel LLM within rounds:** `asyncio.gather` + `asyncio.Semaphore(llm_concurrency_cap)` dispatches all turns in a round concurrently; rounds remain sequential.
- **Turn index pre-assignment:** `turn_assignments = list(enumerate(round_agents, start=1))` computed before gather so interaction plans and `interaction_last_k` are deterministic.
- **Per-turn error isolation:** LLM errors caught inside `_run_one_turn`; catastrophic exceptions caught by `return_exceptions=True`; failing turns logged, round continues.
- **`config.py`:** `LLM_CONCURRENCY_CAP` env var (default 4).
- **`api/simulations.py`:** `SimulationRunRequest.llm_concurrency_cap` (1–16, optional); recorded in `config_snapshot`.
- **Tests:** `tests/test_iteration19.py` — 7 tests: parallel execution, determinism, error isolation, 40-turn stress, API field (117 passed, 1 skipped).
- **Architect PASS follow-ups (same session):** `build_capabilities_dict()` exposes `llm_concurrency_cap` range; `PlanSimulationParams` + `_simulation_run_request` + `validate_plan_against_capabilities` forward the cap through agent orchestrator; `round_complete` log line with `wall_ms` / `failed` counts added to simulation orchestrator.

### Iteration 20 (Completed)

- **`agent_limit` raised to 200:** `SimulationRunRequest.agent_limit` `le=200`; `speakers_per_round` `le=200`; same in `PlanSimulationParams`.
- **`aggregation_threshold`:** new field on `SimulationRunRequest` and `PlanSimulationParams` (default 20, 1–200). `config_snapshot` gains `aggregation_threshold` and `aggregation_mode` (`True` when `agent_limit >= aggregation_threshold`).
- **`compute_cohort_summary` (pure function):** `export_bundle.py` — groups `agent_state_snapshots` by `(group_id, round_number)`; returns per-round averages for support/resistance/workload; agents with no groups aggregate under `group_id: ""`.
- **`export.json` version 5:** `"export_version": "5"` and `"cohort_summary"` key in export JSON.
- **`export.zip`:** adds `cohort_summary.csv` (group_id, round_number, agent_count, spoke_count, avg_* columns).
- **`api/capabilities.py`:** `agent_limit` and `aggregation_threshold` ranges exposed.
- **Agent orchestrator planner:** `aggregation_threshold` forwarded through `PlanSimulationParams` → `_simulation_run_request`; JSON shape in `_PLANNER_SYSTEM` includes the field.
- **Tests:** `tests/test_iteration20.py` — 8 tests (125 passed, 1 skipped).
- **Docs:** `docs/plans/scale-feasibility-500-agent.md` — thesis-grade 500-agent feasibility note.

### Iteration 21 (Completed)

- **Persona `initial_state`:** optional YAML block on each persona; `PersonaTemplate.initial_state` in `registry.py`; orchestrator uses `_initial_state_from_persona` (removed `_initial_state_for_role`). Neutral default when absent: support 0.50, resistance 0.35, workload 0.45, belief_posture `neutral`.
- **Synthetic demographics:** `_build_demographics(role_level, idx)` — age `max(22, 49 - (min(role_level, 6) - 1) * 8 + idx % 3)` (legacy 49/41/33 for levels 1–3; clamp avoids negative ages for large `role_level`), sex cycle, `ethnicity`/`ses` default `unspecified`.
- **Bundled scenarios:** `psle_reform_mvp.yaml` and `fsbb_comparator.yaml` migrated with `initial_state` matching former hardcoded values; embedded FSBB fallback personas updated; PSLE fallback comment documents domain-specific demo.
- **Generate-from-brief:** domain-agnostic system template; optional `initial_state` in schema description.
- **Validation:** `role_level` warning only when `< 1`; `initial_state` type check; **`initial_state` numeric validation** — warn if support/resistance/workload outside `[0,1]`; error if non-numeric (architect pre–Iter 22).
- **Interaction policy docs:** overlays as domain plug-ins; module-level turn-order bullet uses generic ascending `role_level` wording (no principal/HoD/teacher in overview).
- **`GET /capabilities`:** `export_version` string **`"5"`** (aligns with export JSON).
- **`docs/domain-packs.md`:** generic engine vs domain packs one-pager.
- **Roster merge:** `merge_persona_for_slot` preserves `initial_state`.
- **Tests:** `tests/test_iteration21.py` — 9 tests; full suite **134 passed, 1 skipped**.

### Iteration 22 (Completed)

- **`sampling_strategy`:** `SimulationRunRequest` field `full_census` (default) \| `role_stratified`; validated; stored on `config_snapshot` with **`sampling_audit`** (`tier_counts`, `per_agent` with `agent_id`, `tier`, `rationale`; extended audit can include `scenario_roles_not_represented`).
- **`simulation/sampling_strategy.py`:** Pure tier assignment from scenario roles (dynamic, no hardcoded role list); `role_stratified` ensures at least one tier-1 slot per represented role, then assigns tiers 2/3 by descending `role_level` for duplicates.
- **Roster:** optional CSV column **`fidelity_tier`** (1–3) overrides strategy per slot (`ParsedRosterRow.fidelity_tier`).
- **`AgentInstance.fidelity_tier`:** set when building agents; **`run_simulation_task`** / **`_build_agent_instances`** take optional `fidelity_tiers` list. **No** change to LLM calls (all agents still full execution — Iteration 23).
- **`GET /capabilities`:** `sampling_strategies`, `fidelity_tiers` under `simulation_run`.
- **Agent planner:** `PlanSimulationParams.sampling_strategy`; validated vs capabilities; forwarded to run request JSON.
- **Tests:** `tests/test_iteration22.py` — **12** tests (includes `test_role_stratified_all_same_role`, `test_sampling_audit_reports_missing_roles` — architect pre–Iter 23); full suite **146 passed, 1 skipped**.

### Iteration 23 (Completed)

- **Tier execution:** `_run_one_turn` branches on `fidelity_tier`: **1** — full `build_system_prompt` + LLM (same as pre–Iter 23); **2** — `simplified_persona_prompt` + peer/memory clips at `peer_context_max_chars // 2`; **3** — no LLM, `raw_response` `[Tier 3 — heuristic state update]`, `effective_provider` `heuristic`, `latency_ms` 0, state unchanged (placeholder).
- **Persistence / API:** `agent_turns.fidelity_tier` column; poll transcript + `get_simulation_export_bundle` include `fidelity_tier`.
- **Export:** `export_version` **`6`** (`api/simulations.py`, `capabilities.py`); ZIP transcript CSV includes column when non-empty bundle uses dynamic headers.
- **Frontend:** Transcript line shows fidelity tier; `SimulationTurn` type updated.
- **Tests:** `tests/test_iteration23.py` — 3 tests; full suite **149 passed, 1 skipped**.
- **Post–Architect (Pre–24):** `EXPORT_VERSION = "6"` in `export_bundle.py`; `simulations.py` / `capabilities.py` import it (single bump point for future export versions).

### Iteration 24 (Completed)

- **Tier-3 heuristic:** `simulation/heuristic.py` — mean Tier-1/2 state deltas per round + `tier_3_dampening` / `tier_3_noise_std`; skipped when no Tier-1/2 speakers in that round (Tier-3-only runs unchanged).
- **`hybrid_core_remainder`:** `sampling_strategy.py` — role_level bands; `synthetic_remainder_*` personas always Tier 3.
- **Synthetic remainders:** `simulation/remainder.py` — optional **`remainder_config`** on **`POST /simulations/run`**; population draw uses **`core_limit = agent_limit - remainder_count`**; **`config_snapshot`** records `remainder_config`, `synthetic_remainder_count`, `core_agent_limit`, `tier_3_heuristic`.
- **Scale:** **`agent_limit`**, **`speakers_per_round`**, **`aggregation_threshold`** ceiling **300** (`simulations.py`, `capabilities.py`, `PlanSimulationParams`).
- **Tests:** `tests/test_iteration24.py` — 3 tests (tier assignment, heuristic motion, 300-agent stress); **`test_iteration20`** updated for max 300.

### Iteration 25 (Completed)

- **`network_csv`:** Optional on **`POST /simulations/run`** (500k max); `simulation/network.py` — parse, **degree centrality**, undirected **neighbor map**; unknown `agent_id` endpoints → **warnings**, row skipped.
- **`network_centrality`:** Sampling strategy — Tier 1 for agents tied at max centrality; requires non-empty **`network_csv`** (Pydantic + queue).
- **ADR-002 visibility:** **`round_participants_only`** (current-round speakers + own turns + **broadcast** turns from any speaker); **`network_bounded`** (neighbors + broadcasts + own); **`broadcast`** (alias **`full`** on run API); **`network_bounded`** without CSV → **broadcast** + **`run_warnings`** + **`network_visibility_fallback`**.
- **`config_snapshot`:** `network_csv_applied`, `network_edge_count`, **`network_node_count`** (distinct endpoints in parsed edges — post-25 hardening); `interaction_policy.interaction_visibility`, `visibility_effective`, `network_visibility_fallback`; **`sampling_audit.per_agent[].degree_centrality`**; **`GET …/sampling-report`** **`centrality`** map when scores present.
- **Orchestrator:** Passes **`network_neighbors`**, **`visibility_effective`**; per-round **`round_speaker_ids`** into **`visible_turns_for_agent`**.
- **Agent planner:** **`PlanSimulationParams.network_csv`**; visibility validation (**`full`** in plans normalizes to **`broadcast`** vs capabilities).
- **`GET /capabilities`:** **`visibility_policies`** omits legacy **`full`** (no duplicate with **`broadcast`**).
- **Tests:** `tests/test_iteration25.py` (incl. **E2E** `network_csv` + **`network_centrality`** + **`network_bounded`**); **`test_iteration15_interaction_policy`** extended.
- **Post–25 hardening (2026-04-07):** Architect follow-ups from **`review-iteration-25.md`** — see [`iteration-25-closeout.md`](iterations/iteration-25-closeout.md) § Post–Iteration 25 hardening.

### Senna iter-39 (Arc 8, completed 2026-05-19)

- **GM follow-up:** `economics.py` bills from `effective_profile_id` → `pricing_key` (OpenAI/OpenRouter non-zero; local/heuristic $0; legacy anthropic-only fallback).
- **`llm/state_parse.py`:** `resolve_state_from_response` + provenance (`model_parsed`, `repaired`, `keyword_fallback`); duplicate `<state>` blocks and light JSON repair.
- **`agent_turns.state_update_source`:** transcript poll + export JSON/ZIP.
- **Tests:** `test_senna_arc8_integration.py`; manual `scripts/lmstudio_profile_smoke.py` (skipped in CI).
- **Closeout:** [`senna-iter-39-closeout.md`](iterations/senna-iter-39-closeout.md). **Arc 8 Cursor sign-off complete** (2026-05-19) — GM arc review pending.

### Senna iter-38 (Arc 8, completed 2026-05-19)

- **`simulation/preflight.py`:** turn/cost/context estimates; warnings merged into `POST /simulations/run` and `config_snapshot.preflight`.
- **`POST /simulations/preflight`:** preview without queuing.
- **Frontend:** debounced Run setup estimate panel + preflight warnings before Start.
- **Closeout:** [`senna-iter-38-closeout.md`](iterations/senna-iter-38-closeout.md).

### Senna iter-37 (Arc 8, completed 2026-05-19)

- **Commercial profiles:** `openai_default`, `openrouter_default`; settings for base URL, model, API key env names.
- **Adapter:** optional `Authorization: Bearer` on `chat_completion_openai_compatible`; plumbed via `run_openai_compatible_api_key` → orchestrator → `llm_complete`.
- **Closeout:** [`senna-iter-37-closeout.md`](iterations/senna-iter-37-closeout.md).

### Senna iter-36 (Arc 8, completed 2026-05-19)

- **`llm/model_profiles.py`:** `@register_builtin_profile` registry; `BUILTIN_PROFILE_IDS` derived from registry; `ModelCapabilities` + `capabilities_dict()`; `is_builtin` on profiles and capability/snapshot payloads.
- **Tests:** registry id parity, local + frontier capability rows, capabilities API + config snapshot metadata.
- **Closeout:** [`senna-iter-36-closeout.md`](iterations/senna-iter-36-closeout.md).

### Senna iter-35 (Arc 8, completed 2026-05-19)

- **`PlanSimulationParams.model_profile_id`:** optional; validated against built-in profile ids; forwarded to `SimulationRunRequest` via agent orchestrator; planner template + capability validation updated.
- **Tier-3 provenance:** `effective_profile_id="heuristic"` sentinel on heuristic turns (`HEURISTIC_PROFILE_SENTINEL`).
- **Tests:** planner parity + Arc 7 `create_task` mock cleanup in `test_senna_arc7_hardening.py` / `test_model_profiles.py`.
- **Closeout:** [`senna-iter-35-closeout.md`](iterations/senna-iter-35-closeout.md).

### Senna iter-34 (Arc 7, completed 2026-05-19)

- **`tests/test_senna_arc7_hardening.py`:** legacy + profile request shapes; export JSON/ZIP economics and model provenance; hybrid routing E2E.
- **Post–GM:** `resolve_run_llm_provider` — profile-only POST infers `llm_provider` from built-in profile id.
- **Closeout:** [`senna-iter-34-closeout.md`](iterations/senna-iter-34-closeout.md). **Arc 7 Cursor sign-off complete** (2026-05-19) — Architect re-review after GM follow-up.

### Senna iter-33 (Arc 7, completed 2026-05-19)

- **`llm/routing_policies.py`:** `local_only`, `frontier_only`, `hybrid_first_turn`; maps from `llm_provider`.
- **`config_snapshot`:** `routing_policy`, `routing_profile_local_id`, `routing_profile_frontier_id`; per-turn `effective_profile_id` on `agent_turns`.
- **Tests:** `tests/test_routing_policies.py`; hybrid trace test extended in `test_iteration12`.
- **Closeout:** [`senna-iter-33-closeout.md`](iterations/senna-iter-33-closeout.md).

### Senna iter-32 (Arc 7, completed 2026-05-19)

- **`GET /capabilities`:** `model_profiles` block (built-in profiles + hybrid routing metadata).
- **Frontend Run setup:** capability-driven AI model dropdown; `model_profile_id` on run when a profile is selected; hardcoded fallback if capabilities unavailable.
- **Closeout:** [`senna-iter-32-closeout.md`](iterations/senna-iter-32-closeout.md).

### Senna iter-31 (Arc 7, completed 2026-05-19)

- **`llm/model_profiles.py`:** built-in `local_lmstudio_default` / `anthropic_default`; resolver; `config_snapshot` provenance helpers.
- **`api/simulations.py`:** optional `model_profile_id`; profile metadata + resolved model/base URL on runs.
- **Tests:** `tests/test_model_profiles.py`.
- **Closeout:** [`senna-iter-31-closeout.md`](iterations/senna-iter-31-closeout.md).

### Senna iter-30 (Arc 7, completed 2026-05-19)

- **`llm/openai_compatible_client.py`:** generic OpenAI-compatible chat completions; error body parsing; usage token aliases.
- **`llm/lmstudio_client.py`:** compatibility shim re-exporting the generic client (RAG embeddings unchanged import path).
- **`llm/router.py`:** local provider path calls generic adapter.
- **Tests:** `tests/test_openai_compatible_client.py` — lmstudio alias, errors, token parsing, router dispatch.
- **Closeout:** [`senna-iter-30-closeout.md`](iterations/senna-iter-30-closeout.md).

### Iteration 29 (Completed)

- **Economics:** Per-turn **`input_tokens`** / **`output_tokens`**; run **`total_*_tokens`**; **`economics`** on **`GET /simulations/{id}`** and **`run.economics`** in export JSON; **`export_version` `8`**.
- **Cost:** `simulation/economics.py` — Anthropic list defaults (**`PRICE_MAP_DATE`**); env overrides; **`estimated_cost_usd`** from per-turn billing (`anthropic` provider only among LLM turns).
- **Experiments:** **`total_estimated_cost_usd`**; per-run **`economics`**; **`comparison.csv`** token + cost columns.
- **Frontend:** Run metadata economics panel; Experiments cost summary + per-run line.
- **Tests:** **`tests/test_iteration29.py`** (E2E + **`test_economics_pure_functions`** + anthropic pricing path); **`LLMCompletion`** return type for all **`llm_complete`** callers.
- **Architect review:** **PASS** — [`review-iteration-29.md`](reviews/review-iteration-29.md); follow-ups applied (see closeout § Post–architect review).
- **Closeout:** [`iteration-29-closeout.md`](iterations/iteration-29-closeout.md).

### Iteration 28 (Completed)

- **Convergence:** Population mean abs Δ across **`support_level`**, **`resistance_level`**, **`workload_stress`** vs prior round; **`convergence_patience`** consecutive rounds below **`convergence_threshold`** → early **`completed`** with **`converged_at_round`**.
- **API / DB:** **`GET /simulations/{id}`** exposes **`converged_at_round`** and timeline **`convergence_delta`**; nullable columns on **`global_state_snapshots`** and **`simulation_runs`**; **`get_simulation_run_status_only`** returns **`converged_at_round`** for experiment rows.
- **Export:** **`export_version` `7`**; **`global_state_snapshots.csv`** includes **`convergence_delta`** when present; experiment **`comparison.csv`** includes **`convergence_delta`**.
- **Experiments / agent:** **`POST /experiments`** base convergence fields; **`PlanSimulationParams`** + capability validation + planner template; **`_merge_to_simulation_request`** forwards to children.
- **Frontend:** Run + Experiments create optional convergence; Live sparkline + banner; Experiments per-run convergence line + comparison **`convergence_delta`** metric / table.
- **Tests:** **`tests/test_iteration28.py`** (incl. streak reset, experiment E2E, agent plan validation).
- **Closeout:** [`iteration-28-closeout.md`](iterations/iteration-28-closeout.md) (§ Post–Iteration 28 hardening).

### Iteration 27 (Completed)

- **Experiments:** SQLite **`experiments`** + **`experiment_runs`**; **`simulation_runs.experiment_id`** nullable FK-style tag.
- **API:** **`POST /experiments`** (sequential **`queue_simulation_run`** + **`wait_for_simulation_terminal`** per step); **`GET /experiments`**, **`GET /experiments/{id}`** with **`comparison`** (round × series metrics); **`export.json`** / **`export.zip`** including **`comparison.csv`** and per-run export bundles.
- **Runs:** **`config_snapshot.experiment`** records experiment id, step index, label; list simulations exposes **`experiment_id`**.
- **Frontend:** **Experiments** tab — **`ExperimentConsole`** (create sweep, sparklines, status, recent list, two-run ID compare).
- **Capabilities:** **`experiments`** metadata block.
- **Tests:** **`tests/test_iteration27.py`**; suite **180 passed, 1 skipped** (incl. post–27 hardening tests).
- **Closeout:** [`iteration-27-closeout.md`](iterations/iteration-27-closeout.md) (§ Post–Iteration 27 hardening).

### Iteration 26 (Completed)

- **`implementation_posture`:** Optional opaque string on `PersonaTemplate`, roster CSV, population CSV; scenario validation requires string type when present; merge uses **non-empty** roster/population cells only (empty cell keeps YAML posture).
- **`posture_maxvar`:** `sampling_strategy.py` — Tier 1 = one slot per distinct non-empty posture; remainder tiering; **no posture tags** → fallback to `role_stratified` with rationale prefix.
- **`sampling_audit`:** `build_sampling_audit_extended` adds **`role`** and **`implementation_posture`** on each **`per_agent`** row (new runs).
- **API:** `GET /simulations/{id}/sampling-report` — JSON tier/role/posture view from persisted audit; **404** / **409** (pending or running) / **400** (no audit).
- **Capabilities / planner:** `posture_maxvar` in `sampling_strategies`; `simulation_run.implementation_posture` metadata; `PlanSimulationParams` aligned.
- **Templates / YAML:** Roster + population CSV templates include `implementation_posture`; PSLE + FSBB YAML examples with ≥2 tagged personas each.
- **Frontend:** Run tab + Run metadata — link to sampling report (JSON) for **completed** / **failed** runs (`samplingReportUrl`).
- **Tests:** `tests/test_iteration26.py` — unit + API + **E2E** queued run with fake LLM (`posture_maxvar` audit + sampling-report). Full suite **164 passed, 1 skipped** (post-hardening).
- **Closeout:** [`iteration-26-closeout.md`](iterations/iteration-26-closeout.md); architect **PASS_WITH_ISSUES** follow-ups: [`HANDOFF_TO_BUILDER.md` § Post-Iteration 26 hardening](handoffs/HANDOFF_TO_BUILDER.md#post-iteration-26-hardening-pre-filled--2026-04-07).

### Iteration 18 (Completed)

- **Frontend:** **`AgentConsole`** — primary **Ask** (**`POST /agent/ask`** JSON); collapsible **execution plan** JSON after success; **Advanced** — constraints, per-run **`wait_timeout_seconds`**, optional **`plan_temperature`** / **`plan_max_tokens`**, **Plan only**, **Execute** (paste **`ExecutionPlan`** JSON); **Cancel** + elapsed timer; placeholder question; client validation on tuning fields. **`RunResultCard`** shared for Ask + Execute results.
- **`lib/api.ts`:** **`agentPlan`**, **`agentExecute`**, **`agentAsk`** + optional **`AbortSignal`** + shared types (**`ExecutionPlan`**, **`AgentRunReport`**).
- **`App.tsx`:** tab **Agent** (after **Run**).
- **Docs:** `iteration-18-closeout.md`.

### Scenario analyst wizard MVP (Iteration 13+ slice, in repo)

- **Design:** [`docs/plans/scenario-wizard-design.md`](plans/scenario-wizard-design.md) — SQLite `user_scenarios`, catalog API, validation/RAG scope, `config_snapshot` fields.
- **Backend:** `GET/POST/PUT /scenarios`, `POST /scenarios/clone`, `GET /scenarios/bundled-rag-paths`, `GET /scenarios/{id}/document`, `GET /scenarios/{id}/export.yaml`; `load_scenario_for_run` prefers user store over builtins; `config_snapshot` includes `scenario_source`, `scenario_doc_version`.
- **Frontend:** **Scenarios** tab (`ScenarioWizard`); Run tab scenario dropdown from `GET /scenarios` with builtin fallback; Vite proxy `/scenarios` → backend.
- **Tests:** `tests/test_scenario_catalog.py` (catalog + CRUD + clone + export).

### Session notes (2026-04-04, post–Iter 10)

- **Output quality:** Local models may still emit visible chain-of-thought despite user-prompt ban; long reasoning can hit **`llm_max_tokens`** and truncate mid-stream — not an orchestration bug. Thesis-facing runs: consider **hybrid / Haiku** and higher `max_tokens` after Iter **12** hardening (see chat guidance). **IAD-shaped rules of engagement** are not yet encoded in code; episodic “incoherence” vs theory is expected until interaction policy deepens.
- **Next chat:** Prefer a **fresh Cursor thread** near context limits; bootstrap with this file + `BRIEF_FOR_JOAN.md` + `iteration-10-closeout.md` + builder seed at bottom of [`HANDOFF_TO_BUILDER.md`](handoffs/HANDOFF_TO_BUILDER.md).

## Gate Evidence (Latest)

- Backend tests: **`290 passed`**, **`2 skipped`** (`uv run pytest` from `backend/`; Arc 8 economics follow-up + iter-39 integration; manual SSE + LM Studio smoke skipped)
- Frontend build: **`npm run build`** OK after **senna-iter-39** (no UI changes; build regression only)
- Frontend build: **`npm run build`** OK after **senna-iter-38** (Run setup preflight panel)
- Frontend build: **`npm run build`** OK after **senna-iter-34** (Arc 7 hardening regression)
- Frontend build: `npm run build` (`frontend/`, Vite) passed after **senna-iter-25** (a11y: `index.html` focus CSS, tab/panel ARIA, `<main>`, contrast token `#595F6B`)
- Export: `GET /simulations/{id}/export.json` uses **`export_version`: `8`** (Iteration 29: per-turn tokens, **`run.economics`**; Iteration 28: **`convergence_delta`** / **`converged_at_round`**; Iteration 23: **`fidelity_tier`**; earlier: `cohort_summary`, `attribute_sections`, per-turn LLM fields); includes **`validity_notes`**; ZIP includes **`validity_notes.csv`** and **`cohort_summary.csv`**.
- `config_snapshot` includes **`sampling_strategy`** and **`sampling_audit`** (Iteration 22+); **`per_agent`** may include **`role`**, **`implementation_posture`** (26), **`degree_centrality`** (25). Network + visibility metadata (25). Also: **`aggregation_threshold`** / **`aggregation_mode`** (20); **`llm_concurrency_cap`** (19); **`remainder_config`**, **`synthetic_remainder_count`**, **`core_agent_limit`**, **`tier_3_heuristic`** (24).
- Manual: Optional roster CSV + template URL; confirm **`config_snapshot.scale_warning`** when **`agent_limit` > 20**; confirm `cohort_summary` present in export.json; **`GET /simulations/{id}/sampling-report`** for tier/posture view (completed/failed runs).
- Sample QA run `ad901483b0a840689c71debb771cf0c1`: SQLite shows **8** turns (4 agents × 2 rounds), `simulation_mode` `full_round_robin`.

## Next Iteration Focus (post–MVP arc)

**Iteration 29** is **complete** (ship + architect review follow-ups, 2026-04-08). Convergence (**28**) + economics (**29**) are in production; **RQ2** cost columns live in **`comparison.csv`** and **`run.economics`**. **Next:** backlog or ad-hoc slices — **`HANDOFF_TO_BUILDER.md`** (strategic notes + historical starters), **`BRIEF_FOR_JOAN.md`** for UX/scale sequencing.

**Backlog:** multi-run parallelism across agent plan runs, SSE in browser, `aiosqlite` WAL + batch inserts — see [`HANDOFF_TO_BUILDER.md`](handoffs/HANDOFF_TO_BUILDER.md).

**Primary handoff for the builder (“Joan”):** [`docs/handoffs/BRIEF_FOR_JOAN.md`](handoffs/BRIEF_FOR_JOAN.md) plus [`HANDOFF_TO_BUILDER.md`](handoffs/HANDOFF_TO_BUILDER.md) for numbered iteration starters.

**Contracts / checklist:** [`docs/adr/ADR-001-iteration-10-11-contracts.md`](adr/ADR-001-iteration-10-11-contracts.md); **ADR-002** (visibility — implemented Iteration 25); [`docs/handoffs/HANDOFF_TO_ARCHITECT.md`](handoffs/HANDOFF_TO_ARCHITECT.md).

**Builder seed:** This file + latest closeout ([`iteration-29-closeout.md`](iterations/iteration-29-closeout.md)) + [`HANDOFF_TO_BUILDER.md`](handoffs/HANDOFF_TO_BUILDER.md) / [`BRIEF_FOR_JOAN.md`](handoffs/BRIEF_FOR_JOAN.md) for the next slice (no pre-filled Iteration **30** starter yet).

**Planned arc (9–12, adjustable):**

- **9** — Rosters, **groups/factions**, bulk persona import; careful `agent_limit` policy. *(Done — see `iteration-9-closeout.md`.)*  
- **10** — **Interaction model v2** + thin **AgentContext**. *(Done — `iteration-10-closeout.md`.)*  
- **11** — Population pool + deterministic sampling + provenance. *(Done — `iteration-11-closeout.md`.)*  
- **12** — Performance / parallelization sketch, stress tests, thesis fields (e.g. **effective_provider** per turn).

**Still on backlog (any iteration):** hybrid policy extensions, persona schema versioning, Opus/review follow-ups — merge with Joan’s design note.

*Starting a new Cursor chat post–Iteration 27: paste this file + `BRIEF_FOR_JOAN.md` + `iteration-27-closeout.md` + architect steering.*

## Multi-chat agent handoffs

Implementation and “architect” oversight live in **separate chats**; only **you** (or committed docs) connect them.

- **Start build work:** fill and paste [`docs/handoffs/HANDOFF_TO_BUILDER.md`](handoffs/HANDOFF_TO_BUILDER.md) in a new agent chat (include links to this file + the relevant iteration plan).
- **Return for review / next iteration:** fill [`docs/handoffs/HANDOFF_TO_ARCHITECT.md`](handoffs/HANDOFF_TO_ARCHITECT.md) and paste into the architect chat; keep `SESSION_STATE.md` and `docs/iterations/iteration-*-closeout.md` updated so any chat can cold-start.
- **Index:** [`docs/handoffs/README.md`](handoffs/README.md)

Same pattern as Opus review: **no automatic agent-to-agent channel**—scheduled handoffs via templates + repo state.

## End-of-Iteration Update Checklist

At each gate, update this file and add one iteration note under `docs/iterations/`.

Required updates:

1. Update `Current Status` (active phase, last completed gate, date).
2. Add a short bullet list under `Completed Work` for the new iteration.
3. Replace `Gate Evidence (Latest)` with actual outputs:
   - tests/build result
   - run id/status/rounds
   - export file paths
4. Set `Next Iteration Focus` to the next planned scope.

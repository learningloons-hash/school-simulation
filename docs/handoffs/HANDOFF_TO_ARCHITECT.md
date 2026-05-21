# Handoff to architect

**Senna cycle (GM vs Architect vs Builder; max five iterations per arc):** [`SENNA_AGENT_CYCLE.md`](./SENNA_AGENT_CYCLE.md). **After GM arc PASS:** commit and `git push origin main` per [`SENNA_AGENT_CYCLE.md`](./SENNA_AGENT_CYCLE.md) § *Git push after arc close*.

## Current focus — Senna Arc 8 / Model Ecosystem and Guardrails

**Status:** **Senna Arc 8 CLOSED — GM final PASS** (2026-05-19). Gates `senna-iter-35`–`39` **PASS**; economics follow-up **PASS**. Suite **290 passed, 2 skipped**.

**Recommended next priority:** Await GM `HANDOFF_SENNA_ARC9.md` (if any) or thesis backlog per [`HANDOFF_TO_BUILDER.md`](HANDOFF_TO_BUILDER.md). Do **not** start a new arc without GM handoff.

**Builder entry:** [`SESSION_STATE.md`](../SESSION_STATE.md) + thesis backlog in [`HANDOFF_TO_BUILDER.md`](HANDOFF_TO_BUILDER.md).

**Still in backlog:** Multi-run parallelism in agent orchestrator; scenario marketplace; MEETING group scoping (Iteration 15 note); SSE in browser; `aiosqlite` WAL + batch inserts (>200-agent).

**Senna:** **Arc 8** (*Model Ecosystem and Guardrails*) **GM PASS** (2026-05-19). **Arc 7** **GM PASS**. **Arc 6**–**5** closed.

---

## Senna Arc 8 — planned sign-off record (model ecosystem and guardrails)

| Gate | Theme | Closeout | Architect |
|------|-------|----------|-----------|
| **senna-iter-35** | Planner parity, Arc 7 cleanup, Tier-3 provenance sentinel | [`senna-iter-35-closeout.md`](../iterations/senna-iter-35-closeout.md) | PASS (2026-05-19) |
| **senna-iter-36** | Profile registry + model capability registry | [`senna-iter-36-closeout.md`](../iterations/senna-iter-36-closeout.md) | PASS (2026-05-19) |
| **senna-iter-37** | Commercial OpenAI-compatible profiles + optional auth | [`senna-iter-37-closeout.md`](../iterations/senna-iter-37-closeout.md) | PASS (2026-05-19) |
| **senna-iter-38** | Pre-run context/cost checks + Run setup warnings | [`senna-iter-38-closeout.md`](../iterations/senna-iter-38-closeout.md) | PASS (2026-05-19) |
| **senna-iter-39** | Structured-output reliability + Arc 8 integration validation | [`senna-iter-39-closeout.md`](../iterations/senna-iter-39-closeout.md) | PASS (2026-05-19) |

**Senna Arc 8 — Cursor gates:** **complete** (iter 35–39 **PASS**, 2026-05-19). **GM follow-up:** **PASS** (2026-05-19) — `resolve_billing_provider_key` + `test_senna_arc8_economics.py`; see [`senna-iter-39-closeout.md`](../iterations/senna-iter-39-closeout.md) § Post–GM.

**GrandMaster:** initial **PASS_WITH_ISSUES** (economics) — follow-up **PASS** — **final arc PASS** (2026-05-19).

### Senna Arc 8 — Architect summary for GrandMaster

| # | `HANDOFF_SENNA_ARC8.md` § Arc 8 Definition of Complete | Evidence |
|---|--------------------------------------------------------|----------|
| 1 | Gates `senna-iter-35`–`39` PASS | Sign-off table above; closeouts `senna-iter-35` … `senna-iter-39` |
| 2 | Planner `model_profile_id` parity | iter-35; `test_iteration17` execute_plan forward |
| 3 | Registry-derived profile ids | iter-36; `BUILTIN_PROFILE_IDS` from registry |
| 4 | Capabilities in `/capabilities` + snapshot | iter-36–37; capability blocks on profiles |
| 5 | Commercial OpenAI-compatible profiles (mock-tested) | iter-37; `openai_default`, `openrouter_default`, bearer auth |
| 6 | Pre-run context/cost warnings (API + Run UI) | iter-38; `preflight.py`, `POST /simulations/preflight` |
| 7 | Structured-output provenance in exports | iter-39; `state_update_source` on poll/export/ZIP |
| 8 | Tier-3 non-null provenance | iter-35 `effective_profile_id=heuristic`; iter-39 integration test |

**What landed well:** Registry + commercial profiles on one adapter; preflight before run; auditable `<state>` parsing (`model_parsed` / `repaired` / `keyword_fallback`); consolidated `test_senna_arc8_integration.py`.

**Accepted deferrals:** No live LM Studio in CI (`scripts/lmstudio_profile_smoke.py` + manual marker); Tier-3 `state_update_source` null (state applied post-round via heuristic — profile provenance on `effective_profile_id`); cost/context estimates remain heuristic.

---

## Senna Arc 7 — sign-off record (model portability)

| Gate | Theme | Closeout | Architect |
|------|-------|----------|-----------|
| **senna-iter-30** | Generic OpenAI-compatible provider; keep `lmstudio` compatibility alias | [`senna-iter-30-closeout.md`](../iterations/senna-iter-30-closeout.md) | PASS (2026-05-19) |
| **senna-iter-31** | Model profiles + `model_profile_id`; legacy `llm_provider` preserved | [`senna-iter-31-closeout.md`](../iterations/senna-iter-31-closeout.md) | PASS (2026-05-19) |
| **senna-iter-32** | `/capabilities` model profiles + simple frontend profile selector | [`senna-iter-32-closeout.md`](../iterations/senna-iter-32-closeout.md) | PASS (2026-05-19) |
| **senna-iter-33** | Data-driven routing policies preserving current hybrid behavior | [`senna-iter-33-closeout.md`](../iterations/senna-iter-33-closeout.md) | PASS (2026-05-19) |
| **senna-iter-34** | Compatibility, export/economics provenance, build/test hardening | [`senna-iter-34-closeout.md`](../iterations/senna-iter-34-closeout.md) | PASS (2026-05-19) |

**Senna Arc 7 — complete.** GM final verdict: **PASS** (2026-05-19). Arc 8 handoff issued: [`HANDOFF_SENNA_ARC8.md`](HANDOFF_SENNA_ARC8.md).

### Senna Arc 7 — Architect summary for GrandMaster

| # | `HANDOFF_SENNA_ARC7.md` § Arc 7 Definition of Complete | Evidence |
|---|--------------------------------------------------------|----------|
| 1 | Gates `senna-iter-30`–`34` PASS | Sign-off table above; closeouts `senna-iter-30` … `senna-iter-34` |
| 2 | Legacy `llm_provider` preserved | `test_senna_arc7_hardening.py` parametrized queue + E2E hybrid |
| 3 | `model_profile_id` authoritative when used alone | `resolve_run_llm_provider`; `test_post_run_anthropic_profile_only_infers_provider`; `test_queue_anthropic_profile_only_overrides_server_default_lmstudio` |
| 4 | `GET /capabilities` → `model_profiles` | iter-32 + `test_capabilities_model_profiles_after_arc7` |
| 5 | Frontend capability-driven selector + fallback | iter-32; `npm run build` green |
| 6 | Hybrid behavior unchanged | iter-33 + hardening `test_post_run_hybrid_legacy_provider_provenance` |
| 7 | Export/transcript provenance | hardening `_assert_export_provenance` (JSON/ZIP, economics, tokens) |

**What landed well:** Thin adapter refactor (iter-30), profile layer without breaking API (iter-31), capabilities-driven Run setup (iter-32), named routing policies + `effective_profile_id` (iter-33), consolidated hardening suite (iter-34).

**GM issue closed (2026-05-19):** Profile-only POST no longer falls through to server `lmstudio` when `model_profile_id=anthropic_default`.

**Accepted deferrals:** No live LM Studio in CI (mocked E2E); Agent `PlanSimulationParams` still omits `model_profile_id` (UI path uses `POST /simulations/run` only). Arc 8 owns new commercial presets per GM preview in Arc 7 handoff.

---

## Senna Arc 6 — sign-off record (backend)

| Gate | Theme | Closeout | Architect |
|------|-------|----------|-----------|
| **senna-iter-26** | `round_summaries` schema + repo + `llm/round_summary.py` + tests; post-26 hardening: Iter17 `test_agent_plan_mock_llm` mock path | [`senna-iter-26-closeout.md`](../iterations/senna-iter-26-closeout.md) | PASS (2026-04-26) |
| **senna-iter-27** | Orchestrator wiring, `build_user_prompt` + `round_summaries`, `interaction_last_k` cap 12, settings plumbing | [`senna-iter-27-closeout.md`](../iterations/senna-iter-27-closeout.md) | PASS (2026-04-26) |
| **senna-iter-28** | `.md` transcript writer + orchestrator wiring | [`senna-iter-28-closeout.md`](../iterations/senna-iter-28-closeout.md) | PASS (2026-04-26) |
| **senna-iter-29** | Config + tests confirmation (`test_senna_arc6_config`, `test_round_summary`, `test_transcript_writer`); `npm run build` for Arc 6 DoD | [`senna-iter-29-closeout.md`](../iterations/senna-iter-29-closeout.md) | PASS (2026-04-26) |

**Senna Arc 6 — complete.** Optional Cowork **Arc 6** review per [`CLAUDE.md`](../../CLAUDE.md). **Next (product):** thesis backlog + [`SESSION_STATE.md`](../SESSION_STATE.md). **Thesis** **Iteration 27** = experiments — [`iteration-27-closeout.md`](../iterations/iteration-27-closeout.md) (not Senna’s counter).

---

## Senna Arc 5 — sign-off record (frontend)

| Gate | Theme | Closeout | Architect |
|------|-------|----------|-----------|
| **senna-iter-21** | `theme.ts` + `RunResultCard` polish (tokens, pills, merged warnings, no `<code>` / off-palette in card) | [`senna-iter-21-closeout.md`](../iterations/senna-iter-21-closeout.md) | PASS (2026-04-22) |
| **senna-iter-22** | Typography + numeric formatting (`FONT.mono` on Results / Compare / Live tables; Run Details + Quality notes headings; Part C spacing) | [`senna-iter-22-closeout.md`](../iterations/senna-iter-22-closeout.md) | PASS (2026-04-22) |
| **senna-iter-23** | Tab bar: scroll strip, hidden scrollbars, fade, `PRIMARY_TABS` / `SECONDARY_TABS`, `tablist` + `tab` ARIA, refined `tabStyle` | [`senna-iter-23-closeout.md`](../iterations/senna-iter-23-closeout.md) | PASS (2026-04-22) |
| **senna-iter-24** | Empty states (Watch Live / Conversation / Compare), controlled run ID load, `ConversationView` guard, convergence banner spacing | [`senna-iter-24-closeout.md`](../iterations/senna-iter-24-closeout.md) | PASS (2026-04-22) |
| **senna-iter-25** | A11y: `:focus-visible` in `index.html`, tab `id` / `aria-controls` / `tabpanel` / `aria-labelledby`, `<main>`, `aria-label`s, `COLOR.textSecondary` `#595F6B`, `CLAUDE.md` Arc 5 closed | [`senna-iter-25-closeout.md`](../iterations/senna-iter-25-closeout.md) | PASS (2026-04-22) |

**Senna Arc 5 — Cursor gates:** complete (all iterations **PASS**). **Senna Arc 6:** complete — see table above.

**Next (post–Arc 6):** optional Cowork **Arc 5** / **Arc 6** UX or backend recaps; thesis backlog [`HANDOFF_TO_BUILDER.md`](HANDOFF_TO_BUILDER.md) + [`SESSION_STATE.md`](../SESSION_STATE.md).

---

## Senna Arc 4 — sign-off record (frontend)

| Gate | Theme | Closeout | Architect |
|------|-------|----------|-----------|
| **senna-iter-16** | Assistant tab: plain-English copy, `sectionHeadingStyle`, palette borders; no API/behaviour change | [`senna-iter-16-closeout.md`](../iterations/senna-iter-16-closeout.md) | PASS |
| **senna-iter-17** | Compare Runs: strategy + metric display maps, `shortStatusLabel`, token/cost lines aligned with Run Details; `<select>` values unchanged | [`senna-iter-17-closeout.md`](../iterations/senna-iter-17-closeout.md) | PASS (2026-04-22) |
| **senna-iter-18** | Quality Notes tab: plain-English labels; saved-note display; payloads unchanged | [`senna-iter-18-closeout.md`](../iterations/senna-iter-18-closeout.md) | PASS (2026-04-22) |
| **senna-iter-19** | Policy Scenarios wizard: plain labels, step chrome, message panels, palette borders; functionality preserved | [`senna-iter-19-closeout.md`](../iterations/senna-iter-19-closeout.md) | PASS (2026-04-22) |
| **senna-iter-20** | Final sweep: ConversationView label, run list copy, redundant tab `<h2>`s removed, `App.tsx` palette fixes, `CLAUDE.md` Arc 4 closed | [`senna-iter-20-closeout.md`](../iterations/senna-iter-20-closeout.md) | PASS (2026-04-22) |

### Senna Arc 4 — Opus arc review *(complete)*

- **Cowork / Opus verdict (2026-04-22):** **PASS** — all five gates shipped clean; builds green throughout. **No required follow-ups.**
- **What landed well (Opus):** metric/strategy maps in `ExperimentConsole`; thorough `ScenarioWizard` cleanup without behaviour change; Quality Notes translation (Realism / Accuracy / Predictive).
- **Deferred (accepted for Arc 5):** `coral` / `#a30` / `#a60` may remain in `AgentConsole` and `RunResultCard` — iter-20 scoped palette pass to `App.tsx` only; global visual pass is Arc 5 scope.
- **Evidence:** [`HANDOFF_SENNA_ARC4.md`](HANDOFF_SENNA_ARC4.md) § *Definition of Arc Complete*; [`docs/SESSION_STATE.md`](../SESSION_STATE.md); [`CLAUDE.md`](../../CLAUDE.md); closeouts `senna-iter-16` … `senna-iter-20`.

---

## Iteration 27 — sign-off record (condensed)

| Theme | Outcome |
|-------|---------|
| **Persistence** | `experiments`, `experiment_runs`, `simulation_runs.experiment_id`. |
| **API** | Sequential child runs; `comparison` matrix; experiment export JSON/ZIP. |
| **UI** | Experiments tab replaces standalone Compare; run list shows `experiment_id` hint. |
| **Tests** | `tests/test_iteration27.py` (incl. post-27: failure path, dedupe, `run_count`). |

---

## Iteration 28 — sign-off record (condensed)

| Theme | Outcome |
|-------|---------|
| **Convergence** | `convergence_threshold` / `convergence_patience`; `convergence_delta` in timeline + DB; `converged_at_round`; export v7. |
| **Post–28** | Experiments + agent orchestrator + comparison CSV/UI; streak-reset + E2E tests; defensive delta when `prev` missing. |
| **Tests** | `tests/test_iteration28.py`; suite **186 passed, 1 skipped**. |

---

## Iteration 29 — sign-off record (condensed)

| Theme | Outcome |
|-------|---------|
| **Tokens** | Per-turn + run totals; `LLMCompletion` usage from LM Studio / Anthropic when returned. |
| **Economics** | `estimated_cost_usd`, `tier_breakdown`; `GET /simulations/{id}`, export `run.economics`, experiments + `comparison.csv`. |
| **Export** | **`export_version` `8`**; `agent_turns.csv` token columns. |
| **Tests** | `tests/test_iteration29.py` (incl. pure-function + anthropic pricing); suite **191 passed, 1 skipped**. |

---

## Iteration 25 — sign-off record (condensed)

| Theme | Outcome |
|-------|---------|
| **Network CSV** | `parse_network_csv`; unknown agent ids → warnings; `degree_centrality`, `undirected_neighbor_map`. |
| **Sampling** | `network_centrality` strategy; requires non-empty CSV. |
| **Visibility** | `visible_turns_for_agent` + `effective_visibility`, `network_neighbors`, `round_speaker_ids`. |
| **Config** | `network_*`, `interaction_visibility`, `visibility_effective`, `network_visibility_fallback`. |
| **Tests** | `tests/test_iteration25.py` + Iteration 15 policy tests; post-25: E2E queue + **`network_node_count`**, capabilities **`full`** filter, **`round_participants_only`** broadcast. |

---

## Iteration 23 — sign-off record (condensed)

| Theme | Outcome |
|-------|---------|
| **Tier 1** | Unchanged full `build_system_prompt` + LLM path (regression baseline). |
| **Tier 2** | `simplified_persona_prompt`; `peer_context_max_chars // 2` for memory + recent interactions. |
| **Tier 3** | No `llm_complete`; marker response; `heuristic` / `none`; `latency_ms` 0; state copy placeholder. |
| **Persistence / export** | `fidelity_tier` on `agent_turns`; poll + export bundle; **`export_version` `6`**. |
| **UI** | Transcript shows fidelity tier. |
| **Tests** | `tests/test_iteration23.py` (3); full suite **149 passed, 1 skipped**. |

---

## Iteration 26 — sign-off record (condensed)

| Theme | Outcome |
|-------|---------|
| **`implementation_posture`** | Optional opaque string on `PersonaTemplate`, roster CSV, population CSV; validated as string in scenario YAML. |
| **`posture_maxvar`** | Tier 1 diversity across distinct non-empty postures; remainder tiering; falls back to `role_stratified` when no tags. |
| **Report** | `GET /simulations/{id}/sampling-report` reshapes `config_snapshot.sampling_audit`; `centrality` populated when network present (**Iteration 25**). |
| **Audit** | `per_agent` enriched with `role`, `implementation_posture`. |
| **Tests** | `tests/test_iteration26.py` (**11**); suite **164 passed, 1 skipped** (includes queued-run E2E). |
| **Post-26 hardening** | SESSION_STATE + integration test + roster comment + frontend sampling-report link (2026-04-07). |

---

## Iteration 22 — sign-off record (condensed)

| Theme | Outcome |
|-------|---------|
| **`sampling_strategy`** | `SimulationRunRequest` + `PlanSimulationParams`; `full_census` (default, backward compatible) \| `role_stratified`. |
| **Tier assignment** | `simulation/sampling_strategy.py` — roles from scenario YAML only; roster `fidelity_tier` overrides per slot. |
| **Audit** | `config_snapshot.sampling_strategy` + `sampling_audit` (`tier_counts`, `per_agent`, optional `scenario_roles_not_represented`). |
| **Runtime** | `AgentInstance.fidelity_tier` populated; execution unchanged (Iter 23). |
| **Capabilities / planner** | `sampling_strategies`, `fidelity_tiers`; planner JSON + validation. |
| **Pre–Iter 23** | Same-role degenerate + `scenario_roles_not_represented` tests (architect review). |
| **Tests** | `tests/test_iteration22.py` (**12**); full suite **146 passed, 1 skipped**. |

---

## Iteration 21 — sign-off record (condensed)

| Theme | Outcome |
|-------|---------|
| **`initial_state`** | Optional per-persona YAML → `PersonaTemplate.initial_state`; orchestrator `_initial_state_from_persona`; neutral defaults when absent. |
| **Removed hardcoding** | `_initial_state_for_role` deleted; PSLE/FSBB YAML + embedded FSBB carry explicit `initial_state` matching legacy values. |
| **Demographics** | `_build_demographics(role_level, idx)` — no role-name strings; ethnicity/ses `unspecified`; age matches legacy 49/41/33 for levels 1–3; **clamp** for high `role_level` (no negative ages). |
| **Authoring** | `scenarios_generate.py` domain-agnostic; `validate.py` positive-integer `role_level`; **`initial_state`** object + numeric **warnings/errors** for support/resistance/workload. |
| **Docs / capabilities** | `docs/domain-packs.md`; `interaction_policy.py` overlay framing + generic module turn-order bullet; `export_version` **5** in `build_capabilities_dict()`. |
| **Tests** | `tests/test_iteration21.py` (9); **`test_iteration16`** capabilities assertion → v5; suite **134 passed, 1 skipped**. |

---

## Iteration 20 — sign-off record (condensed)

| Theme | Outcome |
|-------|---------|
| **`agent_limit` ceiling** | Raised to 200 in `SimulationRunRequest` and `PlanSimulationParams`; `speakers_per_round` raised to 200 as well. |
| **`aggregation_threshold`** | New field (default 20, 1–200) on `SimulationRunRequest` and `PlanSimulationParams`. `config_snapshot` gains `aggregation_threshold` and `aggregation_mode` (`True` when `agent_limit >= aggregation_threshold`). |
| **`compute_cohort_summary`** | Pure function in `export_bundle.py`. Groups `agent_state_snapshots` by `(group_id, round_number)`; computes `agent_count`, `spoke_count`, `avg_support_level`, `avg_resistance_level`, `avg_workload_stress`. Agents with no `group_ids` aggregate under `""`. No new DB query. |
| **Export version 5** | `export.json` → `"export_version": "5"`, `"cohort_summary": [...]`. ZIP → `cohort_summary.csv` added. |
| **Capabilities** | `"agent_limit": {default:3, min:1, max:200}` and `"aggregation_threshold": {default:20, min:1, max:200}` under `"simulation_run"`. |
| **Agent orchestrator** | `aggregation_threshold` forwarded through `PlanSimulationParams` → `_simulation_run_request`; planner JSON shape updated. |
| **Tests** | 8 new tests in `tests/test_iteration20.py`; full suite **125 passed, 1 skipped**. |
| **Feasibility note** | `docs/plans/scale-feasibility-500-agent.md` — turn counts, wall-clock projections, Anthropic cost table, DB limits, recommended configs per tier. |

---

## Iteration 19 — sign-off record (condensed)

| Theme | Outcome |
|-------|---------|
| **Parallel LLM** | `asyncio.gather` + `asyncio.Semaphore(llm_concurrency_cap)` within rounds; rounds remain sequential. |
| **Pre-assignment** | `turn_assignments = list(enumerate(round_agents, start=1))` before gather; `turn_index`, interaction plan, and `interaction_last_k` all deterministic. |
| **Error isolation** | LLM errors → `[LLM error] …` string (caught inside `_run_one_turn`); `return_exceptions=True` catches escaping errors; failing turn logged, round continues. |
| **Config** | `LLM_CONCURRENCY_CAP` env (default 4); `SimulationRunRequest.llm_concurrency_cap` (1–16, optional); `config_snapshot["llm_concurrency_cap"]`. |
| **Tests** | 7 new tests in `tests/test_iteration19.py`; full suite **117 passed, 1 skipped**. |

---

## Iteration 17 — sign-off record (condensed)

| Theme | Outcome |
|-------|---------|
| **API** | **`/agent/plan`**, **`/agent/execute`**, **`/agent/ask`**; ask supports **`stream=true`** (SSE). |
| **Orchestration** | **`agent/orchestrator.py`** — plan LLM → validate vs capabilities → execute steps sequentially. |
| **Run path** | **`queue_simulation_run`** shared with **`POST /simulations/run`**; **`wait_for_simulation_terminal`** + **`get_simulation_run_status_only`**. |
| **Capabilities** | **`build_capabilities_dict()`** — single source for HTTP + planner prompts. |
| **Tests / demo** | **`tests/test_iteration17.py`** (incl. generate **`HTTPException`** resilience + temperature forwarding); **`@pytest.mark.manual`** SSE placeholder; **`scripts/agent_ask_demo.py`**. |
| **Architect follow-ups** | Per-step errors from generate/queue no longer abort multi-run plans; **`plan_temperature`** 0–2; timeout semantics documented; builder handoff PASS items 2–4 marked addressed in **`HANDOFF_TO_BUILDER.md`**. |

---

## Iteration 18 — sign-off record (condensed)

| Theme | Outcome |
|-------|---------|
| **UI** | **Agent** tab; **`AgentConsole`** — Ask primary; Advanced → Plan only + Execute JSON + tuning fields. |
| **Client** | **`agentAsk`**, **`agentPlan`**, **`agentExecute`** in **`frontend/src/lib/api.ts`**. |
| **SSE** | Not wired in UI; JSON mode only for MVP ( **`curl`** / future slice). |

---

## Iteration 13 — sign-off record (condensed) *(historical)*

| Theme | Outcome |
|-------|---------|
| **Contract** | **`identity`**, **`attitudes`**, **`personal_history`** shallow dicts on context; **`AGENT_CONTEXT_VERSION` `"2"`**; **`config_snapshot.agent_context_version` `"2"`**. |
| **Sources** | Scenario YAML personas; optional population **`identity_json`** / **`attitudes_json`** / **`personal_history_json`** (**`population_schema_version` `2`**). |
| **Prompts** | New labeled blocks in **`build_system_prompt`** when sections non-empty. |
| **Persistence** | **`agent_state_snapshots.attribute_sections_json`**; poll **`state_timeline[].agents[].attribute_sections`**. |
| **Export** | **`export_version` `4`**; CSV stringifies **`attribute_sections`** dict for snapshots. |

---

## Deviation from original Iteration 12 brief (paper trail)

The Joan brief table described Iteration 12 as including a **“batching/queue sketch or parallel calls (if aligned with model).”** **That item was deferred:** the engine still runs **sequential** LLM calls per turn. **Parallel/batch LLM** remains a forward-plan slice when architect approves cost/latency tradeoffs.

---

## Open questions (Iteration 21+)

- **Agent UI:** keep ask-first + Advanced vs promote **Plan** / **Execute** to top-level tabs after user review.
- **SSE** in browser for **`/agent/ask?stream=true`** vs JSON-only.
- **Cancel / timeout** UX for long **`/agent/ask`** (client-only vs future server abort).
- **ADR-002** interaction visibility — **shipped** in Iteration 25 (`network_bounded`, `round_participants_only`, etc.).
- **Multi-run parallelism** in agent orchestrator: parallel runs across `ExecutionPlan.runs` steps (currently sequential).
- **`aiosqlite` WAL mode + batch inserts**: needed before >200-agent runs see write contention; noted in `scale-feasibility-500-agent.md`.
- **500-agent ceiling**: `agent_limit` beyond 200 requires API change + WAL mode; tracked in feasibility note.

---

## Requested architect actions

- [x] Sign off **Iteration 13** — **Approved** (historical; see condensed table above).
- [x] Iterations **14–17** — shipped in repo (see respective **`iteration-*-closeout.md`** and **`HANDOFF_TO_BUILDER.md`** architect review section).
- [x] **Iteration 17** architect PASS non-blocking items **2–4** implemented or documented (see **`iteration-17-closeout.md`** § *Architect review — follow-ups applied*).
- [x] **Iteration 18** (Minister / Agent UI) — shipped ask-first + Advanced (**`iteration-18-closeout.md`**).
- [x] **Iteration 19** (parallel LLM within rounds) — `asyncio.gather` + semaphore; 117 tests passing (**`iteration-19-closeout.md`**).
- [x] **Iteration 20** (population scale + cohort aggregation) — `agent_limit` 200; `compute_cohort_summary`; export_version 5; 125 tests passing (**`iteration-20-closeout.md`**).
- [x] **Iteration 21** (generic engine cleanup) — YAML `initial_state`, demographics/prompts/validation; 131 tests passing (**`iteration-21-closeout.md`**).
- [x] **Iteration 22** (sampling strategy contract — metadata) — shipped; see **`iteration-22-closeout.md`**.
- [x] **Iteration 23** (tier-aware orchestrator) — shipped; see **`iteration-23-closeout.md`**.
- [x] **Iteration 24** (Tier-3 heuristic + scale) — shipped; **`iteration-24-closeout.md`**.
- [x] **Iteration 26** (`posture_maxvar` + sampling report) — shipped; **`iteration-26-closeout.md`**.
- [x] **Iteration 25** (network + ADR-002 visibility) — shipped; **`iteration-25-closeout.md`**.
- [x] **Iteration 27** (experiments framework) — shipped; **`iteration-27-closeout.md`**.
- [x] **Iteration 28** (convergence stopping criterion) — shipped; **`iteration-28-closeout.md`**; architect review **PASS_WITH_ISSUES**; **post–28 hardening** closed 2026-04-08 — [`review-iteration-28.md`](../reviews/review-iteration-28.md).
- [x] Post-28 hardening — experiments + agent orchestrator + tests + comparison UI/CSV (see closeout § Post–28).
- [x] **Iteration 29** (run economics) — shipped; **`iteration-29-closeout.md`** (2026-04-08); architect **PASS** + review follow-ups — [`review-iteration-29.md`](../reviews/review-iteration-29.md) § *Follow-up resolution*.
- [x] **Senna senna-iter-16** (Assistant / `AgentConsole`) — shipped 2026-04-22; [`senna-iter-16-closeout.md`](../iterations/senna-iter-16-closeout.md).
- [x] **Senna senna-iter-17** (Compare Runs / `ExperimentConsole`) — shipped 2026-04-22; [`senna-iter-17-closeout.md`](../iterations/senna-iter-17-closeout.md).
- [x] **Senna senna-iter-18 → senna-iter-20** — Arc 4 shipped; Cowork **PASS** (2026-04-22); see Arc 4 sign-off table above.
- [x] **Senna senna-iter-26** (Arc 6) — `round_summaries` + `round_summary.py`; [`senna-iter-26-closeout.md`](../iterations/senna-iter-26-closeout.md) (2026-04-26).
- [x] **Senna senna-iter-27** (Arc 6) — orchestrator + prompts; [`senna-iter-27-closeout.md`](../iterations/senna-iter-27-closeout.md) (2026-04-26).
- [x] **Senna senna-iter-28** (Arc 6) — `transcript_writer` + orchestrator; [`senna-iter-28-closeout.md`](../iterations/senna-iter-28-closeout.md) (2026-04-26).
- [x] **Senna senna-iter-29** (Arc 6) — config + test confirmation; [`senna-iter-29-closeout.md`](../iterations/senna-iter-29-closeout.md) (2026-04-26). **Arc 6** closed.
- [ ] Next numbered **backend** slice or backlog: parallel experiment + agent-plan runs; SSE-in-UI; WAL mode; real-time cost ticker.

---

## Builder next seed

Use **`SESSION_STATE.md`** + **`HANDOFF_TO_BUILDER.md`** for the next gate. **Senna Arc 6 (backend) — done** — reference [`HANDOFF_SENNA_ARC6.md`](HANDOFF_SENNA_ARC6.md) and closeouts `senna-iter-26`–`29` only for audits or Cowork review. **Senna UX (Arc 5, done):** **`HANDOFF_SENNA_ARC5.md`**. **Thesis / other backend:** historical starters in this file.

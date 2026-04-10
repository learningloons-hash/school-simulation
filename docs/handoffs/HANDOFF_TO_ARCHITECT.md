# Handoff to architect

## Current focus — Post–29 backlog + next slice

**Status:** **Iteration 29** (run economics) **closed** — architect **PASS**; review follow-ups applied (2026-04-08). See [`docs/reviews/review-iteration-29.md`](../reviews/review-iteration-29.md) § *Follow-up resolution*. Suite **191 passed, 1 skipped**. Platform gaps for the thesis study (convergence + economics) are closed.

**Recommended next priority (builder / architect):** Thesis scenario prep (Full SBB YAML, Trinidad agent profiles, validation benchmark), or backlog per [`SESSION_STATE.md`](../SESSION_STATE.md) + [`HANDOFF_TO_BUILDER.md`](HANDOFF_TO_BUILDER.md). Backlog: **parallel experiment dispatch**, **SSE-in-browser**, **`aiosqlite` WAL + batch inserts**, **real-time cost ticker**.

**Builder entry:** [`SESSION_STATE.md`](../SESSION_STATE.md) + latest closeout + [`HANDOFF_TO_BUILDER.md`](HANDOFF_TO_BUILDER.md) strategic notes. Contracts: [`ADR-001`](../adr/ADR-001-iteration-10-11-contracts.md); **ADR-002** (Iteration 25).

**Still in backlog:** Multi-run parallelism in agent orchestrator; scenario marketplace; MEETING group scoping (Iteration 15 note); SSE in browser; `aiosqlite` WAL + batch inserts (>200-agent).

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
- [ ] Next numbered slice or backlog: parallel experiment + agent-plan runs; SSE-in-UI; WAL mode; real-time cost ticker.

---

## Builder next seed

Use **`SESSION_STATE.md`** + **`HANDOFF_TO_BUILDER.md`** for the next builder gate. Refresh this file after that gate.

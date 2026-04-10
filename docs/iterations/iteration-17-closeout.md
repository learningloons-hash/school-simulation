# Iteration 17 closeout — Agent orchestration layer

**Date:** 2026-04-05  
**Status:** Shipped

## Shipped

### 1. In-process orchestration (`mirofish_backend/agent/orchestrator.py`)

- **`llm_build_execution_plan`** — planner LLM receives **`build_capabilities_dict()`** JSON (same as `GET /capabilities`); returns **`ExecutionPlan`**; validates with **`validate_plan_against_capabilities`** before accept.
- **`execute_plan`** — for each **`PlanRunStep`**: optional **`generate_scenario_from_brief`** + **`upsert_user_scenario`**; **`queue_simulation_run`**; **`wait_for_simulation_terminal`**; on **`completed`**, **`analyze_simulation_export`**. Optional **`emit`** hook for SSE progress.
- **Models:** **`PlanSimulationParams`**, **`PlanRunStep`** (exactly one of **`scenario_id`** / **`scenario_brief`**), **`ExecutionPlan`** (1–8 runs).

### 2. HTTP API (`api/agent.py`)

- **`POST /agent/plan`** — `{ question, constraints?, plan_max_tokens?, plan_temperature? }` → `{ plan }` (planner temperature defaults to **0.35** if omitted; range **0–2**).
- **`POST /agent/execute`** — body **`ExecutionPlan`** JSON → `{ runs: [...] }` (per-run status, queue warnings, analysis or **`analysis_error`**). **`HTTPException`** from **`generate_scenario_from_brief`** or **`queue_simulation_run`** is caught per step (**`generate_failed`** / **`queue_failed`**) so later runs still execute.
- **`POST /agent/ask`** — `{ question, constraints?, plan_max_tokens?, plan_temperature?, wait_timeout_seconds? }`; **`wait_timeout_seconds`** applies **per run** (each step waits up to that long; multi-run JSON can add up to a long wall-clock). **`stream=false`** (default) → JSON **`{ plan, runs }`**; **`stream=true`** → **SSE** (`plan_ready`, execute **`emit`** events, **`final`** or **`error`**). **`response_model=None`** on ask route (JSON vs stream union).

### 3. Simulation queue refactor (`api/simulations.py`)

- **`queue_simulation_run(settings, SimulationRunRequest)`** — shared by **`POST /simulations/run`** and orchestrator (no duplicated run logic).
- **`wait_for_simulation_terminal`** — polls **`get_simulation_run_status_only`** until **`completed`** / **`failed`** or timeout.

### 4. Repo + capabilities

- **`get_simulation_run_status_only`** — lightweight status row for waits.
- **`build_capabilities_dict()`** in **`api/capabilities.py`** — **`GET /capabilities`** delegates to it for single source of truth.

### 5. Wiring

- **`main.py`** — **`agent_router`** registered.
- **`frontend/vite.config.ts`** — dev proxy **`/agent`**.

### 6. Tests + demo script

- **`backend/tests/test_iteration17.py`** — capability validation, execute + plan + ask with mocks, invalid plan **422**, per-step resilience after generate **`HTTPException`**, planner temperature forwarded to **`llm_complete`**; **`@pytest.mark.manual`** placeholder for SSE (see **Manual SSE check**).
- **`scripts/agent_ask_demo.py`** — urllib one-liner against **`POST /agent/ask`** (needs live backend + LLM).

## Definition of done (handoff)

- [x] All three **`/agent/*`** endpoints implemented and tested.
- [x] SSE path for **`/agent/ask?stream=true`** (async queue + background task; not fully stress-tested in CI — sync **`TestClient.stream`** hung in local experiment; manual check with curl recommended).
- [x] Orchestrator uses **`queue_simulation_run`**, **`generate_scenario_from_brief`**, **`analyze_simulation_export`** — no duplicated simulation engine logic.
- [x] Planner prompt embeds **`build_capabilities_dict()`** output.
- [x] Demo script for one English sentence → **`/agent/ask`**.
- [x] **`pytest`** passes; **`npm run build`** passes.
- [x] This closeout + **`SESSION_STATE.md`** updated.
- [x] **`HANDOFF_TO_ARCHITECT.md`** reflects Iteration **17** gate + follow-ups.

## Architect review — follow-ups applied (post PASS)

Aligned with **`HANDOFF_TO_BUILDER.md`** § *Iteration 17 — PASS*:

- **Per-step `HTTPException`:** generate + upsert and queue wrapped in **`orchestrator.execute_plan`** → **`scenario_generate_failed`** / **`run_queue_failed`** events; run rows **`generate_failed`** / **`queue_failed`** with **`analysis_error`**; execution **continues** for remaining steps.
- **Planner temperature:** optional **`plan_temperature`** on **`AgentPlanRequest`** and **`AgentAskRequest`** (0–2; omit → **0.35**), forwarded to **`llm_build_execution_plan`** / **`llm_complete`**.
- **`wait_timeout_seconds`:** documented as **per run** for JSON **`/agent/ask`** (wall-clock sums across steps).
- **SSE in CI:** **`pytest.mark.manual`** + registered marker in **`backend/pyproject.toml`**; primary verification remains **`curl`** (see below).

## Manual SSE check

```bash
curl -N -X POST "http://127.0.0.1:8100/agent/ask?stream=true" \
  -H "Content-Type: application/json" \
  -d '{"question":"Plan and run a 1-round PSLE reform simulation and summarize."}'
```

## Deferred

- Minister UI (Iteration 18); parallel runs / LLM (later iterations).
- Automated SSE integration test once **`TestClient`** / async streaming pattern is stable.

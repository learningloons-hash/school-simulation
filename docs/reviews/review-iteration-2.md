# Review: Iteration 2
Date: 2026-03-31
Reviewer: Claude Opus (Architect)
Verdict: NEEDS_WORK

## Iteration Delta
- Iteration 1 added interaction metadata (broadcast/reply/meeting_note) and cross-agent context injection
- Iteration 2 added per-agent state tracking (support/resistance/workload/belief_posture), demographics, global state snapshots, and round outcome indicators

## Critical Issues

### C1: Prompt is a debug string, not a persona prompt
- Severity: CRITICAL
- Files: `backend/src/mirofish_backend/simulation/orchestrator.py` (lines 195-220)
- Problem: The prompt sent to the LLM is a flat key=value dump (`AgentRole=principal`, `PersonaBeliefs={'trust_in_moe_policy': 0.55}`) with no system message. No persona identity separation from task instruction.- Fix: Refactor into two-message architecture. Create a `system` message containing persona identity (name, role, style_cues, beliefs written as natural prose, psychological profile, school context). Create a `user` message containing round context (round number, policy event, interaction task, other agents' recent actions, working memory). Add response format guidance requesting structured output. Update `lmstudio_client.py` to accept and send both `system` and `user` messages.

### C2: max_tokens=64 truncates agent responses
- Severity: CRITICAL
- Files: `backend/src/mirofish_backend/llm/lmstudio_client.py` (line 16)
- Problem: 64 tokens produces 1-2 sentences. Agents cannot express nuanced policy positions, deliberate on implementation challenges, or respond meaningfully to other agents.
- Fix: Change default `max_tokens` to 1024. Make it configurable via `Settings` in `config.py`. Add a `max_tokens` field to `SimulationRunRequest` so it can be set per-run.

### C3: Keyword-counting state update is methodologically invalid
- Severity: CRITICAL
- Files: `backend/src/mirofish_backend/simulation/orchestrator.py` (`_apply_state_update()`, lines 98-120)
- Problem: State updates count keyword occurrences ("support", "concern", "workload"). "I do not support this" increases support score. This is a bag-of-words heuristic applied where LLM-driven analysis is required. An examiner would reject this as invalid for a simulation validity study.- Fix: Replace `_apply_state_update()` entirely. After getting the LLM response, make a second LLM call asking the model to extract belief state as structured JSON: `{"support_level": 0.0-1.0, "resistance_level": 0.0-1.0, "workload_stress": 0.0-1.0, "belief_posture": "supportive|resistant|mixed", "reasoning": "..."}`. Use this JSON to update agent state. Alternatively, instruct the agent to include a `<state>` block in its response that is parsed out.

### C4: No error handling on simulation failure
- Severity: CRITICAL
- Files: `backend/src/mirofish_backend/api/simulations.py` (line 62)
- Problem: `asyncio.create_task()` is fire-and-forget with no error handling. A crash mid-run leaves status as "running" forever. Frontend polls for 8 minutes then shows "timeout".
- Fix: Wrap `run_simulation_task` in a try/except. On exception, call `set_simulation_status(..., status="failed")` and log the error. Add an `error_message` column to `simulation_runs` table to surface the reason.

### C5: No Claude API connector
- Severity: CRITICAL
- Files: `backend/src/mirofish_backend/llm/` (missing)
- Problem: Only LM Studio (local) is connected. Phase 1 research requires frontier model runs on Claude Sonnet/Opus for comparison. The `all_frontier` and `comparison` LLM Router modes don't exist yet.
- Fix: Add `claude_client.py` using the `anthropic` SDK (`pip install anthropic`). Implement `chat_completion_anthropic(*, model, system, messages, max_tokens, temperature) -> str`. Add `anthropic_model` and `anthropic_api_key` fields to `Settings`. Then add a `LLMRouter` class in `llm/router.py` that dispatches based on a `model_mode` enum.

## Important Issues

### I1: No config snapshot per run
- Severity: IMPORTANT
- Files: `backend/src/mirofish_backend/db/schema.py`, `backend/src/mirofish_backend/api/simulations.py`
- Problem: No way to prove a run is reproducible without knowing its exact config. Thesis requires reproducibility.
- Fix: Add `config_snapshot TEXT` column to `simulation_runs`. At run creation, serialize the full config dict (scenario_id, agent_limit, total_rounds, random_seed, model_mode, model_used, prompt_version, llm_temperature, max_tokens) as JSON and store it.

### I2: Personas hardcoded in Python, no YAML files
- Severity: IMPORTANT
- Files: `backend/src/mirofish_backend/scenarios/registry.py`
- Problem: Personas and scenarios are Python dataclasses. Architecture spec requires YAML files so examiners can read them directly and they can be versioned independently.
- Fix: Create `backend/src/mirofish_backend/scenarios/psle_reform.yaml` with persona templates using the full psychological profile schema (openness_to_change, policy_compliance_tendency, professional_identity_strength, risk_aversion, workload_sensitivity). Add a YAML loader in `registry.py`.

### I3: Duplicate virtual environments
- Severity: IMPORTANT
- Files: `backend/.venv/`, `backend/venv/`
- Problem: Two identical venvs. Wastes space and causes confusion about which is active.
- Fix: Delete `backend/venv/`. Add both to `.gitignore`.

### I4: Python 3.14 (pre-release)
- Severity: IMPORTANT
- Files: `backend/.venv/pyvenv.cfg`
- Problem: Python 3.14 is pre-release. Risk of breaking changes.
- Fix: Recreate venv with Python 3.11 or 3.12. Update `pyproject.toml` to `requires-python = ">=3.11,<3.13"`.

## Architecture Alignment

| Component | Status | Gap |
|-----------|--------|-----|
| Orchestrator | ⚠️ | Works but no error recovery, no config snapshot |
| LLM Router | ❌ | LM Studio only. No Claude connector, no 5-mode routing |
| Memory System | ⚠️ | Working memory (last-K) only. No short-term/long-term layers |
| Prompt Architecture | ❌ | No system/user separation. Debug dump format. max_tokens=64 |
| RAG Pipeline | ❌ | Not implemented. Policy events are hardcoded strings |
| Persona System | ⚠️ | Python dataclasses exist but no YAML, no full psych profile |
| Validity Module | ❌ | Not implemented |
| Scenarios | ⚠️ | PSLE MVP only. No FSBB. Hardcoded in Python not YAML |
| Data Model | ⚠️ | Core tables good. Missing config_snapshot, error_message |
| Frontend | ⚠️ | Functional but no charts, no shadcn/Tailwind, polling not WS |
| Config/Reproducibility | ❌ | No config snapshot. Can't prove reproducibility |

## Next Iteration Spec (Iteration 3)

### Priority 1 (must complete)
1. **Prompt refactor**: Split into system + user message structure. System message = persona brief in natural prose. User message = round context + task + response format. Update `lmstudio_client.py` to send `[{role: system, ...}, {role: user, ...}]`.
2. **Increase max_tokens**: Default 1024, configurable via `Settings` and `SimulationRunRequest`.
3. **LLM-driven state update**: Replace `_apply_state_update()` with structured JSON extraction from agent response. Agent system prompt should instruct it to end each response with a `<state>` JSON block. Parse and apply.
4. **Simulation error handling**: Wrap `run_simulation_task` in try/except, set status=failed, store error message.
5. **Config snapshot**: Add `config_snapshot` JSON column to `simulation_runs`, populate at creation.

### Priority 2 (stretch goals)
1. **Claude API connector**: Add `anthropic` SDK, implement `claude_client.py`, add `LLMRouter` dispatch class.
2. **YAML persona templates**: Move personas from `registry.py` to `psle_reform.yaml`, add YAML loader.
3. **Export API endpoints**: Add `GET /simulations/{id}/export/transcript.csv` and `.json` so export doesn't require direct file access.

## Test Requirements for Iteration 3
1. Existing 4 tests must still pass.
2. New test: `test_prompt_has_system_message` — assert that the messages list sent to LLM contains a `system` role message with persona content.
3. New test: `test_state_update_uses_structured_output` — mock LLM to return a response containing a `<state>` block; assert that parsed state values match the block, not keyword counts.
4. New test: `test_simulation_error_sets_failed_status` — mock LLM to raise an exception; assert simulation status becomes "failed" and `error_message` is populated.
5. Frontend build (`vite build`) must still pass.

# Iteration 15 closeout — IAD interaction rules + network topology

**Date:** 2026-04-05  
**Status:** Shipped

## Shipped

### 1. `interaction_policy.py` — named policy objects (new module)

New file: `backend/src/mirofish_backend/simulation/interaction_policy.py`

Encodes the IAD/Trinidad theoretical framework as versioned, named enums and policy objects:

- **`ChannelType`** enum: `BROADCAST`, `DIRECT`, `MEETING` — replaces ad-hoc string literals in the orchestrator.
- **`TurnOrderPolicy`** enum: `ROUND_ROBIN` (previous default), `HIERARCHICAL` (principal → HoDs → teachers by `role_level`).
- **`VisibilityPolicy`** enum: `FULL` (previous default), `GROUP_BOUNDED` (agents only see turns from shared groups + all broadcasts).
- **`InteractionOverlay`** enum: `NONE`, `SCHOOL_TRINIDAD` (activates Trinidad's authority-based channel defaults).
- **`InteractionPolicy`** dataclass: immutable snapshot of all four fields + `policy_version = "1"`.
- **`build_interaction_policy()`** factory: validates string inputs, raises `ValueError` on unknown values. Applies upgrade rule: `school_trinidad` overlay auto-upgrades `round_robin` to `hierarchical`.
- **`apply_turn_order(agents, policy)`**: re-orders agent list by `role_level` (hierarchical) or preserves original order (round-robin). Stable sort within tiers.
- **`visible_turns_for_agent(turns, agent, policy)`**: filters recent turns to those visible under the policy. Agents without groups fall back to full visibility.
- **`channel_for_turn(turn_index, total_speakers, agent_role_level, policy)`**: selects channel type. Trinidad overlay forces `BROADCAST` for `role_level == 1` regardless of turn position.

### 2. Orchestrator integration

- `run_simulation_task` gains three new keyword arguments: `turn_order_policy`, `visibility_policy`, `interaction_overlay`.
- `build_interaction_policy()` is called once per run; policy is passed into each round.
- `apply_turn_order(round_agents, interaction_policy)` applied before the turn loop each round.
- `visible_turns_for_agent` applied after `clip_recent_interactions`, before self-turn exclusion.
- `_build_interaction_plan` updated to accept an optional `InteractionPolicy`; uses `channel_for_turn` to select channel type, then maps to the correct `InteractionPlan` shape.

### 3. Scenario registry

- `ScenarioConfig` gains `interaction_overlay: str = "none"`.
- `_scenario_from_mapping` reads `interaction_overlay` from YAML documents.
- `scenario_config_to_document` serializes it (omitted when `"none"`).
- Orchestrator reads `scenario.interaction_overlay` as the effective overlay when none is specified at the run level.

### 4. API

- `SimulationRunRequest` gains `turn_order_policy`, `visibility_policy`, `interaction_overlay` fields with validation-friendly defaults.
- `run_simulation_task_guarded` passes these through to the orchestrator.
- `config_snapshot` includes an `interaction_policy` sub-object with all four fields and `policy_version`.

## ADR

Interaction parameters are now a versioned contract. `policy_version = "1"` is stored in every `config_snapshot`. Any new parameter added from this point forward is an additive extension (new field with a default) — not a refactor.

Full documentation: `docs/adr/ADR-002-interaction-policy-contract.md` (to be written in a future pass; the code itself is the primary contract reference for now).

## Deferred

- Researcher UI controls for `turn_order_policy` / `visibility_policy` (can be added to Scenario Wizard or run form without touching the engine).
- Network-edge CSV (explicit adjacency matrix for visibility); currently groups proxy this.
- `MEETING` channel group-scoping in `_build_interaction_plan` (meeting note currently broadcasts to `"all"`; restricting to the speaker's groups is a one-line change once group-scoped meetings are needed).

## Verification

- `PYTHONPATH=src pytest tests/test_iteration15_interaction_policy.py` — **26** passed.
- `PYTHONPATH=src pytest tests/` — **96** passed (Python 3.11).
- `npm run build` in `frontend/` — passed (no frontend changes in this iteration).

## References

- `backend/src/mirofish_backend/simulation/interaction_policy.py` (new)
- `backend/src/mirofish_backend/simulation/orchestrator.py`
- `backend/src/mirofish_backend/scenarios/registry.py`
- `backend/src/mirofish_backend/scenarios/serialize.py`
- `backend/src/mirofish_backend/api/simulations.py`
- `backend/tests/test_iteration15_interaction_policy.py`

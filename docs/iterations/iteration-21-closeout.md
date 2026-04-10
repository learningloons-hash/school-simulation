# Iteration 21 closeout — Generic engine cleanup

**Date:** 2026-04-06  
**Status:** Shipped — **Architect PASS**; pre–Iteration 22 hardening from review applied.  
**Theme:** Remove school-specific hardcoding from core engine paths; drive initial agent state from persona YAML; domain-agnostic synthetic demographics and scenario-generation prompts.

## Pre-gate housekeeping

| Item | Detail |
|------|--------|
| **`api/capabilities.py`** | `build_capabilities_dict()["export_version"]` updated **`"4"` → `"5"`** so planner vocabulary matches real exports (Iteration 20 follow-up). |

## Shipped

| Item | Detail |
|------|--------|
| **`PersonaTemplate.initial_state`** | Optional `dict` (YAML `initial_state` block). Parsed in `_persona_from_mapping`; empty → orchestrator uses neutral defaults. |
| **`simulation/orchestrator.py`** | Removed `_initial_state_for_role`. Added `_neutral_initial_state()`, `_initial_state_from_persona(persona)`. `run_simulation_task` seeds `agent_states` from persona YAML. |
| **`_build_demographics`** | Rewritten: `role_level` + `idx` only — age `max(22, 49 - (min(role_level, 6) - 1) * 8 + (idx % 3))` (floors at 22 and caps tier spacing so `role_level` ≥ 8 never yields negative age), sex cycles female/male, **`ethnicity` / `ses` → `"unspecified"`**. No role-name strings. `_merge_demographics` takes `role_level` instead of `role`. |
| **Bundled YAML** | `psle_reform_mvp.yaml` and `fsbb_comparator.yaml` — `initial_state` on each persona matching former `_initial_state_for_role` values (regression). |
| **`registry.py` embedded fallback** | FSBB personas carry `initial_state`; PSLE single-persona fallback carries principal `initial_state`. Comment on `_SCENARIOS_FALLBACK`: school demo, engine domain-agnostic. |
| **`roster/csv_roster.py`** | `merge_persona_for_slot` copies `initial_state` from base. |
| **`api/scenarios_generate.py`** | `_GENERATE_SYSTEM_TEMPLATE` — domain-agnostic wording; `role` / `role_level` described generically; optional `initial_state` on personas; brief asks for 3-persona policy scenario for brief’s domain (not “school” only). |
| **`scenarios/validate.py`** | `role_level < 1` → warning with “positive integer (1 = highest authority)”. Removed old “not 1/2/3” warning. `initial_state` must be object when present. **`initial_state` numeric checks:** `support_level`, `resistance_level`, `workload_stress` — warn if not in `[0.0, 1.0]`; error if not coercible to float. |
| **`simulation/interaction_policy.py`** | Module docstring: turn-order bullet uses generic **ascending `role_level` (lowest number first = highest authority)**; overlays as domain plug-ins (`school_trinidad`, etc.). `TurnOrderPolicy.HIERARCHICAL` docstring generalized around `role_level`. |
| **`docs/domain-packs.md`** | One-pager: generic engine vs domain packs, overlays, PSLE/FSBB as reference. |

## Gate evidence

```bash
cd backend && pytest --tb=short -q
# 134 passed, 1 skipped
cd ../frontend && npm run build
```

## New tests (`tests/test_iteration21.py`)

| Test | What it verifies |
|------|-----------------|
| `test_psle_yaml_initial_state_matches_legacy_engine_defaults` | PSLE three personas → same numeric/posture tuple as pre–Iter 21 hardcoding |
| `test_fsbb_yaml_initial_state_matches_legacy_engine_defaults` | FSBB three personas → same |
| `test_neutral_initial_state_when_persona_has_no_initial_block` | `PersonaTemplate` without `initial_state` → `_neutral_initial_state()` |
| `test_build_demographics_high_role_level_clamps_age` | `role_level=10` → `age >= 22` (architect pre–Iter 22 fix) |
| `test_build_demographics_role_level_based_no_role_strings` | Ages 49/42/35 for role_level 1/2/3 with idx 0/1/2; ethnicity/ses unspecified |
| `test_validate_warns_when_role_level_below_one` | `role_level: 0` → warning |
| `test_validate_warns_initial_state_out_of_range` | `support_level: 1.5` → warning |
| `test_validate_errors_initial_state_non_numeric` | `support_level: "high"` → error |
| `test_validate_no_warning_for_role_level_four` | `role_level: 4` → no positive-integer warning |

**Also:** `tests/test_iteration16.py` — `export_version` assertion updated to `"5"`.

## Architect review — follow-ups applied (pre–Iteration 22)

Per **`HANDOFF_TO_BUILDER.md`** § *Pre-Iteration 22 fixes (from Iteration 21 architect review)*:

1. **Age clamp** — `_build_demographics` uses `min(role_level, 6)` inside the spacing term and `max(22, …)` floor.
2. **`initial_state` validation** — `validate_scenario_document` warns on out-of-range floats; errors on non-numeric values for the three state dimensions.
3. **Module docstring** — `interaction_policy.py` top-level turn-order bullet no longer uses principal/HoD/teacher wording.

## Not in scope (defer)

- Iteration 22+ sampling strategies, tier execution, network, experiments — see `HANDOFF_TO_BUILDER.md`.

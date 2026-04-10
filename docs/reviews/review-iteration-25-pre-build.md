# Review: Iteration 25 — Pre-Build Spec Review

Date: 2026-04-07
Reviewer: Claude Opus (Architect)
Type: Pre-build (Iteration 25 not yet started — no code, no closeout)

## Purpose

Joan is about to build Iteration 25 (network adjacency + `network_centrality` + `network_bounded` + `round_participants_only`). This review identifies spec gaps, ambiguities, and gotchas so she can build it right the first time.

---

## Critical Spec Clarifications (must resolve before building)

### C1: `network_csv` agent ID format — what do the IDs reference?

- Severity: CRITICAL (wrong answer = broken network lookup at runtime)
- Context: Runtime agent IDs are composite: `{persona_id}_{idx:03d}` (e.g. `principal_001_000`). Scenario YAML `persona_id` values are `principal_001`, `hod_001`, etc. Population/roster CSV use `persona_id` too.
- Problem: The spec says `source_agent_id,target_agent_id,influence_weight` but doesn't say whether those IDs match **runtime** `agent_id` (constructed in `_build_agent_instances`) or **persona_id** from YAML/roster.
- **Recommendation:** Use **`persona_id`** in the CSV. At parse time, expand edges to all runtime agents that share that `persona_id`. This handles population-drawn duplicates gracefully (10 agents drawn from `teacher_001` all inherit the same edges). Agents with no matching CSV entries have zero degree. Document the mapping explicitly.
- If the CSV uses runtime `agent_id` instead, the CSV author needs to know the exact `{persona_id}_{idx:03d}` format AND the slot count — fragile and error-prone for researchers.

### C2: Degree centrality — directed or undirected?

- Severity: CRITICAL (affects tier assignment and sampling report)
- Problem: The spec says "sum of influence weights per agent" but the CSV is directional (`source → target`). Is degree centrality the sum of outgoing weights, incoming weights, or both?
- **Recommendation:** Use **total degree** (sum of all edge weights where agent appears as source OR target). This aligns with "who participates most in the influence network" — the relevant measure for sampling. Store `in_degree`, `out_degree`, and `total_degree` in the audit for thesis transparency, but tier assignment keys off `total_degree`.

### C3: `network_bounded` — symmetric or directional visibility?

- Severity: CRITICAL (affects simulation dynamics)
- Problem: If the CSV has edge A→B but not B→A, can A see B's turns? Can B see A's? The spec says "agents with a shared non-zero edge" which implies **any** edge between them (either direction), but "shared" is ambiguous.
- **Recommendation:** Visibility is **symmetric (union of both directions)**. If A→B OR B→A has a non-zero weight, both A and B see each other's turns. This matches the real-world intuition that if A influences B, B is also aware of A. Build the adjacency dict as `undirected_neighbors[agent_id] = set(...)` from the directed CSV. Document this in the `config_snapshot`.

---

## Important Design Decisions (pre-wire correctly)

### I1: `VisibilityPolicy` enum — naming alignment with ADR-002

- Severity: IMPORTANT (enum mismatch between existing code and ADR)
- Current: `VisibilityPolicy` has `FULL` and `GROUP_BOUNDED`.
- ADR-002: Describes `broadcast`, `round_participants_only`, `network_bounded`.
- `broadcast` in ADR-002 = `full` in current code. Two options:
  - **Option A (recommended):** Add `ROUND_PARTICIPANTS_ONLY` and `NETWORK_BOUNDED` to the enum. Keep `FULL` as-is (backward compatible). Treat ADR-002's "broadcast" as the conceptual description of `full`. Note the mapping in docstring.
  - Option B: Add `BROADCAST` as an alias for `FULL`, deprecating `FULL` over time. More complex.
- Joan should go with Option A unless Mark objects.

### I2: `visible_turns_for_agent` — expanded signature

- Current: `visible_turns_for_agent(recent_turns, agent, policy)`.
- Needed for `network_bounded`: the adjacency dict `{agent_id: set(neighbor_ids)}`.
- Needed for `round_participants_only`: the set of agent IDs speaking this round.
- **Recommendation:** Add optional keyword args:

```python
def visible_turns_for_agent(
    recent_turns: list[dict[str, Any]],
    agent: Any,
    policy: InteractionPolicy,
    *,
    network_neighbors: dict[str, set[str]] | None = None,
    round_speaker_ids: set[str] | None = None,
) -> list[dict[str, Any]]:
```

This keeps existing callers working with zero changes (both kwargs default to `None`). The orchestrator passes them when available. If `network_bounded` is set but `network_neighbors` is `None`, fall back to `FULL` with a warning (per ADR-002).

### I3: `interaction_visibility` vs `visibility_policy` — config_snapshot naming

- Severity: IMPORTANT (researcher clarity)
- Current `config_snapshot` has `interaction_policy.visibility_policy` = `"full"` or `"group_bounded"`.
- ADR-002 adds a top-level `interaction_visibility` field.
- **Recommendation:** Record the effective visibility in `config_snapshot.interaction_policy.visibility_policy` (same field), not a new top-level `interaction_visibility`. This keeps the policy object self-contained and avoids duplicate fields that could drift. Update the docstring to document all valid values.

### I4: `network_csv` forwarding to orchestrator

- The `run_simulation_task` signature needs a new parameter for the parsed network graph (not the raw CSV string — parse once in `queue_simulation_run`, pass the dict).
- **Recommended param:** `network_graph: dict[str, set[str]] | None = None` on `run_simulation_task`. The graph is built at queue time, stored in `config_snapshot` summary (node count, edge count, per-agent centrality), and passed through.

### I5: `network_centrality` strategy — top-K threshold

- The spec says "select top-K by degree centrality at Tier 1; next tier at Tier 2; remainder at Tier 3."
- But **K** is not defined. How many agents get Tier 1?
- **Recommendation:** Mirror the `role_stratified` / `posture_maxvar` pattern: one representative per distinct centrality band (e.g. top quartile = Tier 1, middle = Tier 2, bottom = Tier 3). Or simpler: top 33% = Tier 1, next 33% = Tier 2, bottom 33% = Tier 3 by sorted centrality. Pick one rule and document it — the researcher can override via roster `fidelity_tier` anyway.

### I6: `network_centrality` without `network_csv` — 422 vs fallback

- The spec says "return 422 if missing." This is the right choice. The 422 should come from `queue_simulation_run` validation (before the background task launches), NOT from `compute_fidelity_tiers`. Add an early check in `queue_simulation_run`:

```python
if _req.sampling_strategy == "network_centrality" and not (_req.network_csv or "").strip():
    raise HTTPException(status_code=422, detail="network_centrality requires network_csv")
```

### I7: `round_participants_only` — non-speakers see nothing?

- Severity: IMPORTANT (affects state update for non-speakers)
- In `sample_k_per_round` mode, non-speaking agents skip LLM. But with `full_round_robin`, every agent speaks. `round_participants_only` visibility only makes sense with `sample_k_per_round` — in `full_round_robin` it's identical to `full`.
- **Recommendation:** No validation needed (it's correct behavior — all agents speak, all see each other). But document in the capability description that `round_participants_only` is most useful with `sample_k_per_round`.

---

## Minor Issues

### M1: Self-loops in network CSV

- If `source_agent_id == target_agent_id`, silently skip. Don't add an agent to its own neighbor set.

### M2: Duplicate edges

- If CSV has two rows `A,B,0.5` and `A,B,0.7`, last-wins or sum? **Recommendation:** Last-wins (simpler, matches CSV mental model of "latest row overrides"). Log a warning for the researcher.

### M3: Agent planner forwarding

- `PlanSimulationParams` needs `network_csv` and `interaction_visibility` (or the new visibility enum values). The planner JSON and `_simulation_run_request` mapper need alignment.

### M4: Sampling report `centrality` field

- Currently `null`. Populate it with `{agent_id: {total_degree, in_degree, out_degree}}` when network data is present. Keep `null` for non-network runs.

### M5: CSV template

- Add a new `GET /simulations/network-csv-template` endpoint (or embed an example in capabilities) so researchers know the format.

---

## Test Plan (minimum for architect PASS)

1. **Network parse:** Valid CSV → adjacency dict; empty CSV → `None`; malformed rows → 422; self-loops skipped; duplicate edges → last-wins.
2. **Degree centrality:** Known graph → expected `total_degree` / `in_degree` / `out_degree`.
3. **`network_centrality` strategy:** Tier assignment matches centrality ordering; 422 without `network_csv`.
4. **`network_bounded` visibility:** Agent with neighbors sees only neighbor + own turns; agent with no edges falls back to full; missing network graph falls back to full with warning.
5. **`round_participants_only` visibility:** Agent sees only turns from current-round speakers + own turns.
6. **Backward compatibility:** Runs without `network_csv` behave identically to pre-Iteration 25 (no regressions in existing strategies or `full` / `group_bounded` visibility).
7. **`config_snapshot`:** `network_csv_applied`, `network_node_count`, `network_edge_count`, per-agent centrality in `sampling_audit`.
8. **Sampling report:** `centrality` populated for network runs; `null` for non-network runs.
9. **Agent planner:** `PlanSimulationParams` accepts `network_csv` and new visibility values; validation catches `network_centrality` without CSV.
10. **Stress test (optional):** 50-agent run with dense network CSV, `network_bounded` visibility, `network_centrality` strategy, 2 rounds, fake LLM.

---

## Files Joan Will Touch (complete list)

| File | Change |
|------|--------|
| **New:** `simulation/network.py` | Parse CSV → adjacency dict; degree centrality; validation |
| `simulation/interaction_policy.py` | Add `ROUND_PARTICIPANTS_ONLY`, `NETWORK_BOUNDED` to `VisibilityPolicy`; update `build_interaction_policy` + `visible_turns_for_agent` signature/dispatch |
| `simulation/sampling_strategy.py` | Add `network_centrality` to `SAMPLING_STRATEGY_VALUES`; implement `_network_centrality_for_indices`; `compute_fidelity_tiers` needs centrality data param |
| `simulation/sampling_report.py` | Populate `centrality` from audit when present |
| `simulation/orchestrator.py` | Accept `network_graph` param; pass `network_neighbors` + `round_speaker_ids` to `visible_turns_for_agent` |
| `api/simulations.py` | `network_csv` on `SimulationRunRequest`; parse + validate; `config_snapshot` network fields; forward to orchestrator |
| `api/capabilities.py` | New visibility values, `network_centrality` strategy, network CSV docs |
| `agent/orchestrator.py` | `PlanSimulationParams.network_csv`; planner JSON; validation |
| `scenarios/validate.py` | Optional: validate `network_csv` format in scenario docs |
| **Tests:** `tests/test_iteration25.py` | All cases above |
| `docs/iterations/iteration-25-closeout.md` | Gate record |
| `docs/SESSION_STATE.md` | Update |

---

## Summary for Joan

Iteration 25 is the most **cross-cutting** slice since Iteration 15 (interaction policy). It touches the sampling strategy layer, the visibility layer, the orchestrator, the API, the planner, and the sampling report. The three critical decisions (C1–C3) must be locked before writing code — they affect every layer. The interface changes (I1–I4) should be done first as skeleton signatures so the implementation can fill in cleanly.

Suggested build order:
1. `simulation/network.py` (parser + centrality + adjacency builder) + unit tests
2. `interaction_policy.py` enum + `visible_turns_for_agent` expansion + unit tests
3. `sampling_strategy.py` `network_centrality` + unit tests
4. `api/simulations.py` wiring (`network_csv`, `config_snapshot`, orchestrator forwarding)
5. `agent/orchestrator.py` planner alignment
6. `sampling_report.py` centrality population
7. `capabilities.py` + integration tests
8. Docs + closeout

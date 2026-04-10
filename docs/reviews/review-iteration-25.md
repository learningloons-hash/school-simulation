# Review: Iteration 25

Date: 2026-04-07
Reviewer: Claude Opus (Architect)
Verdict: PASS_WITH_ISSUES

## Iteration Delta

- **`simulation/network.py`**: Network CSV parser with header validation, unknown-endpoint warnings, self-loop/zero-weight skip, `degree_centrality` (undirected total degree), `undirected_neighbor_map` for visibility.
- **`interaction_policy.py`**: `VisibilityPolicy` expanded — `BROADCAST` (ADR-002 primary), `FULL` (legacy alias, normalized to `broadcast`), `ROUND_PARTICIPANTS_ONLY`, `NETWORK_BOUNDED`; `visible_turns_for_agent` gains `effective_visibility`, `network_neighbors`, `round_speaker_ids` kwargs.
- **API / orchestrator / planner**: `network_csv` on `SimulationRunRequest` + `PlanSimulationParams`; Pydantic guard for `network_centrality` without CSV; `config_snapshot` records `network_csv_applied`, edge/node counts, `interaction_visibility`, `visibility_effective`, `network_visibility_fallback`; `sampling_report.py` populates `centrality` map from `degree_centrality` in per-agent audit; agent planner validates visibility policy against capabilities.

## Critical Issues

_None._ Network parse, centrality, tier assignment, visibility dispatch, and ADR-002 fallback are all implemented correctly. **172 passed, 1 skipped.**

## Important Issues

### I1: No end-to-end integration test through a queued run

- Severity: IMPORTANT
- Files: `backend/tests/test_iteration25.py`
- Problem: Tests cover parse/centrality/tier math, Pydantic guard, and capabilities. There is no test that **queues a run** with `network_csv` + `sampling_strategy=network_centrality` + `visibility_policy=network_bounded`, waits for completion, and asserts the persisted `config_snapshot` (network fields, per-agent `degree_centrality`, `visibility_effective`) and the `GET /sampling-report` centrality map. Iteration 26 now has such a test (`test_posture_maxvar_queued_run_audit_and_sampling_report`) — Iteration 25 should match that coverage.
- Fix: Add one `TestClient` + fake-LLM test that runs end-to-end and asserts `config_snapshot.network_csv_applied == True`, `config_snapshot.network_edge_count > 0`, `sampling_audit.per_agent[*].degree_centrality` populated, `GET /sampling-report` `centrality` map non-null, and `visibility_effective == "network_bounded"`.

### I2: `network_node_count` always equals `agent_limit` when CSV is present

- Severity: IMPORTANT (misleading for researchers)
- Files: `api/simulations.py` line 724
- Problem: `"network_node_count": len(agent_ids_for_audit) if net_parse else 0` — this is the total agent count, not the count of agents that appear in at least one edge. A run with 300 agents and a 3-edge CSV reports `network_node_count: 300`. The researcher expects this to reflect how many agents are connected.
- Fix: Compute from edges: `len({s for s, _, _ in net_parse.edges} | {t for _, t, _ in net_parse.edges})` — the count of agents that appear in at least one parsed edge. Keep `agent_limit` as a separate field (it already is).

### I3: `VisibilityPolicy.FULL` is a live enum value alongside `BROADCAST`

- Severity: IMPORTANT (duplicate enum, capabilities bloat)
- Files: `simulation/interaction_policy.py` lines 95–99, `api/capabilities.py` line 46
- Problem: `_enum_values(VisibilityPolicy)` returns both `"broadcast"` and `"full"` in the capabilities response. A researcher or planner seeing both values may not know they're identical. The factory normalizes `full` → `broadcast`, so passing `full` works, but the enum having two members for the same behavior is a code smell.
- Fix: Remove `FULL` from the enum; keep the `full → broadcast` normalization in `build_interaction_policy`. Or, if backward compat with stored `config_snapshot` values is needed, exclude `FULL` from capabilities output by filtering in `_enum_values` or marking it with a `_DEPRECATED` convention.

### I4: `round_participants_only` does not include broadcast turns

- Severity: IMPORTANT (design question, not a bug — needs confirmation)
- Files: `simulation/interaction_policy.py` lines 283–293
- Problem: `ROUND_PARTICIPANTS_ONLY` filters strictly to `round_speaker_ids` + own turns. Unlike `NETWORK_BOUNDED` (which also passes broadcast turns), `ROUND_PARTICIPANTS_ONLY` does **not** show broadcast turns from non-speakers. In `sample_k_per_round` mode, a non-speaking Tier-1 principal's broadcast from the previous round would be invisible to current-round agents. This may be intentional (strict cohort isolation) but differs from `NETWORK_BOUNDED`'s more permissive pattern. If a researcher expects broadcasts to always be visible, this is surprising.
- Fix: Confirm this is the intended design. If broadcasts should be visible under `round_participants_only`, add a `turn.get("interaction_type") == ChannelType.BROADCAST.value` passthrough (same pattern as `NETWORK_BOUNDED` and `GROUP_BOUNDED`).

### I5: `SESSION_STATE.md` not updated for Iteration 25

- Severity: IMPORTANT (cold-start handoff integrity)
- Files: `docs/SESSION_STATE.md`
- Problem: The file still shows Iteration **26** as the last gate with **163** tests. Iteration **25** shipped with **172** tests and should be the latest gate. No **Completed Work § Iteration 25** section exists. **Gate Evidence** and **Next Iteration Focus** are stale.
- Fix: Same pattern as the Post-Iteration 26 hardening — update Current Status, add Completed Work section, update Gate Evidence to 172, point Next Iteration Focus at Iteration **27**.

## Minor Issues

### M1: Duplicate weight edge handling undocumented

- Files: `simulation/network.py`
- Problem: If CSV has `A,B,0.3` and `A,B,0.7`, both edges are kept in the tuple. `degree_centrality` sums both (A gets 1.0 from B). `undirected_neighbor_map` adds B to A's neighbors on the first edge and the second is a no-op. This is fine behavior but should be one line in the docstring or CSV template comment.

### M2: Typo in test name

- Files: `tests/test_iteration25.py` line 97
- Problem: `test_samling_strategy_values_contains_network_centrality` — missing "p" in "sampling".

### M3: `network_csv` description says `persona_id_NNN` format

- Files: `api/simulations.py` line 316
- Problem: `"Agent ids must match run ids (persona_id_NNN)"` — the actual format is `persona_id_{idx:03d}` (e.g. `principal_001_000`). This is correct but a researcher won't know the `_NNN` suffix without seeing the audit. Consider documenting the format more clearly or mentioning that `per_agent[].agent_id` in the audit shows the exact IDs.

## Architecture Alignment

| Component | Status | Gap |
|-----------|--------|-----|
| Orchestrator | ✅ | `network_neighbors` + `effective_visibility` threaded through; `spoke_ids` computed before turn dispatch. |
| LLM Router | ✅ | Unchanged. |
| Memory System | ✅ | Unchanged. |
| Prompt Architecture | ✅ | Unchanged. |
| RAG Pipeline | ✅ | Unchanged. |
| Persona System | ✅ | Unchanged. |
| Validity Module | ✅ | Unchanged. |
| Scenarios | ✅ | Unchanged. |
| Data Model | ✅ | `degree_centrality` injected into `sampling_audit.per_agent` at queue time. |
| Frontend | ✅ | No frontend changes this slice (correct per spec). |
| Config/Reproducibility | ✅ | Network metadata + visibility fallback fully recorded. |
| Sampling Audit (Iter 22+) | ✅ | `degree_centrality` on each `per_agent` row; sampling report `centrality` populated. |
| Network (Iter 25) | ✅ | ADR-002 implemented; all three visibility policies functional. |

## Next Iteration Spec

### Priority 1 (must complete) — Iteration 27

1. Multi-run **experiment framework** per `HANDOFF_TO_BUILDER.md` Iteration 27 starter.
2. `POST /experiments`, `GET /experiments/{id}`, comparison table, export.

### Priority 2 (hardening before or with Iteration 27)

1. End-to-end integration test for network run (see I1).
2. Fix `network_node_count` to reflect connected agents, not total roster (see I2).
3. Decide on `FULL` enum cleanup (see I3).
4. Confirm `round_participants_only` broadcast behavior (see I4).
5. Update `SESSION_STATE.md` (see I5).
6. Fix test typo `test_samling_strategy` (see M2).

## Test Requirements

1. `cd backend && uv run pytest` — **172 passed, 1 skipped** (verified 2026-04-07).
2. Integration test (I1) should bring count to ~173+.
3. Backward compat: existing strategies and `full` / `group_bounded` visibility unchanged (verified via existing test suite).

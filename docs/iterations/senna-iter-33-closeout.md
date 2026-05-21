# Senna iter-33 closeout — Data-Driven Routing Policies (Arc 7)

**Spec:** [`docs/handoffs/HANDOFF_SENNA_ARC7.md`](../handoffs/HANDOFF_SENNA_ARC7.md) **`## senna-iter-33`**.  
**Date:** 2026-05-19

## Shipped

- **`llm/routing_policies.py`** — `local_only`, `frontier_only`, `hybrid_first_turn`; `llm_provider_to_routing_policy`; per-turn `resolve_effective_provider` and `resolve_effective_profile_id`.
- **`llm/router.py`** — delegates to routing policies; accepts `routing_policy` or legacy `routing_mode`.
- **`llm/model_profiles.py`** — `routing_policy_config_snapshot` for `config_snapshot`.
- **`api/simulations.py`** — persists `routing_policy`, `routing_profile_local_id`, `routing_profile_frontier_id`; passes policy + profile ids into orchestration; legacy `hybrid_routing_policy` retained when hybrid.
- **`simulation/orchestrator.py`** — uses named policy per turn; persists `effective_profile_id`.
- **`db/schema.py` / `db/repo.py`** — `agent_turns.effective_profile_id` column; transcript + export bundle include field.

## Behavior

| `llm_provider` | `routing_policy` |
|------------------|------------------|
| `lmstudio` | `local_only` |
| `anthropic` | `frontier_only` |
| `hybrid` | `hybrid_first_turn` (turn 1 → frontier, else local) |

## Verification

- `uv run pytest` (from `backend/`): **228 passed, 1 skipped**
- Hybrid E2E (`test_iteration12`) still passes with `effective_provider`, `effective_model`, and `effective_profile_id`.

## Next

**senna-iter-34** — Arc 7 hardening + migration checks (full-stack).

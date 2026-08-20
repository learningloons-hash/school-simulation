# Senna iter-45 closeout — memory context instrumentation

**Spec:** [`docs/handoffs/handoff-to-architect.md`](../handoffs/handoff-to-architect.md) / [`handoff-to-builder.md`](../handoffs/handoff-to-builder.md) **`senna-iter-45`** (link repointed 2026-08-20 — original `HANDOFF_SENNA_ARC10_MEMORY_DIAGNOSTICS.md` no longer exists on `main`, per Arc 10 review Warning #5 / Arc 11 carry-forward item 4)
**Date:** 2026-08-18
**Status:** **CLOSED**

## Delivered

- Per-turn inclusion/exclusion log: `agent_context_inclusion` table + `build_memory_context_inclusion_records()` distinguishes **network_filtered**, **recency_cut**, and **char_budget_truncated** (included with truncation flag).
- Visibility partition: `partition_turns_by_visibility()` in `interaction_policy.py` (existing `visible_turns_for_agent` unchanged).
- Char clip metadata: `prepare_peer_response_for_prompt_with_meta()` in `context_clip.py`.
- Orchestrator persists inclusion rows each LLM turn (`orchestrator.py`); simulation behavior unchanged.
- Export: `memory_context_log`, `memory_context_summary` (incl. group-addressed proportion from `agent_turns.target_scope`); `EXPORT_VERSION` **10**; ZIP `memory_context_log.csv` + `memory_context_summary.json`.
- API: `GET /simulations/{id}/memory-context-report` (404/409/400 conventions match sampling-report).

## Verification

```bash
cd backend && uv run pytest tests/test_senna_iter45_memory_context.py -q
# → 7 passed

cd backend && uv run pytest -q
# → 309 passed, 2 skipped (2026-08-18)
```

## Gate checklist

1. One row per observer/candidate with distinguishable exclusion reasons — PASS (unit + integration tests).
2. Group-addressed proportion from existing `target_scope` — PASS (`get_group_addressed_turn_summary`).
3. Export v10 additive — PASS (`test_export_version_bumped`, iteration28/29 updated).
4. No turn-content regression — PASS (instrumentation is observational only).

**Next:** `senna-iter-46` (MemBench adapter) — confirm MIT license permits fixture vendoring before committing dataset files.

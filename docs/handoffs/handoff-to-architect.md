# Handoff to Architect

**Ritual:** Builder fills this file when work is **complete** (tests pass, committed). Architect reviews against [`handoff-to-builder.md`](./handoff-to-builder.md) and posts verdict in chat.

**Status:** Ready for review — `scenario-context-field` Part A.

---

## Builder report

### Summary

Implemented optional scenario-level `context:` YAML → `ScenarioConfig.context` → organisational setting block in tier-1/tier-2 LLM system prompts + `config_snapshot.scenario_context`. No `EXPORT_VERSION` bump.

### Files changed

| File | Change |
|------|--------|
| `backend/src/mirofish_backend/scenarios/registry.py` | `ScenarioConfig.context`; `_context_from_scenario()` with load-time `ValueError` |
| `backend/src/mirofish_backend/llm/prompt_templates.py` | `ORGANISATIONAL_CONTEXT_TITLE`, `_organisational_context_block()`, kwarg on both prompt builders |
| `backend/src/mirofish_backend/simulation/orchestrator.py` | `organisational_context=scenario.context` in tier-1 and tier-2 branches |
| `backend/src/mirofish_backend/api/simulations.py` | `"scenario_context": dict(scenario_cfg.context)` in `config_snapshot` |
| `backend/tests/test_scenario_context.py` | **New** — acceptance tests A–E |

### Decisions implemented

| # | Decision | Done |
|---|----------|------|
| 1 | Block after Prompt version, before persona; exact framing title via `_profile_lines()` | ✅ |
| 2 | Reuse `_profile_lines()` — no duplicate bullet renderer | ✅ |
| 3 | Tier 1 ✅ Tier 2 ✅ Tier 3 ❌ (heuristic only) | ✅ |
| 4 | No `EXPORT_VERSION` bump; additive `scenario_context` key | ✅ |

### Acceptance tests

| Test | Result |
|------|--------|
| **A** Sentinel `SENNA_CTX_SENTINEL_7f3a9c` in every captured system prompt (stub orchestrator, mixed tiers) | ✅ |
| **B** Empty/absent context → byte-identical golden prompts (tier 1 & 2) | ✅ |
| **C** `config_snapshot["scenario_context"]` matches scenario dict | ✅ |
| **D** Malformed `context` → `ValueError("scenario.context must be a mapping when present")` | ✅ |
| **E** Framing title + order before persona section | ✅ |
| **F** Builtin scenarios load with `context == {}` | ✅ |

### Verification

```text
cd backend && uv run pytest tests/test_scenario_context.py tests/test_prompt_messages.py tests/test_iteration23.py -q
→ 17 passed
```

### Out of scope (untouched)

`PersonaTemplate`, `policy_events`, RAG/corpus, `ciepss_school_b.yaml`, SSTRF fixtures.

### Part B unblock

Fixture authors may now add `context:` YAML; runs will inject context once Part A is merged. Sentinel test guards silent no-op regression.

### Commit

`scenario-context-field` Part A (ScenarioConfig.context + prompt injection).

### Notes for architect

- Empty context omits the block entirely (no extra blank lines vs pre-change prompts).
- `_context_from_scenario` normalises keys to `str`; values pass through as loaded from YAML.
- Config snapshot test uses `tmp_path` + `init_db` because `queue_simulation_run` touches `user_scenarios` when `scenario_source == "user"`.

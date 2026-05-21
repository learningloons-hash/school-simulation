# Senna iter-39 closeout — Structured Output Reliability + Arc 8 Integration

**Spec:** [`docs/handoffs/HANDOFF_SENNA_ARC8.md`](../handoffs/HANDOFF_SENNA_ARC8.md) **`## senna-iter-39`**.  
**Date:** 2026-05-19

## Shipped

- **`llm/state_parse.py`:** Hardened `<state>` extraction (multiple blocks, light JSON repair, code fences); `resolve_state_from_response` returns provenance: `model_parsed` | `repaired` | `keyword_fallback` (no extra LLM repair call).
- **Persistence:** `agent_turns.state_update_source`; poll transcript, export JSON, and ZIP `agent_turns.csv` include the field.
- **Orchestrator:** `_apply_state_from_response` records provenance on LLM turns; Tier-3 heuristic rows leave `state_update_source` null.
- **Tests:** Extended `test_state_parse.py`; new `test_senna_arc8_integration.py` (local, Anthropic, OpenAI-compatible mock, hybrid, keyword/repaired provenance, Tier-3 sentinel, preflight on queue, export).
- **Manual smoke:** `backend/scripts/lmstudio_profile_smoke.py`; `pytest.mark.manual` placeholder skipped in default CI.

## Files touched

- `backend/src/mirofish_backend/llm/state_parse.py`
- `backend/src/mirofish_backend/simulation/orchestrator.py`
- `backend/src/mirofish_backend/db/schema.py`
- `backend/src/mirofish_backend/db/repo.py`
- `backend/tests/test_state_parse.py`
- `backend/tests/test_senna_arc8_integration.py` (new)
- `backend/scripts/lmstudio_profile_smoke.py` (new)

## Verification

- `uv run pytest` (from `backend/`): **286 passed, 2 skipped** (manual SSE + LM Studio smoke placeholders)
- `npm run build` (from `frontend/`): **PASS**

## Arc 8 status

All five Builder gates (**senna-iter-35** through **senna-iter-39**) are implemented. Cursor Architect **PASS** (2026-05-19). **Return to GrandMaster for arc review.**

## Post–GM (economics follow-up)

**Date:** 2026-05-19  
**Issue:** Post-run economics billed only `effective_provider == anthropic`; OpenAI/OpenRouter profile runs showed $0.

**Shipped:**

- **`simulation/economics.py`:** `resolve_billing_provider_key` maps `effective_profile_id` → built-in `pricing_key` via registry; Tier-3 `heuristic` → $0; missing/unknown profile → legacy anthropic-provider-only fallback.
- **`tests/test_senna_arc8_economics.py`:** pure profile billing cases + mocked `openai_default` API/export regression.

**Verification:** `uv run pytest` — **290 passed, 2 skipped** (after follow-up).

**Cursor Architect:** **PASS** (2026-05-19) — GM issue resolved; legacy anthropic-without-profile regression retained in `test_iteration29.py`.

## Next

- **Arc 8:** GM final **PASS** (2026-05-19). Await next GM arc handoff.

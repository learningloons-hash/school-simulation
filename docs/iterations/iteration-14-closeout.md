# Iteration 14 closeout — researcher persona attribute UX

**Date:** 2026-04-05  
**Status:** Shipped

## Shipped

### 1. Roster CSV `_json` columns (schema parity with population CSV v2)

- `ParsedRosterRow` gains optional `identity`, `attitudes`, `personal_history` fields.
- New `_parse_json_object_cell` helper validates JSON objects with line-number errors.
- `merge_persona_for_slot` shallowly merges each section over the base persona (roster wins on key conflicts), same semantics as population CSV.
- `ROSTER_CSV_TEMPLATE` updated to include all three `_json` columns with comment.

### 2. `POST /scenarios/{id}/llm-fill` endpoint

- Accepts a persona stub (`persona_id`, `role`, `name`, `style_cues`, `beliefs_summary`, optional `sections` list).
- Calls the configured LLM (same provider as server default) with a structured prompt to generate `identity`, `attitudes`, `personal_history` dicts.
- Leniently parses LLM response (strips code fences, falls back to regex JSON extraction).
- Returns `LlmFillResponse` with the three dicts and `raw_llm_text` for debugging.
- Returns 422 if no valid sections requested; 502 if LLM call fails.

### 3. Scenario Wizard — sectioned attribute editor (frontend)

- `PersonaRow` type extended with `identity`, `attitudes`, `personal_history` (`Record<string, string>`).
- `hydrateFromDocument` and `buildDocument` round-trip sections correctly.
- Per-persona **Show/Edit** toggle reveals key-value editor for each of the three sections.
- **Randomize** button fills sections with role-appropriate plausible values (local, no LLM).
- **LLM Fill** button calls `POST /scenarios/{id}/llm-fill`; merges suggestions over existing keys; shows loading state.
- Key count badge shows "N keys set" when sections are populated.
- `toSectionMap` helper normalises server values to `Record<string, string>`.

## Deferred

- Enum registries / validated option sets for specific keys (e.g. gender_identity options).
- Section display in Run tab or transcript.

## Verification

- `PYTHONPATH=src pytest tests/` — **70** passed (Python 3.11).
- `npm run build` in `frontend/` — passed.

## References

- `backend/src/mirofish_backend/roster/csv_roster.py`
- `backend/src/mirofish_backend/api/scenario_catalog.py`
- `frontend/src/components/ScenarioWizard.tsx`
- `frontend/src/lib/api.ts`
- `backend/tests/test_iteration14_attributes_ux.py`

# Iteration 13 closeout — structured persona attributes

**Date:** 2026-04-04  
**Status:** Shipped (MVP slice: YAML + population overlays + prompts + persistence + export)

## Shipped

### 1. `AgentContext` version **2** (type name unchanged: `AgentContextV1`)

- New shallow maps: **`identity`**, **`attitudes`**, **`personal_history`** (string keys, JSON-serializable values).
- **`PersonaTemplate`** loads optional YAML blocks under each persona; **`scenario_config_to_document`** round-trips them.
- Orchestrator merges **population CSV** overlays per slot into those maps (shallow **`.update()`** per section).

### 2. Population CSV **schema v2** (backward compatible)

- Optional columns: **`identity_json`**, **`attitudes_json`**, **`personal_history_json`** — JSON **objects** per cell.
- **`POPULATION_SCHEMA_VERSION = "2"`**; template updated on **`GET /simulations/population-csv-template`**.

### 3. Prompts

- **`build_system_prompt`** emits labeled blocks: *Identity (structured attributes)*, *Attitudes / stance (structured)*, *Personal history (structured)* when non-empty.

### 4. Persistence & export

- SQLite **`agent_state_snapshots.attribute_sections_json`** (JSON blob of the three maps).
- **`state_timeline`** agents include **`attribute_sections`** when any section is non-empty.
- **`export.json` `export_version`:** **`4`**; ZIP **`agent_state_snapshots.csv`** stringifies dict **`attribute_sections`** per row for Excel safety.

### 5. `config_snapshot`

- **`agent_context_version`:** **`"2"`** on new runs.

### 6. Validation

- Scenario documents: **`identity`**, **`attitudes`**, **`personal_history`** on personas must be **objects** when present.

### 7. Example scenario

- **`psle_reform_mvp.yaml`**: principal persona includes sample **identity / attitudes / personal_history** keys.

### 8. Frontend

- **State** tab: expandable JSON for **`attribute_sections`** when present.
- Validity copy: **`export_version` 4**.

### 9. Tests

- `tests/test_iteration13_attributes.py`, extended **`test_agent_context`**, **`test_prompt_messages`**, population JSON parse/merge tests.

## Architect follow-up (post-review, non-blocking)

- **Rename:** population → orchestrator pipeline uses **`slot_overrides`** (was misleading as `demographic_overrides` only). Public helper **`build_personas_and_slot_overrides`**; **`build_personas_and_demographic_overrides`** kept as an alias.
- **Analyst-facing merge note:** `GET /simulations/population-csv-template` documents shallow merge for **`identity_json`** / **`attitudes_json`** / **`personal_history_json`** over scenario YAML.
- **Export changelog:** `export_bundle.py` module docstring + ADR-001 table for **`export_version`** 1→4.
- **Tests:** Export ZIP includes **`attribute_sections`**; population **`identity_json`** rejects JSON arrays.
- **PSLE YAML:** HoD and teacher personas include minimal example sections for demos.

## Deferred (later 13+ / 14)

- Analyst **wizard UI** for editing sections (today: YAML / JSON in scenario or population CSV).
- **Constrained randomize** and **LLM fill** with schema validation.
- **Enum registries** / inclusive option sets for specific keys.

## Verification

- `PYTHONPATH=src pytest tests/` — **62** passed (Python 3.11), including export ZIP **`attribute_sections`** + population JSON non-object rejection.
- `npm run build` in `frontend/`.

## References

- `backend/src/mirofish_backend/simulation/agent_context.py`
- `backend/src/mirofish_backend/scenarios/registry.py`, `validate.py`, `serialize.py`
- `backend/src/mirofish_backend/population/csv_population.py`
- `backend/src/mirofish_backend/db/schema.py`, `db/repo.py`
- `docs/adr/ADR-001-iteration-10-11-contracts.md`

# ADR-001: Iteration 10–11 contracts (agent context, interaction v2, population data)

**Status:** Accepted (Iterations 10–11 shipped; Iter 12+ extensions only)  
**Date:** 2026-04-02 (amended 2026-04-04)  
**Relates to:** [`BRIEF_FOR_JOAN.md`](../handoffs/BRIEF_FOR_JOAN.md) §0, §5–§6; [`HANDOFF_TO_ARCHITECT.md`](../handoffs/HANDOFF_TO_ARCHITECT.md); [`ARCHITECT_SIGNOFF_CHECKLIST_ITER10_11.md`](../handoffs/ARCHITECT_SIGNOFF_CHECKLIST_ITER10_11.md)

## Context

The Joan brief requires an **interaction model v2** (who speaks, who hears, non-speaker updates), **external population/network data**, and **reproducibility**. A separate planning thread adds a **dependency-first** rule: ship a **thin, versioned per-agent context** before interaction logic hardens on ad-hoc `demographics`, and use **one population-table contract** for import and sampling so a second format is not introduced later.

The brief also specifies:

- **§0 (IAD + Trinidad):** Generic **IAD-shaped** interaction vocabulary for cross-domain use; **Trinidad / school sociology** as an **optional overlay** for education scenarios—not universal for non-school runs.
- **§6:** Prefer prototyping **two** interaction strategies behind a **feature flag** early in Iteration 10 (e.g. `full_round_robin` vs `sampled_groups`) to avoid a single irreversible abstraction.

## Decision

1. **AgentContext (or equivalent) v0**  
   - Iteration 10 introduces a **documented, versioned** runtime structure for per-agent data the interaction planner and prompts consume.  
   - Existing `age`, `sex`, `ethnicity`, `ses` are **projected** from current `_build_demographics` into this shape until a full attribute schema lands (Iteration 13+).  
   - The contract is **locked** in this ADR’s “Interface” section below once implementation starts; minor revisions bump a **version** field and are recorded in `config_snapshot` / closeout.

2. **Feature flag (brief §6)**  
   - Iteration 10 **SHOULD** support **at least two** `simulation_mode` (or equivalent) values if schedule allows, sharing the **same** `AgentContext` contract for both.  
   - If timeboxed, **one** MVP mode ships first, with the **second** mode explicitly scheduled as **10b** in the same iteration closeout **or** recorded as deferred with a remediation date—**not** an undocumented second code path.  
   - Interaction **policy** (who speaks, selection rule, non-speaker updates) lives in **backend domain code**, not UI-only or ad-hoc scripts (see checklist).

3. **IAD vs Trinidad overlay (brief §0)**  
   - **Core** interaction and agent fields are **domain-neutral** (IAD-friendly: actors, positions, rules-in-use as appropriate to code structure).  
   - **School-specific** priors, channels, or empirical weights are loaded via **explicit overlay** (e.g. `school_profile`, `site_id`, scenario flag) and documented in run **provenance** / thesis note—not baked into the only code path.  
   - Iteration 11 **population / sampling** documentation MUST include a short **thesis alignment** note on representativeness limits and **IAD core vs Trinidad overlay** (per checklist).

4. **Iteration 11: single population contract**  
   - One **versioned** schema for population import (`population_schema_version` or equivalent).  
   - Weighted / stratified sampling uses **keys aligned** to `AgentContext` fields.  
   - **Network / edges** (brief “optional”) are an **add-on** to the same ADR family—separate artefact type but **one versioning story**, not a second competing population CSV dialect.

## Interface — `AgentContextV1` (Iterations 10 + 13)

Implementation: [`backend/src/mirofish_backend/simulation/agent_context.py`](../../backend/src/mirofish_backend/simulation/agent_context.py). The type name stays **`AgentContextV1`**; **`AGENT_CONTEXT_VERSION`** is **`"2"`** (Iteration 13).

| Field | Type | Notes |
|-------|------|--------|
| `version` | `str` | `AGENT_CONTEXT_VERSION` (**`"2"`**). |
| `slot_index` | `int` | 0-based roster index (roster CSV slot = index + 1). |
| `demographics` | `dict[str, Any]` | `age`, `sex`, `ethnicity`, `ses` (+ synthetic base / population overlays). |
| `group_ids` | `tuple[str, ...]` | Persona cohort ids (Iteration 9). |
| `identity` | `dict[str, Any]` | **Iteration 13** — survey-like identity attributes (YAML persona + optional population JSON overlay). |
| `attitudes` | `dict[str, Any]` | **Iteration 13** — stance / policy-relevant attitudes. |
| `personal_history` | `dict[str, Any]` | **Iteration 13** — career / biography snippets. |

`AgentInstance` holds `context: AgentContextV1`; `demographics` is a **property** delegating to `context.demographics`. Prompts use `to_prompt_demographics()` plus structured blocks for **`identity`**, **`attitudes`**, **`personal_history`** when non-empty (see `prompt_templates.build_system_prompt`). **`attribute_sections_for_snapshot()`** serializes the three maps for DB / export.

**`config_snapshot` (new runs):** `agent_context_version` **`"2"`**, `simulation_mode`, `speakers_per_round` (JSON `null` when `full_round_robin`), plus **Iteration 11–13** `population_*` fields when a population pool is applied (see below).

**Persistence:** `agent_state_snapshots.attribute_sections_json` stores the three maps per snapshot row; poll **`state_timeline`** agents may include **`attribute_sections`** when non-empty. **`export.json` `export_version`** **`4`** adds nested / CSV-serialized snapshot fields (see Iteration 13 closeout).

**`export.json` `export_version` (additive changelog):** **`1`** base; **`2`** +`validity_notes`; **`3`** + per-turn **`effective_provider`** / **`effective_model`**; **`4`** + snapshot **`attribute_sections`**; **`5`** + **`cohort_summary`**; **`6`** + per-turn **`fidelity_tier`** (Iteration 23); **`7`** + **`convergence_delta`** on global snapshots + **`converged_at_round`** on run (Iteration 28). See module docstring on [`export_bundle.py`](../../backend/src/mirofish_backend/export_bundle.py).

## Population table contract — **v1** (Iteration 11) + **v2** extensions (Iteration 13)

Implementation: [`backend/src/mirofish_backend/population/csv_population.py`](../../backend/src/mirofish_backend/population/csv_population.py).

- **Version:** `population_schema_version` **`2`** (`POPULATION_SCHEMA_VERSION`) — **backward compatible**: v1-style rows (without JSON columns) still parse; optional columns add overlays only.
- **Import:** Single CSV dialect; extensions bump version — **no** parallel format.
- **Draw:** Without replacement; deterministic RNG `Random(random_seed & 0xFFFFFFFF)`; modes **`weighted`** | **`stratified`** (by `stratum` column).
- **Alignment:** Rows reference **`persona_id`** (scenario template); optional **`age`**, **`sex`**, **`ethnicity`**, **`ses`**, **`name`**, **`groups`** map into **`AgentContextV1`** / `PersonaTemplate` after merge.
- **Iteration 13 columns (optional):** **`identity_json`**, **`attitudes_json`**, **`personal_history_json`** — each cell is a **JSON object** merged shallowly over the scenario persona’s section for that drawn row.
- **Precedence:** Population draw builds the run list → optional **roster CSV** overlays per 1-based slot (roster wins on overlapping persona fields).
- **Provenance:** `population_draw`, `population_merge_order`, `population_data_provenance`, `population_thesis_note` on `config_snapshot`.
- **Network / edges:** Still an **add-on** to this ADR family when implemented (separate artefact; shared versioning story).

**Interaction modes (`simulation_mode`):**

- `full_round_robin` — every agent gets a turn each round (legacy).
- `sample_k_per_round` — each round, `K = min(speakers_per_round, agent_limit)` agents selected with a **deterministic** RNG seeded from `random_seed` and `round_number`. Non-selected agents **do not** receive LLM turns that round; internal state is unchanged for them until they speak. Global round metrics still aggregate **all** agents.

Further fields or version bumps: amend this ADR and record in closeout / `SESSION_STATE.md`.

## Per-turn LLM traceability (Iteration 12)

- **`agent_turns.effective_provider`:** `lmstudio` \| `anthropic` — resolved per turn (e.g. hybrid: frontier on first turn of each round).
- **`agent_turns.effective_model`:** Model id string from server settings for that provider at run time.
- **`GET /simulations/{id}`** transcript entries and **export** flat `transcript` include both fields.
- **`GET /simulations/{id}/export.json`:** `export_version` **`4`** (Iteration 13 adds agent snapshot **attribute** sections; v3 fields retained). Still includes validity notes and prior bundle keys.
- **`POST /simulations/run`:** Response body includes **`warnings[]`** for analyst-visible issues (e.g. roster or population **`groups`** not defined on the scenario); detailed lists remain in **`config_snapshot`**.
- **`interaction_last_k`** (recent peer turns fed into prompts; orchestrator, first turn of round when `round_number > 1`): **`full_round_robin`** — `min(120, max(working_memory_last_k * 2, len(full_agents) * (round_number - 1)))`. **`sample_k_per_round`** — `min(120, max(working_memory_last_k * 2, len(round_agents) * max(1, round_number - 1) * 3))`. All other turns: `working_memory_last_k * 2`. *(The ×3 and cap 120 avoid over-fetching peer history when K ≪ agent_limit.)*

## Consequences

- Positive: Less refactor when full attribute schema and census weights arrive.  
- Negative: Iteration 10 is **larger** than “interaction only”; use **10a/10b** trains under one closeout if needed.  
- Checklist: [`ARCHITECT_SIGNOFF_CHECKLIST_ITER10_11.md`](../handoffs/ARCHITECT_SIGNOFF_CHECKLIST_ITER10_11.md).

## Links

- [`docs/plans/agent-attributes-roadmap.md`](../plans/agent-attributes-roadmap.md) — dependency-first sequencing summary.

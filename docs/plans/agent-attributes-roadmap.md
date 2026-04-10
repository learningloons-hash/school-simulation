# Agent attributes roadmap (dependency-first)

**Purpose:** In-repo summary of sequencing for **structured agent attributes**, **interaction v2**, and **population data**—aligned with [`HANDOFF_TO_ARCHITECT.md`](../handoffs/HANDOFF_TO_ARCHITECT.md) and [`ADR-001`](../adr/ADR-001-iteration-10-11-contracts.md). Detailed design notes may also live in Cursor plans; this file is the **versioned** anchor for anyone not using Cursor.

## Principle

Ship **stable contracts** before code that is expensive to unwind (interaction routing, exports, SQLite shape). Prefer one **population import / sampling** format over parallel dialects.

## Iteration map

| Iteration | Focus |
|-----------|--------|
| **10** | **Shipped (MVP):** **Interaction model v2** + **`AgentContextV1`** (`simulation/agent_context.py`). **`simulation_mode`:** `full_round_robin` \| `sample_k_per_round` + `speakers_per_round` (seed-stable subset). ADR-001 Interface updated. Further strategies (neighborhoods, two-tier) = later flags or Iter 11+. |
| **11** | **Single population-table contract**: import + weighted/stratified sampling + attribute completion; keys match agent context; `config_snapshot` provenance. Optional **network/edges** as add-on under same ADR/versioning story. |
| **12** | Performance / thesis hardening on **frozen** 10–11 contracts (`effective_provider`, stress tests, exports). |
| **13** | **Shipped (MVP):** Structured **`identity` / `attitudes` / `personal_history`** on **`AgentContextV1`** (version **2**); YAML personas + population CSV **v2** JSON columns; prompts + **`attribute_sections_json`** snapshots + **`export_version` 4**. |
| **14+** | Sectioned **UI**, constrained randomize, LLM-generated attributes with validation, enum registries—**extensions only**. |

## Longer-term vision (13+)

- Sectioned attributes: demographics, identity, attitudes, personal history, simulation-facing fields.  
- Editable enums (e.g. inclusive gender/sexuality options), random draws within schema bounds, census-style representativeness via Iteration 11 tables.  
- LLM fill + validate against the same schema as human edits.

## Links

- [`BRIEF_FOR_JOAN.md`](../handoffs/BRIEF_FOR_JOAN.md) §5.1 — planning note vs original iteration table.  
- [`ARCHITECT_SIGNOFF_CHECKLIST_ITER10_11.md`](../handoffs/ARCHITECT_SIGNOFF_CHECKLIST_ITER10_11.md) — review rubric.

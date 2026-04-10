# Brief for Joan (coding agent) — next iterations

**From:** Architect / Mark  
**Read before each implementation gate** (together with `HANDOFF_TO_BUILDER.md` and `docs/SESSION_STATE.md`). Iterations 8–9 are shipped; **10+** is current focus.

---

## Theoretical layering (IAD + Trinidad)

- **IAD (general):** Use the **Institutional Analysis and Development** framing as the **cross-domain engine vocabulary**—actors, positions, action situations, rules-in-use—so the same orchestration ideas can apply to **multiple policy contexts**, not only education. Reference: [`docs/frameworks/iad_guide.pdf`](../frameworks/iad_guide.pdf).

- **Trinidad (school-specific):** Use **Trinidad’s school / organisational sociology** only to **refine** interaction sequencing, channels, and empirical priors when the unit of analysis is a **school** (e.g. Mark’s case study). Do **not** treat that layer as universal for non-school scenarios. Reference: [`docs/frameworks/33OrgSoc.pdf`](../frameworks/33OrgSoc.pdf).

- **Implementation direction:** Prefer a **generic interaction / institution layer** (IAD-shaped) plus an optional **overlay** (e.g. `school_profile`, `site_id`, or loaded `empirical_weights`) that activates for education scenarios—so future domains can ship without Trinidad baggage.

---

## 1. UX idea (suggestion — do not rush)

**Desired eventually:** Side panel or bar while a run is **in progress**: per-agent cards, **tables or simple line charts** for attitude / round stats **updating live** (today’s data already arrives via polling `GET /simulations/{id}`). Optionally **key quotations** tagged as leaning toward implementation vs resistance.

**Architect instruction:** Treat this as **primarily UX**, but **do not lead with heavy UI polish** until the **simulation model and scale story** are thought through. First deliver a **short design note** (in-repo markdown under `docs/iterations/` or `docs/plans/`) that covers:

- What we poll today vs what we might **stream** later (SSE/WebSocket).
- How charts behave at **N agents** (10 vs 50 vs 500) — layout, pagination, “focus agents.”
- **Key quotes:** Phase A = heuristics / state deltas / conflict flags; Phase B = optional small LLM tagger (cost, latency).

Only then sequence UI work so we are not redrawing everything when scale semantics change.

---

## 2. Scale — be honest about “500 agents”

Today the engine runs **one LLM call per agent per round** in sequence (`agent_limit` currently capped at **50** in the API). A **literal** “500 agents × R rounds” with a full transcript per agent is **not** a small UX tweak: it is **time, cost, context, and interaction-structure** problem.

**Target to plan toward:** A **school-scale population (e.g. 500)** modeled as:

- A **roster** (identity + attributes + group memberships), and  
- A **simulation policy** that defines **who speaks**, **when**, and how **non-speaking** agents are updated (aggregate stats, sampling, hierarchical summaries — TBD).

Joan should **not** promise “500 LLM chatters per round” without a new **interaction model** signed off by Mark/architect.

---

## 3. Things to plan for (checklist for your design note)

- **N agents:** UX and API limits; performance testing as N grows.
- **Bulk persona management:** CSV/JSON import, templates, inheritance (“base teacher” + overrides), validation errors.
- **Groups / factions:** Departments, grades, cliques — how they affect **who hears whom** and **turn order**.
- **Network / population data:** Optional edge lists or adjacency for “neighborhood” interaction; weight tables for stratified sampling from census-like marginals.
- **Reproducibility:** `random_seed`, snapshot of sampling decisions in `config_snapshot` or sidecar export.
- **Thesis traceability:** e.g. persist **effective_provider** per turn (already flagged in prior handoff).

---

## 4. Iteration count to “full scaled” 500-population model

Rough **order-of-magnitude** (not a contract):

- **5 iterations (8–12):** Credible **path** to a **defined** large-population mode (roster + groups + one chosen sampling/interaction strategy + imports + perf guardrails), with **MVP** runs in the tens–low hundreds of **speaking** turns per round or heavy use of **aggregation**.  
- **Beyond that:** Hardening, evaluation, alternative interaction policies, parallel LLM execution, and operational monitoring — easily **+3–6 iterations** depending on how strict “full” is.

So: **~8–12 iterations from now** to something defensible as “500-person school population simulation” in a **thesis**, if “500” means **population + sampling**, not **500× full individual dialogue every round**.

---

## 5. Proposed next **five** iterations (8 → 12)

| Iter | Theme | Outcomes (MVP) |
|------|--------|----------------|
| **8** | **Observability + limits** | Live run dashboard: side panel / charts / table driven by **existing** poll payload; document current **scale limits** and cost model in docs; optional faster poll while `running`. |
| **9** | **Roster & groups** | Data model for **cohorts/factions**; bulk persona import (CSV/YAML); API/UI to assign agents to groups; modest increase in supported **agent_limit** **or** explicit “soft cap” with warnings — **no** fake 500 yet without Iter 10. |
| **10** | **Interaction model v2** | Choose and implement **one** strategy: e.g. **sample K speakers per round** from groups, **neighborhood-limited** attention, or **two-tier** (few detailed LLM agents + aggregate pool). Design doc + code + tests. |
| **11** | **External data** | Import **network** (edges) and/or **population table** for weights; deterministic stratified draw; export provenance fields. |
| **12** | **Performance & thesis hardening** | **Shipped:** per-turn **effective_provider** / **effective_model**, export v3, run **warnings[]**, sample-K **interaction_last_k** tweak, fake-LLM stress test. **Deferred:** parallel/batch LLM queue. |

Mark and architect may **reorder** 9–11 after your design note if one dependency is clearer.

### 5.1 Planning note — dependency-first scope (Iterations 10–11+)

The table above is the **original MVP wording**. **Current planning** (see [`HANDOFF_TO_ARCHITECT.md`](HANDOFF_TO_ARCHITECT.md), [`docs/adr/ADR-001-iteration-10-11-contracts.md`](../adr/ADR-001-iteration-10-11-contracts.md), [`docs/plans/agent-attributes-roadmap.md`](../plans/agent-attributes-roadmap.md)) tightens sequencing to reduce refactors:

- **Iteration 10** — **MVP shipped:** **`AgentContextV1`** + **`simulation_mode`** `full_round_robin` \| `sample_k_per_round` (see `iteration-10-closeout.md`, ADR-001). Further strategies (neighborhood-limited, two-tier pool) remain future work or additional modes.
- **Iteration 11** — **MVP shipped:** **one versioned population-table contract** (pool CSV, **`weighted`** / **`stratified`** draw, `config_snapshot` trace + thesis note). See `iteration-11-closeout.md`. **Network / edges** remain optional add-on under the same ADR versioning story.
- **Iteration 12** — **Shipped** (`docs/iterations/iteration-12-closeout.md`): **`effective_provider`** + **`effective_model`** per turn (DB, poll, export v3); **`warnings[]`** on **`POST /simulations/run`** for unknown roster/population **`group_ids`**; **`interaction_last_k`** tweak for **`sample_k_per_round`**; fake-LLM **stress** test. **Deferred:** parallel LLM / queue sketch.
- **Iteration 13+** — Rich attribute schema (survey-like sections), UI editor, constrained randomize, LLM fill—**extensions** of the Iteration 10 shell only. **Scenario analyst wizard (MVP shipped):** SQLite-backed user scenarios, `GET/POST/PUT /scenarios`, clone + YAML export, Run dropdown from API — see [`docs/plans/scenario-wizard-design.md`](../plans/scenario-wizard-design.md).

Architect **approval** of this scope shift is requested via `HANDOFF_TO_ARCHITECT.md`. Until then, treat this subsection as the **builder default** unless the architect revises it.

---

## 6. Is this a good idea?

**Yes**, with one refinement: treat **“500 agents”** as **population scale + sampling/aggregation semantics**, not **500 identical chat loops**. Your design note should make that distinction explicit so thesis methods stay defensible.

**Better idea if stuck:** Prototype **two** interaction strategies behind a feature flag (e.g. `simulation_mode: full_round_robin | sampled_groups`) early in Iter 10 so we don’t paint ourselves into one abstraction.

---

## Handback

Before handing back Iteration 10–11 work, self-check against `docs/handoffs/ARCHITECT_SIGNOFF_CHECKLIST_ITER10_11.md` and include pass/fail notes in `HANDOFF_TO_ARCHITECT.md`. Contract intent is summarized in `docs/adr/ADR-001-iteration-10-11-contracts.md` (update that ADR’s Interface section when types are concrete).

When each iteration gate is done: fill `HANDOFF_TO_ARCHITECT.md` and update `SESSION_STATE.md` + `docs/iterations/iteration-N-closeout.md`.

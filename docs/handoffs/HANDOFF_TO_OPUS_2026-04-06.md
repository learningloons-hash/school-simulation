# Handoff to Opus — 2026-04-06

This file is a cold-start brief for Opus (or any other assistant picking up this work in a new channel). It assumes no prior conversation context. It covers two threads: (1) what MiroFish has built through Iteration 18, and (2) a grant proposal discussion that took place on 2026-04-06. Read both sections before responding.

---

## 1. What MiroFish is

**MiroFish** is an LLM-powered multi-agent simulation platform built to model policy implementation dynamics in Singapore education contexts. It is a research tool and a PhD thesis artefact.

| Item | Detail |
|------|--------|
| **Owner** | Mark Lee Ser Ming — Ministry of Education Singapore (policy officer), PhD candidate at ANU Crawford School of Public Policy |
| **PhD thesis** | "Using Large Language Model-Powered Multi-Agent Simulation to Model Policy Implementation and Policy Evaluation" (submitted April 2026, ANU Crawford) |
| **Stack** | FastAPI backend (Python 3.12, `uv`) + React/Vite frontend (TypeScript) + SQLite |
| **LLM endpoints** | Local: LM Studio at `http://127.0.0.1:1234/v1`; Cloud: Anthropic Messages API |
| **Backend** | `0.0.0.0:8100` |
| **Frontend** | `0.0.0.0:3100` |
| **Host machine** | Mac mini (always-on); thin client is a Windows laptop over Tailscale |
| **Repo root** | `mirofish-mvp/` |
| **Session state doc** | `docs/SESSION_STATE.md` — single source of truth for cross-session handoffs; updated at every iteration gate |

The simulation runs multi-agent "rounds" where LLM-backed agents (teachers, school leaders, parents, policy officers, etc.) interact under a policy scenario, producing transcripts, state timelines, and outcome indicators. The entire pipeline from scenario definition through simulation run through export and analysis is now API-driven and can be triggered by a single natural-language question via the `/agent/ask` endpoint.

---

## 2. Build history: MVP through Iteration 18

### MVP 1.0
FastAPI backend with a React frontend and SQLite transcript persistence. Shipped `/simulations/run` (POST, background task), polling via `/simulations/{id}`, and a CSV export workflow. This was the working skeleton everything else is built on.

### Iterations 1–3: Interaction metadata, state engine, export API
Iteration 1 added structured interaction metadata per turn (`interaction_type`, `target_scope`, `target_agent_id`, `intent_tag`). Iteration 2 introduced a deterministic state engine with per-agent dimensions (`support_level`, `resistance_level`, `workload_stress`, `belief_posture`) and demographic profile fields, plus global round state snapshots and outcome indicators (`adoption_momentum`, `conflict_events`, `consistency_index`). Iteration 2 hardening added versioned prompt templates, a simulation failure guard, and `config_snapshot` persistence. Iteration 3 added `GET /simulations` (list), `GET /simulations/{id}/export.json` (full bundle), and `GET /simulations/{id}/export.zip` (CSVs). Frontend gained tabbed UI, run history, and compare-runs.

### Iteration 4: LLM router, YAML scenarios, context clipping
Structured `<state>{...json...}</state>` blocks appended by agents; `llm/state_parse.py` parses them. `llm/router.py` + `llm/claude_client.py` introduced `llm_provider` `lmstudio` | `anthropic`. YAML scenario registry in `scenarios/data/*.yaml` (PSLE MVP included). Context clipping (`llm/context_clip.py`) strips reasoning from peer context to avoid `n_ctx` exhaustion. Config: `llm_max_tokens`, `llm_provider`, `anthropic_api_key`, `peer_context_max_chars`.

### Iteration 5: RAG scaffold, FSBB scenario
Second YAML scenario `fsbb_comparator` with FSBB-themed policy events. RAG package (`mirofish_backend.rag/`): character chunking, cosine top-k retrieval, in-process embedding cache. Embeddings via LM Studio `/v1/embeddings`. Orchestrator injects "Reference excerpts" block into user prompt when `rag_effective`. Config: `RAG_ENABLED`, `EMBEDDING_MODEL`, `RAG_TOP_K`, `RAG_CHUNK_SIZE`. `config_snapshot` records RAG provenance.

### Iteration 6: Validity notes
SQLite `validity_notes` table with optional round-level scores (`face_score`, `construct_score`, `predictive_score`) and rubric text fields. `POST /simulations/{id}/validity-notes` and `GET /simulations/{id}` includes notes array. Export bundle and ZIP include validity notes. Frontend Validity tab.

### Iteration 7: Rich persona profiles, hybrid routing
Persona YAML extended with optional `psychological_profile` and `implementation_profile` nested maps. `llm_provider = hybrid`: `resolve_effective_provider` sends Anthropic on `turn_index == 1` each round (frontier anchors the opening broadcast), LM Studio for all others. `config_snapshot` records `hybrid_routing_policy`. Frontend Run tab optional LLM routing dropdown.

### Iteration 8: Live dashboard
Frontend Live tab with SVG sparklines and tables from `GET /simulations/{id}` — global readiness/alignment, adoption series, per-agent support/resistance/workload. Poll frequency reduced to ~750ms while running. Scale/cost doc added (`docs/plans/SCALE_LIMITS_AND_COST.md`).

### Iteration 9: Groups, factions, roster CSV
Optional `groups` field on personas and roster rows. `mirofish_backend.roster` parses and merges by 1-based slot. `POST /simulations/run` accepts `roster_csv`; `GET /simulations/roster-csv-template`. `agent_limit` 1–50. `group_ids` persisted on turns and state snapshots. Frontend: roster textarea, agent limit 50, warning >20 agents.

### Iteration 10: AgentContextV1, simulation modes
`AgentContextV1`: versioned per-agent bundle (`slot_index`, `demographics`, `group_ids`). `simulation_mode`: `full_round_robin` (default) | `sample_k_per_round` (deterministic subset per round via `random_seed` + round index; non-sampled agents skip LLM). `spoke_this_round` on state snapshots. ADR-001 Interface section updated.

### Iteration 11: Population pool CSV
`population/csv_population.py` — parse pool CSV; `weighted` / `stratified` draw without replacement. `POST /simulations/run` accepts `population_csv` and `population_sample_mode`. Merge order: population draw → roster overlay (roster wins). `config_snapshot` includes full population provenance trace.

### Iteration 12: Per-turn LLM traceability, export v3
`effective_provider` and `effective_model` persisted on each `agent_turns` row. `POST /simulations/run` returns `{ id, warnings[] }` for unknown group IDs. `export_version` bumped to `3`. `interaction_last_k` for `sample_k_per_round` cohort-scaled (capped 120). Stress test: 40 fake-LLM turns < 5s.

### Iteration 13: AgentContext v2 — structured attributes
`AgentContextV1` version `"2"`: `identity`, `attitudes`, `personal_history` dicts on each agent. YAML personas + population CSV v2 support these fields via `_json` columns. Prompts render structured sections. `attribute_sections_json` on `agent_state_snapshots`. `export_version` 4.

### Iteration 14: Researcher UX — attribute editor
Sectioned attribute editor in Scenario Wizard (identity / attitudes / personal_history). `POST /scenarios/{id}/llm-fill` endpoint: LLM populates attribute sections given a persona description. Constrained randomize from fixed vocabulary. Roster CSV `_json` columns parsed and merged. Frontend key-value editor with Show/Edit toggle. `toSectionMap` normalises any server shape safely.

### Iteration 15: IAD interaction rules + network topology
Named policy objects: `ChannelType`, `TurnOrderPolicy`, `VisibilityPolicy`, `InteractionOverlay`. `build_interaction_policy()` factory with upgrade rule (Trinidad → hierarchical). `apply_turn_order` (pure function), `visible_turns_for_agent` (broadcast / group / own-turn). `ScenarioConfig.interaction_overlay` bakes overlay into YAML. `config_snapshot.interaction_policy` sub-object with `policy_version = "1"`. All enum values now schema-driven.

### Iteration 16: Agent-ready API surface
Three new endpoints:
- `POST /scenarios/generate-from-brief` — brief → LLM → `validate_scenario_document` → scenario (422 + errors + `raw_llm_text` on failure).
- `GET /capabilities` — schema-driven: enum values from `interaction_policy.py` at runtime; no hard-coded strings.
- `POST /simulations/{id}/analyze` — stateless LLM analysis of completed run; two-stage context clipping; returns `key_findings`, `per_agent_summary`, `trajectory_narrative`, `suggested_follow_ups`.

Frontend: Scenario Wizard "Generate from brief" button hydrates the form.

### Iteration 17: Agent orchestration layer
Three endpoints: `POST /agent/plan`, `POST /agent/execute`, `POST /agent/ask` (+ SSE via `?stream=true`). Thin wrapper design — orchestrator reuses the same in-process functions the HTTP routes call (`queue_simulation_run`, `generate_scenario_from_brief`, `analyze_simulation_export`). Zero simulation logic duplicated. `build_capabilities_dict()` embedded in planner prompts at runtime. `validate_plan_against_capabilities` guards before execute. Demo script: `scripts/agent_ask_demo.py` (zero-dependency, `urllib` only). **108 tests passing.**

### Iteration 18 — latest PASS (2026-04-05)
**Minister / Agent UI.** `frontend/src/components/AgentConsole.tsx`:
- Primary **Ask** flow: research question → `POST /agent/ask` → structured per-run result cards.
- **Show execution plan (JSON)** after success; pre-loads Execute JSON editor.
- **Advanced** (collapsed): constraints, wait timeout, planner temperature, plan max tokens, Plan-only, Execute JSON.
- Cancel + elapsed-time indicator; client-side range validation on Advanced fields.
- `RunResultCard` shared for Ask and Execute result lists.
- API client (`api.ts`): `agentAsk`, `agentPlan`, `agentExecute` with optional `AbortSignal`.
- All tabs stay mounted (`display: none` when inactive) to preserve in-flight requests and form state.

**110 tests passing, 1 skipped.** Frontend build clean.

**Deferred from Iteration 18:** SSE live log in the browser (SSE remains `curl`/manual); auto-loading Agent-returned `simulation_id` into the Run tab poll state.

### Planned (not yet built)

| Iteration | Theme |
|-----------|-------|
| **19** | Parallel LLM within rounds (`asyncio.gather`, concurrency cap ~4); stress tests for determinism and error isolation |
| **20** | Population scale >50; aggregation mode |

---

## 3. Grant proposal discussion (2026-04-06)

### Background
Mark is applying for a **small internal MOE research seed grant** (~SGD 5,000–20,000) covering **January–December 2027**. The primary motivation is to **legitimise the MiroFish work** in front of Ministry bosses and peer researchers, not primarily to obtain funds. He also wants to present at the **annual MOE research conference in October 2026** — so much of the actual simulation work will be done in 2026 (before the official grant window opens). The timelines are intentionally misaligned and that is fine.

### What is realistic in 2026 vs the full thesis

The PhD thesis has three phases:
- **Phase 1 (Year 1):** Retrospective simulation validation — use Singapore education policy cases, compare simulation outputs to known outcomes, assess face/construct/predictive validity. **→ This is what MiroFish is already doing. Phase 1 work is completable Apr–Oct 2026.**
- **Phase 2 (Year 2):** Fine-tune a locally-grounded LLM for Singapore governance context (LoRA, RAG, hybrid). Requires corpus assembly and comparative validation. Genuine 12+ month effort.
- **Phase 3 (Year 3):** Simulate policy evaluations (RCTs, quasi-experiments, developmental evaluation); produce governance guidelines; expert feedback rounds. Cannot be compressed.

**Honest assessment: the full thesis cannot be completed in a few months. Phase 1 can.** The grant covers a well-scoped Phase 1 pilot study, and the Jan–Dec 2027 window is for formalising, extending, and publishing what was piloted in 2026.

### Key decisions from this conversation

1. **Do not reorganise `docs/`.** Opus had suggested a new `system/state/iterations/templates` folder layout. Mark and the Cursor architect agreed the existing system (`SESSION_STATE.md` + `docs/handoffs/` + `docs/iterations/`) is working well and should not be disturbed.

2. **Grant framing:** Standalone pilot study, explicitly noting it is "part of a larger study" (the PhD). The form allows this and it is honest.

3. **Proposed title:** *Piloting LLM Multi-Agent Simulation for Pre-Implementation Policy Analysis in Singapore Education*

4. **Trinidad's framework data:** Mark conducted a qualitative school case study last year using Trinidad's (2024) structural/network/ecological framework. He has interview data and document analysis from that case. This is the empirical seed: the profiles and interaction patterns from the case study become the YAML persona configurations in MiroFish.

### Proposed grant proposal outline (Sections A–J)

**A — Abstract (200 words)**
Pilot validation study. Seeds LLM agent profiles from a qualitative school case study (Trinidad's framework). Runs retrospective simulation of one Singapore education policy case. Assesses face, construct, and predictive validity against documented outcomes. Produces preliminary governance guidelines for internal MOE use of LLM simulation.

**B — Research objectives**
1. Develop a replicable methodology for constructing LLM agent profiles from qualitative field data structured via Trinidad's framework.
2. Validate simulation outputs against known implementation dynamics in a Singapore education policy case (PSLE reform or FSBB).
3. Produce preliminary governance guidelines for responsible internal MOE use of LLM simulation as a decision-support tool.

State explicitly: "This proposal is part of a larger study" — Mark's ANU PhD candidature.

**C — Research questions**
1. To what extent can LLM agents seeded with school-level qualitative field data reproduce known patterns of policy interpretation and implementation resistance?
2. How should face, construct, and predictive validity be assessed for LLM simulation in Singapore education contexts?
3. What governance conditions are necessary for MOE to responsibly use LLM simulation as an internal decision-support tool?

**D — Impetus / literature review (≤1000 words)**
Anchor on: Lipsky (2010) street-level bureaucracy → Trinidad (2024) structural/network/ecological framework for school-level implementation → classical ABM limits (Axelrod, Epstein) → generative ABM turn (Park et al. 2023; Ghaffarzadegan et al. 2024) → LLM simulation in policy (Li, Das & Shirado 2025) → Singapore AI governance (IMDA 2024, 2026) → gap: existing frameworks govern AI deployment to the public; none address how government bodies should govern their own internal use of simulation as evidence for policy decisions.

**E — Methodology and design**
Three-stage design:
1. *Profile construction* — translate Trinidad case study interviews and document analysis into MiroFish YAML persona configs (structural role, network position, ecological context → `identity`, `attitudes`, `personal_history` fields).
2. *Simulation runs* — retrospective simulation of one Singapore education policy case; multiple configurations (RAG corpus from public documents, interaction policy variants); transcripts and state timelines produced.
3. *Validity assessment* — structured comparison of simulated vs documented stakeholder responses (parliamentary debates, media, academic sources); score face / construct / predictive validity; document failure modes and simulation limits.

Sampling: purposive selection of one policy case with well-documented implementation dynamics (PSLE reform or FSBB are natural candidates — confirm with Mark's supervisors). Data analysis: qualitative comparative analysis of simulated vs documented responses.

**F — Utility and deliverables**
- Practical: a reusable pre-implementation analysis methodology for MOE policy officers.
- Governance: preliminary guidelines for responsible internal use (what simulation can and cannot substitute; human oversight requirements; accountability for simulation-informed decisions).
- Academic: conference paper at the Oct 2026 MOE annual research conference; journal submission (target: *Asia-Pacific Education Researcher* or *Journal of Policy Analysis and Management*).
- Open-source: MiroFish YAML configuration templates for Singapore education policy contexts.

**G — Research team**
Mark Lee Ser Ming (PI). Research assistance may be engaged for document coding or validity scoring if budget permits.

**H — Research mentors**
A/Prof Michael Di Francesco (primary, ANU Crawford — public administration reform, policy implementation). A/Prof Mark Chou (secondary, ANU Crawford — political theory, AI governance and normative dimensions). Optionally, a senior MOE research officer as internal mentor.

**I — Project implementation schedule (Jan–Dec 2027)**

| Period | Milestone |
|--------|-----------|
| Jan–Feb 2027 | Methodology write-up; ethics review (if needed for retrospective data) |
| Mar–Apr 2027 | Profile construction from Trinidad case data; scenario YAML configuration |
| May–Jun 2027 | Simulation runs; iterative refinement |
| Jul–Aug 2027 | Validity assessment; comparative analysis against documented outcomes |
| Sep–Oct 2027 | Governance guidelines draft; expert review round |
| Nov–Dec 2027 | Final report; journal submission; open-source release of MiroFish configs |

*Narrative note:* Preliminary simulation runs were completed in 2026 as part of doctoral fieldwork; this grant formalises, extends, and publishes that pilot.

**J — Funding details**

| Item | Estimate (SGD) |
|------|---------------|
| Anthropic API credits (frontier-model simulation runs) | 1,000–3,000 |
| Research assistance (document coding / validity scoring) | 2,000–5,000 |
| Conference travel / registration (if any in-person component in 2027) | 500–1,000 |
| **Total** | **~3,500–9,000** |

Hardware (Mac mini + LM Studio) is already owned — no grant cost.

---

## 4. What Opus should pick up

**Primary ask:** Help Mark draft each grant proposal section (A–J) as actual prose, suitable for submission to the MOE internal grant committee.

**Key source materials:**
- Thesis proposal PDF in repo root: `3-Thesis_Proposal-Lee_Ser_Ming_Mark copy.docx.pdf` — primary source for literature review citations and methodology framing. Opus should read this before drafting Sections D and E.
- The outline above provides the section-by-section structure and key arguments.

**Before drafting Sections A, B, C, and E, Opus should ask Mark:**
- Which school was the Trinidad case study conducted at, and which policy was studied? (Need to know whether it is PSLE reform, FSBB, or something else, and what level of school — primary, secondary, JC.)
- What are the key themes from the case study? (What implementation patterns or resistance dynamics emerged? These become the agent behaviour expectations the simulation will be validated against.)
- Is ethics review required for retrospective use of the interview data in the grant write-up, or is it already covered under a prior approval?

**Keep distinct:**
- The **Oct 2026 conference paper** — early output of the 2026 simulation pilot; shorter and more descriptive; Mark will produce this independently.
- The **Jan–Dec 2027 grant** — formalises and extends the pilot; produces the full methodology write-up, validity report, and governance guidelines.

**On the MiroFish build side:** Mark is continuing development through Iterations 19–20 (parallel LLM, population scale) in parallel to the grant write-up work. These are separate threads; Opus should not conflate them unless Mark asks.

---

*Document prepared by Cursor architect session, 2026-04-06. Cross-reference: `docs/SESSION_STATE.md` (last gate: Iteration 18, 2026-04-05).*

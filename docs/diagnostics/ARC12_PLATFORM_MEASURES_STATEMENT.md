# Arc 12 platform-measures statement (Ops input for GM-F)

**Purpose:** Inventory what Senna **actually measures** after Arcs 9–12, at study configuration, so GM-F can draft the scoring system (ARC12 §4) against platform reality — **not** against assumed measures.

**Audience:** GM-F (scoring criterion author). **Not** a scoring rubric, proposition list, threshold, or judge protocol.

**Product state:** `export_version` **14** (`backend/src/mirofish_backend/export_bundle.py`); platform closeout through **senna-iter-56** (`adb2763`).

**Scoring system (GM-F delivered):** [`SSTRF_RQ1_SCORING_SYSTEM_V2.md`](../research/SSTRF_RQ1_SCORING_SYSTEM_V2.md) — supersedes the misread in §1 below.

---

## 0. Correction — build rule vs study scoring (GM-F, 2026-08-25)

Earlier drafts of this document (§1, §4, §7) stated that scoring must **never use correspondence with CIEPSS**. That **misread** the Arc 11 non-negotiable.

| Context | Rule |
|---------|------|
| **Platform development (Arc 11)** | Judge *builds* on platform measures — **never** select architecture by whether it reproduces a study case (fitting to the test set). |
| **Study scoring (RQ1)** | The study's purpose **is** correspondence with CIEPSS dynamics. Propositions are CIEPSS findings; raters judge whether simulation evidence exhibits them. |

**Still prohibited:** lexical matching, string overlap, embedding similarity to CIEPSS source text. Raters score dynamics from transcripts + elicitation against proposition statements — **not** against shown CIEPSS source text.

**Not correspondence instruments** (diagnostic only, excluded from proposition scoring): MemBench, architectural interview. See GM-F §0 instrument table.

---

## 1. Scope

| Term | Definition |
|------|------------|
| **Study trial** | One completed `simulation_run` using scenario **`ciepss_school_b`**, 8 agents, Anthropic tier, documented CIEPSS network, `network_bounded` visibility — the iter-55 RQ1 rehearsal profile |
| **Post-run diagnostics** | Scripts run **after** the live simulation (architectural interview, MemBench adapter, ablation summaries) — not part of the orchestrator loop unless explicitly invoked |
| **External judge** | GM-F v2 correspondence scoring via judge harness on product `main` (`scripts/sstrf_scoring_*.py`, iter-57 `177306a`) — not orchestrator output |

**Arc 11 build rule:** Platform development judges **build on platform measures** — not on whether a configuration reproduces a study case. **Study scoring** (GM-F v2) judges correspondence with CIEPSS **dynamics** from transcript + elicitation evidence via rubric — never lexical overlap with source text.

**Standing constraint (Arc 12):** iter-54–56 runs are **rehearsal / calibration**, not study-validity runs. This document describes **measure availability**, not study outcomes.

---

## 2. How to retrieve measures

| Channel | Endpoint / artifact | Notes |
|---------|---------------------|--------|
| **Export JSON** | `GET /simulations/{id}/export.json` | Top-level `export_version`; nested tables below |
| **Export ZIP** | `GET /simulations/{id}/export.zip` | CSV mirrors of bundle tables + `memory_context_summary.json` |
| **Live API** | `GET /simulations/{id}` | Run status, `transcript`, `state_timeline`, `economics`, `converged_at_round` |
| **SQLite** | `simulation_runs`, `agent_turns`, `agent_state_snapshots`, `global_state_snapshots`, … | Same fields as export; source of truth for rehearsal extraction |

**Bundle top-level keys** (from `get_simulation_export_bundle`):

`run`, `transcript`, `agent_state_snapshots`, `global_state_snapshots`, `round_outcomes`, `state_timeline`, `outcome_indicators`, `validity_notes`, `likert_responses`, `memory_context_log`, `memory_context_summary`, `architectural_interview_responses`, `architectural_interview_scores`, `agent_reflections`

`run.economics` is attached at export time (export v8+).

---

## 3. Per-trial measure inventory

For each measure: **what**, **format**, **provenance**, **when produced**, **availability**.

### 3.1 Transcript turns (live orchestrator)

| | |
|--|--|
| **What** | Each agent LLM turn: prompt, response, interaction metadata, token usage, state-extraction provenance, optional importance |
| **Format** | List of objects; key fields: `round_number`, `turn_index`, `agent_id`, `agent_role`, `agent_name`, `interaction_type`, `target_scope`, `target_agent_id`, `raw_prompt`, `raw_response`, `latency_ms`, `group_ids`, `effective_provider`, `effective_model`, `effective_profile_id`, `fidelity_tier` (1=LLM, 2=partial, 3=heuristic), `input_tokens`, `output_tokens`, `state_update_source`, `importance_score`, `importance_source` |
| **Provenance** | Table `agent_turns`; export `transcript`; ZIP `agent_turns.csv`; export v3 (provider/model), v6 (`fidelity_tier`), v8 (tokens), v12 (`importance_*`) |
| **When** | Per turn, during run |
| **Availability** | Always (every LLM/heuristic turn). **`importance_score` / `importance_source`** only when `importance_scoring_enabled` (config + request); **off** on iter-55 study rehearsal |

**`state_update_source`** (iter-52+): how float state was derived from `raw_response` — e.g. `model_parsed`, `keyword_fallback`. iter-55 RQ1: **100% `model_parsed`** on all LLM turns.

---

### 3.2 Agent float state (live orchestrator)

| | |
|--|--|
| **What** | Continuous attitude/stress state per agent per round |
| **Format** | Floats in **[0, 1]**: `support_level`, `resistance_level`, `workload_stress`; string `belief_posture`; optional persona attrs (`age`, `sex`, `ethnicity`, `ses`), `attribute_sections` (JSON), `spoke_this_round`, `group_ids` |
| **Provenance** | Table `agent_state_snapshots`; export `agent_state_snapshots`; ZIP `agent_state_snapshots.csv`; v4 (`attribute_sections`) |
| **When** | End of each round (snapshot after all turns in round) |
| **Availability** | Always |

**Derived (export):** `cohort_summary` — per `group_id` × round: `agent_count`, `spoke_count`, `avg_support_level`, `avg_resistance_level`, `avg_workload_stress` (computed from snapshots, v5).

**Study-rehearsal dispersion signal:** final-round `support_level` stdev across agents (computed offline from snapshots) — iter-55 range **0.017–0.071** ([`ARC12_STUDY_REHEARSAL_RESULTS.md`](./ARC12_STUDY_REHEARSAL_RESULTS.md)).

---

### 3.3 Likert self-report (iter-40)

| | |
|--|--|
| **What** | Round-end ordinal self-report per indicator, mapped to float, compared to engine float state (`divergence`) |
| **Format** | Rows: `round_number`, `agent_id`, `indicator` (default: `support`, `resistance`, `workload_stress`), `anchor_label`, `ordinal_value` (1–6), `mapped_float`, `source`, `float_value`, `divergence`, token fields on LLM call |
| **Provenance** | Table `agent_round_likert`; export `likert_responses`; ZIP `agent_round_likert.csv`; export v9 |
| **When** | End of each round (one LLM call per agent per round when enabled) |
| **Availability** | Only if `likert_self_report_enabled` on scenario **or** request override, **and** scenario has six `likert_anchor_labels` per indicator |

**Study profile:** `ciepss_school_b` has Likert **off** (no `likert_self_report_enabled` in scenario YAML). iter-55 runs: **not exercised**. Convergence (§3.8) uses float state only (D2) — Likert does not drive stopping.

---

### 3.4 MemBench adapter (iter-46) — post-run diagnostic

| | |
|--|--|
| **What** | Offline memory QA accuracy on vendored MemBench trajectories: **participation** vs **observation** × **factual** vs **reflective** cells |
| **Format** | JSON report from `scripts/membench_adapter.py` → `run_membench_suite()`: nested `participation` / `observation` each with `factual` / `reflective` `{ accuracy, correct, total, … }`; plus `seed`, `answer_mode`, `fixtures_dir` |
| **Provenance** | **Not** in standard export bundle by default; stored in Arc 10/11 diagnostic summaries (`arc10_baseline`, `arc11_ablation`) when harness runs MemBench |
| **When** | Post-run script (`run_membench_suite` or canonical recompute path in `diagnostics/arc10_canonical.py`) |
| **Availability** | Requires explicit harness invocation; fixtures at `backend/tests/fixtures/membench/`. **Not run** on iter-55 study rehearsal |

**Note:** MemBench measures **adapter/memory QA** on benchmark fixtures — not in-simulation recall of CIEPSS dialogue.

---

### 3.5 Architectural interview (iter-47) — post-run diagnostic

| | |
|--|--|
| **What** | Park et al. five-category post-simulation interview + judge scores |
| **Format** | **Responses:** `agent_id`, `category` (`self_knowledge`, `memory_retrieval`, `planning`, `reaction`, `reflection`), `question_text`, `response_text`, interview model metadata, tokens. **Scores:** integer **0–2** per response, `score_label`, `rationale`, judge model metadata, `parse_source`, `rubric_version` (`"1"`) |
| **Provenance** | Tables `architectural_interview_responses`, `architectural_interview_scores`; export keys of same name; ZIP CSVs; export v11. Administered via `scripts/run_architectural_interview.py` |
| **When** | Post-run (not in live orchestrator) |
| **Availability** | Empty unless interview script run. Rubric doc: [`ARCHITECTURAL_INTERVIEW_RUBRIC.md`](./ARCHITECTURAL_INTERVIEW_RUBRIC.md). Judge profile configurable (same stack as run LLM profiles) |

**Between-agent dispersion:** per-category stdev of scores across agents (used in Arc 11 ablation reports) — **not** run at study scale in iter-55.

---

### 3.6 Memory context instrumentation (iter-45)

| | |
|--|--|
| **What** | Per candidate prior turn: was it included in the assembling agent's prompt, and why not |
| **Format** | **Log rows:** `round_number`, `observer_agent_id`, `candidate_turn_id`, `included`, `exclusion_reason` (`recency_cut`, `visibility_policy`, `char_budget_truncated`, `same_round_peer`, …), `target_scope`, `char_truncated`, `retrieval_signals` (JSON, v13 when weighted retrieval on). **Summary:** `record_count`, `exclusion_breakdown` counts, `total_turns`, `group_addressed_turns`, **`group_addressed_proportion`** |
| **Provenance** | Table `memory_context_log`; export `memory_context_log` + `memory_context_summary`; ZIP `memory_context_log.csv`, `memory_context_summary.json`; export v10 (+ v13 retrieval signals) |
| **When** | Per turn during run (instrumentation parallel to prompt build) |
| **Availability** | Always logged at study scale. Weighted retrieval signals only when `weighted_retrieval_enabled` — **off** on iter-55 |

**iter-55 evidence:** `group_addressed_proportion` = **0.25** all six runs; `char_budget_truncated` **0–6** per run ([`senna-iter-55-closeout.md`](../iterations/senna-iter-55-closeout.md) §2.7).

---

### 3.7 Agent reflections (iter-51)

| | |
|--|--|
| **What** | Periodic agent-generated reflection text tied to source turns and accumulated importance |
| **Format** | Rows: `agent_id`, `round_number`, `reflection_text`, `source_turn_ids`, `accumulated_importance`, `parse_source`, `reflection_prompt_version`, tokens |
| **Provenance** | Table `agent_reflections`; export `agent_reflections`; ZIP when non-empty; export v14 |
| **When** | During run when reflection trigger fires |
| **Availability** | Only when `reflection_enabled` — **off** on iter-55 interim flags |

---

### 3.8 Global state, round outcomes, convergence (iter-28)

| | |
|--|--|
| **What** | Population-level round metrics; optional early-stop signal |
| **Format** | **`global_state_snapshots`:** `round_number`, `implementation_readiness`, `alignment_index`, **`convergence_delta`** (float, null round 1). **`round_outcomes`:** `adoption_momentum`, `conflict_events`, `consistency_index`. **Run row:** `converged_at_round` (int or null) |
| **Provenance** | Tables `global_state_snapshots`, `round_outcomes`, `simulation_runs.converged_at_round`; export + ZIP `global_state_snapshots.csv`; v7 |
| **When** | End of each round (`convergence_delta` from round 2+) |
| **Availability** | `convergence_delta` always **computed and stored**; early stop only if `convergence_threshold` set at run start |

**`convergence_delta` definition:** mean over agents of mean abs Δ in `support_level`, `resistance_level`, `workload_stress` vs prior round (float only, not Likert).

**iter-55:** threshold **not set** — all runs completed full 15/20 rounds. Calibration doc: [`ARC12_CONVERGENCE_CALIBRATION.md`](./ARC12_CONVERGENCE_CALIBRATION.md) — recommends **τ = 0.02**, patience **2**.

---

### 3.9 Run economics (iter-29; pricing iter-56)

| | |
|--|--|
| **What** | Token totals and USD estimate from per-turn billing |
| **Format** | `run.economics`: `total_input_tokens`, `total_output_tokens`, `estimated_cost_usd`, `llm_provider`, `tier_breakdown` (`tier_1/2/3_turns`, optional `likert_self_report_turns`) |
| **Provenance** | `simulation_runs.total_*_tokens`; `build_run_economics_payload()`; export v8; per-turn billing via `effective_profile_id` → `pricing_key` (per-model after iter-56 Part A) |
| **When** | Aggregated post-run (per-turn tokens during run) |
| **Availability** | Always for completed runs with usage metadata |

**Study cost table:** [`ARC12_STUDY_COST_TABLE.md`](./ARC12_STUDY_COST_TABLE.md). iter-55 recorded **$15.90** at generic Anthropic rates; Haiku 4.5 list-rate retroactive ≈ **$5.30**.

---

### 3.10 Validity notes and sampling audit

| | |
|--|--|
| **What** | Engine-generated validity warnings; per-run sampling roster audit |
| **Format** | **`validity_notes`:** rater-style rows (face/construct/predictive scores — optional manual entry). **`config_snapshot.sampling_audit`:** per-agent `agent_id`, `persona_id`, `fidelity_tier`, strategy metadata |
| **Provenance** | Table `validity_notes`; export v2; `run.config_snapshot` |
| **When** | Validity notes: optional during/after run; sampling audit: run start |
| **Availability** | Validity notes often empty; sampling audit always in snapshot for census runs |

---

### 3.11 `config_snapshot` (full reproducibility)

| | |
|--|--|
| **What** | Frozen run configuration for replication and pre-registration |
| **Format** | JSON on `run.config_snapshot` — includes: `scenario_id`, `scenario_source`, seeds, rounds, `llm_provider`, model profile ids, `anthropic_model`, interaction policy (`visibility_policy`, `visibility_effective`, network CSV flags), RAG fields, mechanism flags (`likert_*`, `importance_scoring_*`, `weighted_retrieval_*`, `reflection_*`), `working_memory_last_k`, `peer_context_max_chars`, `convergence_threshold` / `convergence_patience`, preflight estimate, population/network CSV provenance, etc. |
| **Provenance** | `simulation_runs.config_snapshot`; export `run.config_snapshot` |
| **When** | Written at run queue; `converged_at_round` merged on early stop |
| **Availability** | Always |

**iter-55 snapshot highlights:** `claude-haiku-4-5-20251001`, all memory mechanisms **false**, `network_csv_applied` true, `convergence_threshold` null.

---

## 4. What the platform does **not** measure

| Gap | Detail |
|-----|--------|
| **Proposition-level scores (P1–Pn) in product** | Not produced by orchestrator; GM-F v2 criterion implemented in judge harness on product `main` (iter-57 Part B, `177306a`, 56 tests in `test_sstrf_rq1_scoring.py`) |
| **Lexical CIEPSS matching** | Never — correspondence is dynamic/rubric-based, not string overlap |
| **Blind plausibility ratings** | Arc 9 packet pipeline exists on **study repo** (iter-42); not product-orchestrator output |
| **RQ2 actor scale** | ~20 documented actors + synthetic remainder **not rehearsed** — iter-55 `--skip-rq2` |
| **MemBench / interview at study scale** | Adapters exist but were **not executed** on iter-55 six runs |
| **Likert on study scenario** | Off for `ciepss_school_b` in current fixture |
| **Mechanism-mediated memory** | Importance, weighted retrieval, reflection **off** in iter-55/56 interim config (GM-F pending) |
| **Human rater panels** | Not in product — protocol is GM-F / study-repo scope |

---

## 5. Study-rehearsal evidence (mechanics only)

| Artifact | Validates |
|----------|-----------|
| [`arc12_study_rehearsal_results.json`](./arc12_study_rehearsal_results.json) | Tokens, cost, wall-clock, QA, memory breakdown, dispersion, state provenance at 8×15/20 |
| [`ARC12_STUDY_REHEARSAL_RESULTS.md`](./ARC12_STUDY_REHEARSAL_RESULTS.md) | Human-readable mechanics summary |
| [`ARC12_CONVERGENCE_CALIBRATION.md`](./ARC12_CONVERGENCE_CALIBRATION.md) | `convergence_delta` series; τ = 0.02 recommendation |
| [`ARC12_STUDY_COST_TABLE.md`](./ARC12_STUDY_COST_TABLE.md) | Funder-facing cost at study config |
| [`ciepss_school_b_provenance.json`](./ciepss_school_b_provenance.json) | Scenario seed provenance |
| [`senna-iter-55-closeout.md`](../iterations/senna-iter-55-closeout.md) | ARC12 §2 findings synthesis |
| [`senna-iter-56-closeout.md`](../iterations/senna-iter-56-closeout.md) | §3 DoD closure |

---

## 6. RQ1 scoring harness (product `main`, iter-57 Part B)

**Location:** product repo `main` — `scripts/sstrf_scoring_*.py`, `scripts/sstrf_rq1_scoring.py`,
`backend/tests/test_sstrf_rq1_scoring.py` (commit `177306a`, **56 tests**).

**Status:** GM-F scoring system v2 **implemented** (iter-57 Part B). Calibration content C1–C5,
per-agent scoring (17 judgements/trial), rater packet leakage checks, adjudication, and
aggregation per [`SSTRF_RQ1_SCORING_SYSTEM_V2.md`](../research/SSTRF_RQ1_SCORING_SYSTEM_V2.md).

**Interface:** Consumes elicitation JSON + export bundles; does not define proposition text or
thresholds (GM-F document is authoritative).

**Study-repo note:** Arc 9 iter-43 originally delivered on `sstrf-local`; product `main` now hosts
the v2 harness with synthetic fixtures (iter-43 pattern).

---

## 7. Handoff to GM-F — use when drafting scoring

Checklist for scoring-system design (D1):

1. **Bind propositions to correspondence evidence** — per GM-F v2: elicitation responses + transcripts for raters; float state supporting only; MemBench/interview excluded from scoring. No lexical CIEPSS overlap.
2. **Respect study profile switches** — `ciepss_school_b` today: Likert off, mechanisms off, 8 agents, network-bounded; convergence recommend τ = 0.02 if early stop used.
3. **Separate live vs post-run** — orchestrator delivers §3.1–3.3, 3.6–3.11 during run; §3.4–3.5 require explicit post-run scripts.
4. **Price and horizon** — use [`ARC12_STUDY_COST_TABLE.md`](./ARC12_STUDY_COST_TABLE.md) for RQ1 economics; RQ2 row empty until fixture exists.
5. **P5 and compound propositions** — platform provides judge **inputs** (transcript + diagnostics); structural reachability of score levels is a **criterion design** question (Phase V note in ARC12 §4).
6. **Pre-reg (iter-58)** — [`PREREG_SSTRF_RQ1_V2.md`](../research/PREREG_SSTRF_RQ1_V2.md) drafted; study seeds and platform freeze in [`ARC12_PLATFORM_FREEZE.json`](./ARC12_PLATFORM_FREEZE.json) — **Mark signature** before study output.

**Ops next step:** iter-58 freeze complete — await **Mark signature** on pre-reg v2, then execute validity trials under frozen config.

---

*Document: senna-iter-57 Part A; updated senna-iter-58 Part B (freeze housekeeping).*

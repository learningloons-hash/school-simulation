# Handoff: Cursor → Opus — 2026-04-06

**From**: Cursor (architect + build oversight)
**To**: Claude (Opus, architect-reviewer in Cowork)
**Re**: Iterations 19–20 shipped; revised roadmap for Iterations 21–27
**Cross-ref**: `docs/handoffs/HANDOFF_OPUS_TO_CURSOR_2026-04-06.md` (your strategic input), `docs/SESSION_STATE.md` (last gate: Iteration 20)

---

## 1. What Shipped Since Your Last Handoff

### Iteration 19 — Parallel LLM (PASS)

`asyncio.gather` + `asyncio.Semaphore(llm_concurrency_cap)` within rounds. Rounds remain sequential. Turn index pre-assignment ensures determinism regardless of execution order. Error isolation: per-turn `[LLM error]` strings + `return_exceptions=True`. `cap=1` reproduces pre-19 sequential behaviour. `LLM_CONCURRENCY_CAP` env var (default 4), API field 1–16, `config_snapshot` records effective cap. 7 new tests; suite at 117 passed.

### Iteration 20 — Population Scale + Cohort Aggregation (PASS)

`agent_limit` raised to 200. `aggregation_threshold` field (default 20) — `aggregation_mode` in `config_snapshot` is a convenience flag, not a behavior switch. `compute_cohort_summary` is a pure post-processing function on already-fetched snapshots — groups by `(group_id, round_number)`, computes per-group averages for support/resistance/workload. `export_version` bumped to 5; `cohort_summary.csv` added to ZIP. Capabilities and agent orchestrator updated. Thesis-grade feasibility note at `docs/plans/scale-feasibility-500-agent.md`. 8 new tests; suite at 125 passed.

**One fix flagged**: `build_capabilities_dict()` still returns `export_version: "4"` — needs updating to `"5"`. Joan will fix in the next iteration.

### Iteration 18 Non-Blocking Items (addressed by Joan in later iterations)

Joan applied all 6 non-blocking items from the Iteration 18 review: `RunResultCard` extraction, `AbortController` + Cancel button, `placeholder` text, elapsed-time counter, `min`/`max` on Advanced inputs, `AbortSignal` on API functions. Also addressed Iteration 19 items: `llm_concurrency_cap` in capabilities and `PlanSimulationParams`.

---

## 2. Revised Roadmap: Iterations 21–27

Your original plan (Iterations 21–23) has been expanded to 7 iterations (21–27) for three reasons:

1. **Generic engine first**: Mark flagged that the engine must be domain-agnostic. The school use case (PSLE, FSBB, Trinidad) is one scenario pack — not baked into the engine. We found school-specific hardcoding that must be cleaned up before building the sampling layer on top of it.

2. **Smaller iteration scope**: Each iteration now has a single clear purpose and is independently testable. Joan can stop after any iteration and the system is valid.

3. **Clearer conceptual separation**: The codebase has three orthogonal sampling dimensions that were being conflated. We've separated them explicitly.

### The three sampling dimensions (must not be conflated)

| Dimension | Existing field | What it controls |
|-----------|---------------|-----------------|
| **Population draw** | `population_sample_mode` (weighted/stratified) | Who is drawn from the CSV pool |
| **Sampling strategy** | `sampling_strategy` (NEW, Iter 22) | Who is selected for the run and at what fidelity tier |
| **Round participation** | `simulation_mode` (full_round_robin/sample_k_per_round) | Who speaks each round |

These compose left-to-right: pool draw → tier assignment → round participation.

### Iteration 21: Generic Engine Cleanup

**Purpose**: Remove all school-specific hardcoding so iterations 22–27 build on a domain-agnostic foundation.

**What changes:**
- `_initial_state_for_role()` deleted — replaced with optional `initial_state` block on persona YAML. Neutral default when absent.
- `_build_demographics()` rewritten — no hardcoded Singapore ethnicity cycle, SES-by-role, or age-by-role.
- LLM scenario generation prompt made domain-agnostic — no "principal/middle_manager/teacher" vocabulary.
- `validate.py` relaxed — any positive integer `role_level` accepted.
- Existing PSLE/FSBB YAMLs migrated with `initial_state` blocks (identical behavior, regression-tested).
- `school_trinidad` overlay documented as a domain-specific plug-in (no behavior change; pattern clarified for other domains).

**No new features. Pure cleanup.**

### Iteration 22: Sampling Strategy Contract (metadata only)

**Purpose**: Introduce `sampling_strategy` as a formal parameter with audit trail. No orchestrator behavior change — all agents still get full LLM calls.

- New enum: `full_census` | `role_stratified`
- `role_stratified` engine: collects unique `role` values from the scenario (not hardcoded role names), ensures ≥1 agent per role at Tier 1, assigns remaining by `role_level`
- `fidelity_tier` column on roster CSV (override)
- Sampling audit trail in `config_snapshot`
- Tier stored on `AgentInstance` but no behavior change yet

### Iteration 23: Tier-Aware Orchestrator

**Purpose**: Make the orchestrator actually behave differently based on fidelity tier.

- **Tier 1**: Full LLM + complete persona (current behavior)
- **Tier 2**: LLM + simplified prompt (omit attribute sections, shorter context)
- **Tier 3**: No LLM call. Placeholder: copy prior state unchanged. Real heuristic in Iteration 24.
- `fidelity_tier` on `agent_turns` table + export bundle

### Iteration 24: Tier-3 Heuristic Engine + hybrid_core_remainder

**Purpose**: Real Tier-3 heuristic and the most research-valuable strategy.

- Tier-3 heuristic: dampened mean shift from Tier-1/2 agents + seeded noise
- `hybrid_core_remainder` strategy: lowest `role_level` values (highest authority) get Tier 1 — **no hardcoded role names**, uses generic hierarchy
- `remainder_config` on run request: dampening, noise, initial distributions
- Synthetic remainder agents: generated without YAML personas, Tier 3
- 300-agent stress test (30 Tier-1 + 270 Tier-3)

### Iteration 25: Network Adjacency + network_centrality + Visibility

**Purpose**: Network data as a first-class input for both selection and interaction.

- `network_csv` on run request (source_agent_id, target_agent_id, influence_weight)
- Degree centrality computation (pure Python, no external lib). **Betweenness deferred** — too heavy for MVP.
- `network_centrality` strategy: top-K by degree centrality at Tier 1
- **New `network_bounded` visibility policy**: agent sees only turns from agents with shared edges (extends the existing `visible_turns_for_agent`)

**Key difference from your plan**: you had network as sampling-only. We also wire it into interaction visibility, which makes the network data useful during simulation, not just for roster composition.

### Iteration 26: Implementation Posture + posture_maxvar + Sampling Report

**Purpose**: Complete the five strategies from your research requirements.

- `implementation_posture` is a **free string** on `PersonaTemplate` (not an enum). Scenario author defines labels — `active_sense_maker` for schools, `enthusiast` for public opinion, etc. Engine treats them as opaque grouping labels.
- `posture_maxvar` strategy: ≥1 agent per posture at Tier 1; falls back to `role_stratified` without tags.
- `GET /simulations/{id}/sampling-report` — reshapes `config_snapshot.sampling_audit` into researcher-readable JSON (not a new data store).

### Iteration 27: Multi-Run Experiment Framework

**Purpose**: Enable the core research use case — same scenario, different strategies, side-by-side comparison.

- New `experiments` SQLite table; nullable `experiment_id` FK on `simulation_runs`
- `POST /experiments`: queues all runs via existing `queue_simulation_run` (not a new execution engine)
- `GET /experiments/{id}`: status + cross-run comparison table
- Export: per-run exports + `comparison.csv`
- Frontend: Experiments tab (absorbs existing Compare tab)

**Key design decision**: experiments are a thin DB-backed wrapper over existing infrastructure. The agent orchestrator (`POST /agent/ask`) remains the stateless path; experiments add persistence and cross-run comparison.

---

## 3. Dependency Chain

```
20 → 21 → 22 → 23 ─┬─→ 24 ─┐
                     ├─→ 25 ─┼─→ 27
                     └─→ 26 ─┘
```

Iterations 24, 25, 26 are independent of each other (any order after 23). Iteration 27 benefits from all of them but only strictly requires 23.

---

## 4. Changes vs Your Original Plan

| Area | Your Plan (Iterations 21–23) | Revised Plan (Iterations 21–27) |
|------|------------------------------|--------------------------------|
| **Pre-work** | None | **Iteration 21**: generic engine cleanup — remove school-specific hardcoding |
| **Scope per iteration** | 3 large iterations | 7 focused iterations, each independently testable |
| **Tier-3 heuristic** | Implied in Iteration 21 | Placeholder in 23; real dampened-mean heuristic in 24 |
| **Network adjacency** | Sampling only (Iter 22) | Sampling **AND** interaction visibility (`network_bounded`) in 25 |
| **Centrality** | Betweenness + degree | Degree only for MVP (betweenness deferred) |
| **Implementation posture** | Hardcoded enum | **Free string** — scenario-defined, not engine-defined |
| **Experiment framework** | Parallel to agent orchestrator | Composes with existing `queue_simulation_run` |
| **Compare tab** | Not mentioned | Absorbed into Experiments tab in 27 |
| **Domain-agnostic** | Assumed | **Enforced** in Iteration 21 — no school-specific code in the engine |

---

## 5. What We Need From You

1. **Sign off on the revised 21–27 roadmap** — or flag adjustments before Joan starts Iteration 21.
2. **Priority call on Iterations 24/25/26 ordering** — they can run in any order after 23. Do you have a preference? Our default: 24 (heuristic) → 25 (network) → 26 (posture), since `hybrid_core_remainder` is the most research-valuable strategy.
3. **500-agent ceiling**: the feasibility note (`docs/plans/scale-feasibility-500-agent.md`) concludes that 500-agent runs are architecturally feasible but need `agent_limit` raised beyond 200 + SQLite WAL mode. Should we plan this as a separate hardening slice, or fold it into Iteration 24's stress test?
4. **ADR-002** (interaction policy): still deferred from Iteration 15. With `network_bounded` visibility coming in Iteration 25, this is a good time to author it. Want to write it yourself, or should we draft it?

---

## 6. Files to Read

| File | What it tells you |
|------|-------------------|
| `docs/SESSION_STATE.md` | Current status (post–Iteration 20) |
| `docs/iterations/iteration-19-closeout.md` | Parallel LLM details |
| `docs/iterations/iteration-20-closeout.md` | Population scale + cohort aggregation |
| `docs/plans/scale-feasibility-500-agent.md` | Thesis-grade cost/scale analysis |
| `docs/handoffs/HANDOFF_TO_BUILDER.md` | Full iteration starters (21–27) with scope, DoD, risks |

---

*Written by Cursor (architect), 2026-04-06. Next expected Opus action: review revised roadmap and confirm or adjust before Joan starts Iteration 21.*

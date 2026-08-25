# senna-iter-54 — Fixture Reunification, Confound Test, Individuation

**Spec:** [`docs/handoffs/HANDOFF_SENNA_ITER54.md`](../handoffs/HANDOFF_SENNA_ITER54.md)
**Arc:** 12 — Freeze and Study Readiness
**Date:** 2026-08-25
**Status:** Iteration scope **CLOSED** (Parts A–C + this closeout). Mechanism-defaults verdict **pending GM-F** — iter-54 → iter-55 gate (ARC12 §8).

---

## What iter-54 delivered

Three independently committed parts addressing ARC12 §1:

| Part | Commit | Deliverable |
|------|--------|-------------|
| A — Fixture reunification | `93368c9` | Seeding script, provenance schema, CI tests, setup doc, manifest |
| B — Confound test | `e448c03` | `docs/diagnostics/arc12_confound_results.{json,md}` |
| C — Individuation report | `37d8419` | `docs/diagnostics/ARC12_INDIVIDUATION_FINDING.md` |

Standing constraint honoured throughout: mechanics only — no reading, citing, or scoring substantive transcript content.

---

## Part A — Fixture reunification (Option 1)

**Problem (ARC12 blocking defect):** `ciepss_school_b.yaml` lives only in the study repo (`senna-sstrf-study`), not the platform repo.

**Solution:** Study fixture stays in the private repo; platform loads it via `user_scenarios` + `scripts/seed_scenario_from_study_repo.py`.

### Pre-flight (§1.1 — Architect verified)

| Check | Result |
|-------|--------|
| Study repo | `https://github.com/learningloons-hash/senna-sstrf-study.git` @ `47013659309c5ac047dbc53dcea3fd1441d74042` |
| YAML path | `backend/src/mirofish_backend/scenarios/data/ciepss_school_b.yaml` |
| Content | Clean — roster, roles, paraphrased policy events, `# source:` comments only |
| `rag_enabled` | Absent — corpus reunification out of scope |
| Personas | 8 (matches ARC12 RQ1 assumption) |

### Evidence

- **CI:** 5 tests in `test_senna_iter54_scenario_reunification.py` (synthetic `dummy_external_scenario` fixture).
- **Manual:** Seeded `ciepss_school_b` from study checkout; smoke sim `c28fe9b01eb147cf924844287ea07d8b` → `completed` (2 rounds, 3 agents, stub LLM — load/resolution check).
- **Provenance manifest:** [`docs/diagnostics/ciepss_school_b_provenance.json`](../diagnostics/ciepss_school_b_provenance.json) — **cite this file (not the DB row) for iter-58 pre-registration fixture commit/repo.**
- **Setup doc:** [`docs/SETUP_STUDY_FIXTURES.md`](../SETUP_STUDY_FIXTURES.md)

---

## Part B — Anthropic confound test (six runs)

**Question:** Was Arc 11's `memory_retrieval` interview decline a mechanism effect or local-8B model degradation under longer prompts?

**Design:** Two conditions × three seeds (42/43/44) = 6 runs. `fsbb_comparator`, 3 agents, 5 rounds, Anthropic tier for simulation + interview + judge. Harness: `run_arc11_ablation.py` (no code changes).

### Runs (all completed, QA clean)

| Condition | Seeds | Simulation IDs |
|-----------|-------|----------------|
| `baseline` | 42/43/44 | `2e962591…`, `553b7d29…`, `0b75a919…` |
| `+importance+retrieval+reflection` | 42/43/44 | `059b3122…`, `aa1241a5…`, `9a5a9303…` |

- Zero `[LLM error]` transcript entries; zero context-length failures.
- Total cost: **US$0.96** (~227 s wall-clock) vs ~US$10 estimate.

**Operational note:** First attempt failed preflight (401) — shell-exported `ANTHROPIC_API_KEY` shadowed `backend/.env`. Fixed with `unset ANTHROPIC_API_KEY` before rerun.

### Interview by category (Anthropic tier, all five reported)

| Category | baseline | +importance+retrieval+reflection |
|----------|----------|----------------------------------|
| memory_retrieval | 2.00 | 2.00 — **ceiling** |
| planning | 2.00 | 2.00 — **ceiling** |
| reaction | 1.22 | 1.00 — only category with headroom |
| reflection | 2.00 | 2.00 — **ceiling** |
| self_knowledge | 2.00 | 2.00 — **ceiling** |

MemBench: factual 1.0, reflective 1.0 (all six runs — ceiling).

### Interpretation call (fixed rule, HANDOFF §2)

`memory_retrieval` at **2.00 in both arms** on Anthropic. Arc 11's local-8B decline **does not persist** → **model confound**, not mechanism effect. Mechanisms are **not implicated** for `memory_retrieval` on this evidence.

Full results: [`docs/diagnostics/arc12_confound_results.md`](../diagnostics/arc12_confound_results.md)

---

## Part C — Individuation finding (summary)

Full report: [`docs/diagnostics/ARC12_INDIVIDUATION_FINDING.md`](../diagnostics/ARC12_INDIVIDUATION_FINDING.md)

**Separate question from Part B:** Do agents individuate enough that SSTRF propositions (P1 authority, P3 self-concept, P4 adaptation scale) are testable?

| Tier | Profile | Baseline interview stdev | Memory-stack interview stdev |
|------|---------|--------------------------|------------------------------|
| Local 8B (Arc 11) | 3 agents, 5 rounds | ≈ 0.00 | ≈ 0.31 (+importance+retrieval) |
| Anthropic (Part B) | 3 agents, 5 rounds | ≈ 0.09 | ≈ 0.06 (+importance+retrieval+reflection) |

Arc 11 showed baseline homogeneity and mechanism-mediated differentiation on local 8B. Part B on Anthropic shows low spread in **both** arms with most interview categories at ceiling. This is a **study-validity** argument — not a mechanism-quality verdict. Ablation profile ≠ study profile (`ciepss_school_b`, 8 actors, 15–20 rounds). **Ops does not conclude** on mechanism defaults from this report.

---

## Evidence synthesis for GM-F (§4 combined DoD)

What iter-54 puts on the table for the mechanism-defaults ruling:

| Dimension | Finding |
|-----------|---------|
| **Quality (confound)** | Arc 11 `memory_retrieval` decline does not reproduce on Anthropic — likely local-model artefact, not mechanism harm |
| **Quality (instruments)** | MemBench and four of five interview categories ceilinged on Anthropic ablation profile — low discrimination |
| **Cost** | Full memory stack adds ~40% input tokens on local 8B (Arc 11); Anthropic confound run cost $0.96 total for 6 runs |
| **Dispersion** | Arc 11: mechanisms break false homogeneity on local 8B (~0.00 → ~0.31). Part B Anthropic: low spread both arms (~0.09 / ~0.06) — individuation on study profile **unverified** |

**Current frozen shipping config** (from iter-53, unchanged pending GM-F ruling):

| Flag | Default |
|------|---------|
| `importance_scoring_enabled` | `false` |
| `weighted_retrieval_enabled` | `false` |
| `reflection_enabled` | `false` |
| `working_memory_last_k` / `peer_context_max_chars` | 2 / 1200 |

**Ops does not recommend flipping defaults.** GM-F rules using the evidence above.

---

## iter-55 carry-forward (out of scope here)

1. **Documented CIEPSS network** — no code path loads a real network CSV today; ablation harness synthesises a chain topology only.
2. **Dispersion verification** — must run on study profile (`ciepss_school_b`, 8 actors, 15–20 rounds), not assumed from ablation shape.
3. **Study-scale rehearsal** — ARC12 §2; blocked on GM-F mechanism-defaults ruling per gate below.

---

## Open question for GM-F

**iter-54 → iter-55 gate (ARC12 §8):** Fixture loads from clean checkout ✓. **Mechanism defaults ruling required before iter-55 begins.**

Specifically:

1. Keep all mechanism flags OFF (iter-53 position), enable any, or conditional?
2. Does the confound result + individuation evidence change the Arc 11 PASS WITH ISSUES posture on memory mechanisms?
3. Approve iter-55 scope (study-scale rehearsal on `ciepss_school_b`)?

---

## Is iter-54 complete?

**Build scope: yes.** Parts A, B, C committed; architect-reviewed PASS; this closeout delivered.

**Iteration closed for independent review: yes** — pending GM-F ruling only (not a build item).

**Arc 12 complete: no.** iter-54 is the first of five iterations (`54`–`58`).

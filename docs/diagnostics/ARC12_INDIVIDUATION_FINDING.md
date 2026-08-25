# Arc 12 individuation finding — between-agent dispersion

**Iteration:** `senna-iter-54` Part C  
**Arc:** 12 — Freeze and Study Readiness  
**Date:** 2026-08-25  
**Status:** Evidence-only report. No new runs. Does **not** rule on mechanism defaults — that is GM-F's call.

---

## What this document is

Arc 11's ablation surfaced a **dispersion** result that is easy to miss next to interview-score declines and MemBench ceilings: under some configurations, agents answer the architectural interview as if they were the same actor. Arc 12 Part B reran a subset of that ablation on the **Anthropic tier** (six runs) to test a **model confound** on `memory_retrieval`. This report answers a **different question** using overlapping evidence: **do agents individuate enough that the SSTRF study's propositions are testable at all?**

That is a **study-validity** question, not a "are memory mechanisms good?" question.

**Sources (no re-runs):**

| Evidence | Path |
|----------|------|
| Arc 11 dispersion (local 8B, 12 runs) | [`senna-iter-53-closeout.md`](../iterations/senna-iter-53-closeout.md) dispersion table; raw metrics in [`arc11_ablation_results.json`](./arc11_ablation_results.json) |
| Part B dispersion (Anthropic, 6 runs) | [`arc12_confound_results.json`](./arc12_confound_results.json), [`arc12_confound_results.md`](./arc12_confound_results.md) |
| Part B mechanism-vs-model call | [`arc12_confound_results.md`](./arc12_confound_results.md) § Interpretation — cited below, **not** adopted as this report's conclusion |

**Metric definition (shared):** The ablation harness reports two dispersion measures per run (`arc11_ablation.py::compute_dispersion_metrics`):

1. **Final-round support stdev** — standard deviation of agents' `support_level` in the last simulation round.
2. **Cross-agent interview-score stdev** — per interview category (0–2 rubric), standard deviation of agent mean scores across agents; the closeout table summarises this as a single headline figure per condition (see Arc 11 below).

Both are **mechanics-only** aggregates. This report does not read, cite, or score substantive transcript content.

---

## 1. Arc 11 dispersion (local 8B tier)

From the Arc 11 closeout dispersion table ([`senna-iter-53-closeout.md`](../iterations/senna-iter-53-closeout.md)):

| Condition | Final-round support stdev (mean) | Cross-agent interview-score stdev |
|-----------|----------------------------------|-----------------------------------|
| `baseline` | 0.0438 | **≈ 0.00** (agents answer near-identically) |
| `+importance+retrieval` | 0.0438 | **≈ 0.31** (agents differentiate) |
| `+importance+retrieval+reflection` | 0.0492 | **≈ 0.27** |

**Plain reading:** On the Arc 11 profile (local `dolphin3.0-llama3.1-8b`, `fsbb_comparator`, 3 agents, 5 rounds), baseline agents behave like copies of each other in the architectural interview. Adding importance and retrieval **breaks that false homogeneity** — cross-agent interview dispersion rises from ~0.00 to ~0.31. Reflection does not collapse dispersion; the full stack remains differentiated (~0.27).

Final-round support stdev stays flat (~0.04) across conditions — the headline individuation signal in Arc 11 is in **interview-score dispersion**, not support levels alone.

---

## 2. Part B dispersion (Anthropic tier) — separate question

Part B reran **two** conditions × three seeds on Anthropic (`baseline` and `+importance+retrieval+reflection` only). Profile unchanged: `fsbb_comparator`, 3 agents, 5 rounds. See [`arc12_confound_results.md`](./arc12_confound_results.md) for run IDs and QA.

### Final-round support stdev

| Condition | Seed 42 | Seed 43 | Seed 44 | Mean |
|-----------|---------|---------|---------|------|
| `baseline` | 0.016 | 0.026 | 0.025 | **0.023** |
| `+importance+retrieval+reflection` | 0.019 | 0.022 | 0.009 | **0.017** |

Both arms show **low** final-round support dispersion (≈ 0.02). The full memory stack does **not** raise support stdev on this Anthropic profile; if anything it is slightly lower.

### Cross-agent interview-score stdev

Computed from [`arc12_confound_results.json`](./arc12_confound_results.json) using the same per-category-across-agents stdevs the harness emits. Headline figure = mean of the five category stdevs per run, then averaged across seeds (matching the closeout table's summary style):

| Condition | Per-seed headline stdev | Mean across seeds |
|-----------|-------------------------|-------------------|
| `baseline` | 0.189, 0.094, 0.000 | **≈ 0.09** |
| `+importance+retrieval+reflection` | 0.094, 0.094, 0.000 | **≈ 0.06** |

**Category detail (Anthropic tier):** In both conditions, `memory_retrieval`, `planning`, `reflection`, and `self_knowledge` show **0.00** cross-agent stdev in every run — all agents score at the **2.00 ceiling**. Only `reaction` carries non-zero between-agent spread (up to ≈ 0.47 in some seeds). Three of five interview categories are saturated with no between-agent range.

### How this differs from Part B's mechanism call

Part B's fixed interpretation ([`arc12_confound_results.md`](./arc12_confound_results.md) § Interpretation) addresses **`memory_retrieval` decline on local 8B vs Anthropic** — a model-confound question. It concludes that on Anthropic, `memory_retrieval` sits at 2.00 in **both** arms, so the Arc 11 interview decline does not persist at that tier.

**This report does not restate that as its conclusion.** The question here is **individuation**: whether agents diverge enough to support study propositions. The six Part B runs show **low dispersion in both arms** on the headline interview metric (≈ 0.06–0.09 vs Arc 11 baseline ≈ 0.00 and memory arms ≈ 0.31 on local 8B). On Anthropic, the baseline is **not** as homogenous as Arc 11's ≈ 0.00, but the full stack **does not** reproduce Arc 11's differentiation lift either — and four interview categories remain at ceiling with zero cross-agent stdev.

---

## 3. Study-validity framing (P1, P3, P4)

The SSTRF pre-registration tests propositions that assume **distinct actors**, not copies:

| Proposition | Why dispersion matters |
|-------------|------------------------|
| **P1 (authority)** | Authority dynamics require agents in different roles to **disagree, defer, or resist** — not give interchangeable interview answers. |
| **P3 (self-concept)** | Self-concept change is **agent-specific**; identical actors collapse individual trajectories into one voice. |
| **P4 (adaptation scale)** | Adaptation over 15–20 rounds requires **heterogeneous starting points and paths**; homogeneity at baseline or throughout makes scale effects unobservable. |

**Implication (study-validity, not mechanism quality):** A platform configuration that produces near-identical actors — whether at baseline or with memory mechanisms enabled — **cannot test P1, P3, or P4** regardless of how well the independent judge scores propositions. Scoring quality is moot if the simulated population lacks variance.

Arc 11 evidence on **local 8B** is mixed but informative: baseline homogeneity (~0.00 interview stdev) is a **real risk**, and importance + retrieval **mitigate** it on that tier (~0.31). Part B on **Anthropic** (3-agent ablation profile) shows **low dispersion in both arms** with most interview categories at ceiling — a different pattern that neither confirms nor denies study-scale behaviour on `ciepss_school_b` (8 actors, 15–20 rounds), but flags that **individuation must be verified on the actual study profile**, not assumed from ablation shape alone.

This is evidence for GM-F's ruling on defaults and study readiness. **Ops does not conclude** whether mechanisms should ship on or off from this report alone.

---

## 4. What this report does not do

- **No mechanism-defaults recommendation.** GM-F rules on importance / retrieval / reflection defaults using quality, cost, dispersion, and confound evidence together.
- **No Part B mechanism conclusion duplicated here.** See [`arc12_confound_results.md`](./arc12_confound_results.md) § Interpretation for the `memory_retrieval` model-confound call.
- **No transcript scoring or proposition-level claims.** Mechanics and aggregates only.
- **No claim that the ablation profile equals the study run.** The ablation used `fsbb_comparator`, 3 agents, 5 rounds; the study uses `ciepss_school_b`, 8 actors, 15–20 rounds. Dispersion on the study profile is an open verification step for `iter-55` rehearsal, not settled here.

---

## Summary table

| Tier | Profile | Baseline interview stdev | Memory-stack interview stdev | Individuation read |
|------|---------|--------------------------|------------------------------|-------------------|
| Local 8B (Arc 11) | 3 agents, 5 rounds | ≈ 0.00 | ≈ 0.31 (+importance+retrieval) | Baseline risk; mechanisms increase spread |
| Anthropic (Part B) | 3 agents, 5 rounds | ≈ 0.09 | ≈ 0.06 (+importance+retrieval+reflection) | Low spread both arms; ceilings dominate |

**Bottom line:** Dispersion is not a footnote — it gates whether the study's propositions are testable. Arc 11 showed baseline homogeneity and mechanism-mediated differentiation on local 8B. Part B on Anthropic shows a different dispersion landscape on the same toy profile. **GM-F** should weigh this alongside Part B's mechanism confound result when ruling on defaults and when gating `iter-55`.

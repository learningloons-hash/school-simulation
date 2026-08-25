# Arc 12 confound test results (senna-iter-54 Part B)

Anthropic-tier rerun of Arc 11 ablation shape (two conditions × three seeds) to test model-vs-mechanism confound on `memory_retrieval`.

**Harness:** senna-iter-52 (`run_arc11_ablation.py`)
**Command:** `../scripts/run_arc11_ablation.py --conditions baseline +importance+retrieval+reflection --seeds 42 43 44 --llm-provider anthropic --interview-profile-id anthropic_default --judge-profile-id anthropic_default --json-out ../docs/diagnostics/arc12_confound_results.json --markdown-out ../docs/diagnostics/arc12_confound_results.md`

## Run profile

- Scenario: `fsbb_comparator`
- Agents: 3
- Rounds: 5
- Visibility: `network_bounded` (+ network CSV)
- Seeds: [42, 43, 44]
- Reflection threshold (reflection arm): 35
- Network CSV: synthetic chain for network_bounded (not identical to Arc 10 measured baseline network)

## Baseline reference

- Source: `docs/diagnostics/ARC10_MEASURED_BASELINE_REAL_RUN.md`
- Simulation ID: `21a6d94e0af141de95da73fc3c41f759`

## Per-condition summary (aggregate across seeds)

| Condition | Δ factual | Δ reflective | Δ reflection (interview) | Input tokens (mean) | Cost USD (mean) | Wall s (mean) | Support stdev (mean) |
|-----------|-----------|--------------|------------------------|---------------------|-----------------|---------------|----------------------|
| baseline | 0.0 | 0.0 | 0.0 | 32025.0 ± 96.750538 | 0.158605 ± 0.00061 | 28.055667 ± 3.962819 | 0.022507 ± 0.0044 |
| +importance+retrieval+reflection | 0.0 | 0.0 | 0.0 | 44712.333333 ± 262.304319 | 0.162022 ± 0.001258 | 47.619333 ± 6.076958 | 0.016629 ± 0.005214 |

Deltas are vs [`ARC10_MEASURED_BASELINE_REAL_RUN.md`](./ARC10_MEASURED_BASELINE_REAL_RUN.md) diagnostic summary.

*MemBench is run-level accuracy; between-agent dispersion uses final-round support stdev and per-category interview stdev across agents.*

## Architectural interview by category (all five — Anthropic tier)

| Category | baseline (mean ± stdev across seeds) | +importance+retrieval+reflection | Notes |
|----------|--------------------------------------|-----------------------------------|-------|
| memory_retrieval | 2.00 ± 0.00 | 2.00 ± 0.00 | **Ceiling (2.00)** — no dynamic range |
| planning | 2.00 ± 0.00 | 2.00 ± 0.00 | **Ceiling (2.00)** |
| reaction | 1.22 ± 0.16 | 1.00 ± 0.27 | Only category with headroom |
| reflection | 2.00 ± 0.00 | 2.00 ± 0.00 | **Ceiling (2.00)** |
| self_knowledge | 2.00 ± 0.00 | 2.00 ± 0.00 | **Ceiling (2.00)** |

MemBench (all six runs): factual mean = 1.0, reflective mean = 1.0.

## Between-agent dispersion (final-round support stdev)

| Condition | Seed 42 | Seed 43 | Seed 44 | Mean |
|-----------|---------|---------|---------|------|
| baseline | 0.016 | 0.026 | 0.025 | 0.023 |
| +importance+retrieval+reflection | 0.019 | 0.022 | 0.009 | 0.017 |

## Cost and wall-clock (six runs total)

| Metric | Value |
|--------|-------|
| Total estimated cost | **US$0.96** (vs ~US$10 GM-F estimate — well under) |
| Total input tokens | 230,212 |
| Total output tokens | 33,149 |
| Total wall-clock | ~227 s (~3.8 min) |

## QA

- Zero `[LLM error]` transcript entries across all six runs
- Zero context-length failures
- All six cells completed cleanly

## Interpretation call (fixed rule, §2)

On the Anthropic tier, `memory_retrieval` is at the **2.00 ceiling in both conditions** (baseline and full memory stack). The Arc 11 decline on local 8B **does not persist** here — consistent with **model confound** (local model degrading under longer prompts), not a mechanism effect. Mechanisms are **not implicated** by this confound test for the `memory_retrieval` interview category.

Three of five interview categories (`memory_retrieval`, `reflection`, `self_knowledge`) remain saturated at 2.00; `planning` also ceilinged. Only `reaction` carries dynamic range.

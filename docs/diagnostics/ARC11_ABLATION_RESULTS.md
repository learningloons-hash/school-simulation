# Arc 11 memory ablation results

**Harness:** senna-iter-52
**Command:** `../scripts/run_arc11_ablation.py --seeds 42 43 44`

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
| baseline | 0.0 | 0.0 | 0.0 | 25887.333333 ± 359.681649 | 0.0 | 178.694333 ± 50.153954 | 0.04381 ± 0.007645 |
| +importance | 0.0 | 0.0 | 0.0 | 30739.333333 ± 468.576094 | 0.0 | 159.351333 ± 27.072428 | 0.04381 ± 0.007645 |
| +importance+retrieval | 0.0 | 0.0 | 0.0 | 33022.0 ± 113.137085 | 0.0 | 198.917 ± 76.127801 | 0.04381 ± 0.007645 |
| +importance+retrieval+reflection | 0.0 | 0.0 | 0.0 | 37002.333333 ± 6.236096 | 0.0 | 184.797333 ± 1.171198 | 0.049216 |

Deltas are vs [`ARC10_MEASURED_BASELINE_REAL_RUN.md`](./ARC10_MEASURED_BASELINE_REAL_RUN.md) diagnostic summary.

*MemBench is run-level accuracy; between-agent dispersion uses final-round support stdev and per-category interview stdev across agents.*

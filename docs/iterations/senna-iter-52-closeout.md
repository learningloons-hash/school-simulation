# senna-iter-52 — Ablation Harness (closeout)

## Delivered

- **`scripts/run_arc11_ablation.py`** — CLI sweep: 4 cumulative conditions × configurable seeds (default `[42, 43, 44]`). Queues simulations via backend API, waits for terminal status, runs Arc 10 diagnostics with `--execute-interview`, writes JSON + markdown artifacts.
- **`mirofish_backend/diagnostics/arc11_ablation.py`** — Condition→flag mapping, network CSV builder, metric extraction, delta vs measured baseline, between-agent dispersion (final-round support stdev + interview category stdev), aggregation, markdown generation. `execute_ablation_cell` for stubbed CI path.
- **Artifacts:** `docs/diagnostics/arc11_ablation_results.json` (placeholder until live sweep), `docs/diagnostics/ARC11_ABLATION_RESULTS.md`, `backend/tests/fixtures/arc11/measured_baseline_summary.json`, `ablation_results_schema.json`.
- **Tests:** `tests/test_senna_iter52_arc11_ablation.py` — flag ladder, delta math, 1 seed × 4 conditions with stub LLM/interview/embed.

## Four conditions (cumulative)

| Condition | Flags |
|-----------|-------|
| `baseline` | none |
| `+importance` | `importance_scoring_enabled` |
| `+importance+retrieval` | + `weighted_retrieval_enabled` |
| `+importance+retrieval+reflection` | + `reflection_enabled` |

## Run profile (matches Arc 10 measured baseline)

- Scenario `fsbb_comparator`, 3 agents, 5 rounds, `network_bounded` + generated network CSV, `full_census` tier-1.

## Reproducibility

Full sweep (slow; live LLM + embeddings):

```bash
python3 scripts/run_arc11_ablation.py --seeds 42 43 44
```

Smoke (2 conditions, 1 seed):

```bash
python3 scripts/run_arc11_ablation.py --seeds 42 --conditions baseline +importance
```

Deltas are vs [`ARC10_MEASURED_BASELINE_REAL_RUN.md`](../diagnostics/ARC10_MEASURED_BASELINE_REAL_RUN.md) via fixture summary JSON.

## Out of scope (iter-53)

Arc 11 selection decision, frontend experiment UI, live 12-run CI matrix.

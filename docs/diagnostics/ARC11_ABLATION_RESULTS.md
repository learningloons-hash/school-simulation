# Arc 11 memory ablation results

**Harness:** senna-iter-52 — results not yet generated.

Run the full sweep (slow; requires live LLM + embeddings stack):

```bash
python3 scripts/run_arc11_ablation.py --seeds 42 43 44
```

Fast smoke:

```bash
python3 scripts/run_arc11_ablation.py --seeds 42 --conditions baseline +importance
```

Structured JSON: [`arc11_ablation_results.json`](./arc11_ablation_results.json)

Deltas are vs [`ARC10_MEASURED_BASELINE_REAL_RUN.md`](./ARC10_MEASURED_BASELINE_REAL_RUN.md).

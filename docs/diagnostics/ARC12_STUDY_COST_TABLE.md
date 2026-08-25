# Arc 12 study cost table (RQ1 rehearsal)

**Source:** senna-iter-55 Part B live runs  
**Results JSON:** [`arc12_study_rehearsal_results.json`](./arc12_study_rehearsal_results.json)  
**Summary:** [`ARC12_STUDY_REHEARSAL_RESULTS.md`](./ARC12_STUDY_REHEARSAL_RESULTS.md)  
**Supersedes:** Phase C / SSTRF cover-note pilot figures (8 actors × **6** rounds, pilot configuration)

This table reports **measured** token and cost mechanics at the **study rehearsal profile**. Substantive outputs were not read or scored (Arc 12 standing constraint).

---

## 1. Configuration snapshot

| Field | Value |
|-------|--------|
| Scenario | `ciepss_school_b` |
| Agents | 8 |
| Visibility | `network_bounded` |
| Network | `docs/research/fixtures/ciepss_school_b_network.csv` (9 documented edges) |
| Sampling | `full_census` |
| LLM provider | Anthropic |
| Model | `claude-haiku-4-5-20251001` |
| `importance_scoring_enabled` | false |
| `weighted_retrieval_enabled` | false |
| `reflection_enabled` | false |
| `convergence_threshold` | not set (full horizon) |
| Seeds | 42, 43, 44 |

*Mechanism flags: iter-53 interim defaults; GM-F formal ruling pending.*

---

## 2. Per-run cost table

Costs are **as recorded at run time** from per-turn billing in the results JSON (`estimated_cost_usd`). iter-55 executed **before** senna-iter-56 Part A; billing used the generic Anthropic bucket ($3.00 / $15.00 per MTok input/output), not Haiku 4.5 list rates. See §4.

| Config | Seed | Rounds | Agents | Input tokens | Output tokens | Cost (USD) | Wall-clock (s) | Cost / round (USD) |
|--------|-----:|-------:|-------:|-------------:|--------------:|-----------:|---------------:|-------------------:|
| RQ1-15 | 42 | 15 | 8 | 540,800 | 30,987 | 2.087 | 128.9 | 0.139 |
| RQ1-15 | 43 | 15 | 8 | 503,056 | 29,554 | 1.952 | 129.4 | 0.130 |
| RQ1-15 | 44 | 15 | 8 | 509,397 | 29,197 | 1.966 | 132.4 | 0.131 |
| RQ1-20 | 42 | 20 | 8 | 918,862 | 40,685 | 3.367 | 169.2 | 0.168 |
| RQ1-20 | 43 | 20 | 8 | 915,151 | 39,890 | 3.344 | 155.2 | 0.167 |
| RQ1-20 | 44 | 20 | 8 | 864,217 | 39,039 | 3.178 | 184.5 | 0.159 |

Simulation IDs: see [`ARC12_STUDY_REHEARSAL_RESULTS.md`](./ARC12_STUDY_REHEARSAL_RESULTS.md) § Simulation IDs.

**Cost / round** = `estimated_cost_usd ÷ rounds` (derived; linear with round count at this scale because per-round input grows with history).

---

## 3. Totals and means by configuration

### RQ1-15 (8 agents × 15 rounds × 3 seeds)

| Metric | Total (3 runs) | Mean per run |
|--------|---------------:|-------------:|
| Input tokens | 1,553,253 | 517,751 |
| Output tokens | 89,738 | 29,913 |
| Cost (USD) | **6.01** | **2.00** |
| Wall-clock (s) | 390.7 | 130.2 |
| Cost / round (USD) | — | 0.133 |

### RQ1-20 (8 agents × 20 rounds × 3 seeds)

| Metric | Total (3 runs) | Mean per run |
|--------|---------------:|-------------:|
| Input tokens | 2,698,230 | 899,410 |
| Output tokens | 119,614 | 39,871 |
| Cost (USD) | **9.89** | **3.30** |
| Wall-clock (s) | 508.9 | 169.6 |
| Cost / round (USD) | — | 0.165 |

### Grand total (six RQ1 runs)

| Metric | Value |
|--------|------:|
| Runs | 6/6 completed |
| Total input tokens | 4,251,483 |
| Total output tokens | 209,352 |
| **Total cost (USD)** | **15.90** |
| **Total wall-clock** | **~899 s (~15 min)** |
| LLM errors | 0 |
| Context-length failures | 0 |

---

## 4. Pricing notes (iter-56 Part A)

| Item | Detail |
|------|--------|
| **iter-55 billing** | Generic `anthropic` key: $3.00 / $15.00 per MTok (matches JSON totals; e.g. RQ1-15 seed 42: 540,800×3/1M + 30,987×15/1M ≈ $2.087). |
| **Part A map (future runs)** | `PRICE_MAP_DATE = 2026-08-25`; Haiku 4.5 → `anthropic_haiku_4_5` at **$1.00 / $5.00** per MTok. |
| **Retroactive Haiku estimate** | Same tokens at Haiku list rates ≈ **$0.67** mean per 15-round run and **$1.10** mean per 20-round run (grand total ≈ **$5.30** vs $15.90 recorded — ~67% lower). JSON figures are **not** re-billed here — funder reporting should use Part A rates for runs after `866c992`. |
| **Convergence (Part B sibling doc)** | Recommended τ = 0.02 would counterfactually stop at round 8 → ~47% / ~53% cost reduction vs full RQ1-15 / RQ1-20 horizons at similar per-round burn. See [`ARC12_CONVERGENCE_CALIBRATION.md`](./ARC12_CONVERGENCE_CALIBRATION.md). |

---

## 5. RQ2 row (deferred)

| Config | Status |
|--------|--------|
| RQ2 (~20 documented actors + synthetic remainder, Lee 2020 fixture) | **Deferred** — no platform scenario fixture; `--skip-rq2` on all iter-55 invocations. **No cost figures invented.** Re-run rehearsal without `--skip-rq2` when fixture exists. |

---

## 6. Comparison to Phase C pilot

| | Phase C (superseded) | iter-55 RQ1 rehearsal |
|--|---------------------|------------------------|
| Actors | 8 | 8 |
| Rounds | 6 | **15** and **20** |
| Scenario | Pilot configuration | `ciepss_school_b` + documented network |
| Tier | Pilot | Anthropic Haiku 4.5 |
| Mechanisms | Pilot flags | All off (interim) |

Use this table for grant / thesis cost planning at **study configuration**, not Phase C extrapolation.

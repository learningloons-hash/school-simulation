# Arc 12 convergence threshold calibration

**Source:** senna-iter-55 RQ1 study rehearsal (six completed runs)  
**Harness:** [`arc12_study_rehearsal_results.json`](./arc12_study_rehearsal_results.json)  
**Data extraction:** `global_state_snapshots.convergence_delta` from `backend/data/mirofish.sqlite` (same rows as export bundles)  
**Pricing context:** Part A per-model map is unrelated to convergence; this doc is mechanics-only.

---

## 1. Stopping rule (platform definition)

Senna implements **population-level convergence** on continuous agent state, **not** on Likert self-report (D2).

After each round (from round 2 onward), the orchestrator computes **`convergence_delta`**: the mean, across all agents, of the mean absolute change in three float fields vs the prior round:

- `support_level`
- `resistance_level`
- `workload_stress`

Formally (see `orchestrator._population_convergence_delta`):

\[
\delta_r = \frac{1}{N} \sum_{i=1}^{N} \frac{|s_i - s_i'| + |r_i - r_i'| + |w_i - w_i'|}{3}
\]

where \(s, r, w\) are the three attitude/stress floats and primes denote the previous round.

**Early stop** when `convergence_threshold` is set **and**:

1. \(\delta_r < \text{threshold}\) for **`convergence_patience` consecutive rounds** (default **2**), then
2. Run status → `completed`, `converged_at_round` recorded.

If `convergence_threshold` is **omitted** (API default), the run executes the full `total_rounds` regardless of \(\delta_r\). There is **no default threshold** — only a default patience of **2** when a threshold *is* supplied (`SimulationRunRequest`, `GET /capabilities`).

---

## 2. iter-55 rehearsal context

| Item | Value |
|------|--------|
| Scenario | `ciepss_school_b` |
| Agents | 8 |
| Configs | RQ1-15 (15 rounds), RQ1-20 (20 rounds) |
| Seeds | 42, 43, 44 |
| LLM | Anthropic — `claude-haiku-4-5-20251001` |
| Visibility | `network_bounded` + documented CIEPSS network CSV |
| Mechanism flags | All **off** (iter-53 interim defaults; GM-F pending) |
| `convergence_threshold` on runs | **Not set** (null in all six `config_snapshot`s) |

All six runs completed their full 15 or 20 rounds. Analysis below is **counterfactual**: at candidate thresholds, when *would* patience-2 early stop have fired?

---

## 3. `convergence_delta` by round (all six runs)

Round 1 has no prior state → delta is null. Values rounded to four decimals.

### RQ1-15

| Round | Seed 42 | Seed 43 | Seed 44 |
|------:|--------:|--------:|--------:|
| 1 | — | — | — |
| 2 | 0.0329 | 0.0354 | 0.0313 |
| 3 | 0.0342 | 0.0288 | 0.0304 |
| 4 | 0.0463 | 0.0446 | 0.0517 |
| 5 | 0.0275 | 0.0213 | 0.0275 |
| 6 | 0.0492 | 0.0471 | 0.0446 |
| 7 | 0.0025 | 0.0092 | 0.0117 |
| 8 | 0.0075 | 0.0017 | 0.0113 |
| 9 | 0.0133 | 0.0008 | 0.0088 |
| 10 | 0.0017 | 0.0071 | 0.0075 |
| 11 | 0.0017 | 0.0063 | 0.0092 |
| 12 | 0.0075 | 0.0075 | 0.0042 |
| 13 | 0.0108 | 0.0000 | 0.0000 |
| 14 | 0.0025 | 0.0000 | 0.0113 |
| 15 | 0.0000 | 0.0025 | 0.0000 |

Sim IDs: seed 42 `8c6d1ec…`, 43 `5e7d44a5…`, 44 `2f995f36…`.

### RQ1-20

| Round | Seed 42 | Seed 43 | Seed 44 |
|------:|--------:|--------:|--------:|
| 1 | — | — | — |
| 2 | 0.0388 | 0.0358 | 0.0300 |
| 3 | 0.0325 | 0.0346 | 0.0321 |
| 4 | 0.0488 | 0.0446 | 0.0446 |
| 5 | 0.0321 | 0.0221 | 0.0292 |
| 6 | 0.0504 | 0.0338 | 0.0363 |
| 7 | 0.0058 | 0.0067 | 0.0079 |
| 8 | 0.0017 | 0.0104 | 0.0050 |
| 9 | 0.0033 | 0.0046 | 0.0033 |
| 10 | 0.0058 | 0.0071 | 0.0054 |
| 11 | 0.0038 | 0.0013 | 0.0071 |
| 12 | 0.0133 | 0.0025 | 0.0033 |
| 13 | 0.0000 | 0.0042 | 0.0008 |
| 14 | 0.0042 | 0.0050 | 0.0008 |
| 15 | 0.0013 | 0.0025 | 0.0000 |
| 16 | 0.0054 | 0.0042 | 0.0000 |
| 17 | 0.0038 | 0.0046 | 0.0000 |
| 18 | 0.0000 | 0.0000 | 0.0000 |
| 19 | 0.0050 | 0.0013 | 0.0000 |
| 20 | 0.0050 | 0.0000 | 0.0000 |

Sim IDs: seed 42 `fa54ad08…`, 43 `a91dcb4c…`, 44 `5332c81e…`.

### Distribution summary (rounds 2–20, all runs)

| Stat | Value |
|------|------:|
| n | 99 |
| Mean | 0.0140 |
| Median | 0.0063 |
| 90th pct | 0.0446 |
| Max | 0.0517 |

**Early-round band (rounds 2–6):** min per run 0.021–0.032; max 0.044–0.052. **Late-round band (rounds 7+):** predominantly &lt; 0.015 after round 6's spike.

---

## 4. Counterfactual early-stop analysis (`convergence_patience = 2`)

“Stop round” = first round \(r\) where \(\delta_{r-1} < \tau\) **and** \(\delta_r < \tau\). “Never” = no such pair within the run horizon.

| Threshold τ | RQ1-15 (seeds 42/43/44) | RQ1-20 (seeds 42/43/44) |
|-------------|-------------------------|-------------------------|
| **0.05** | 3 / 3 / 3 | 3 / 3 / 3 |
| **0.02** | 8 / 8 / 8 | 8 / 8 / 8 |
| **0.015** | 8 / 8 / 8 | 8 / 8 / 8 |
| **0.01** | 8 / 8 / 10 | 8 / 10 / 8 |
| **0.005** | 11 / 9 / 13 | 9 / 12 / 9 |
| **0.003** | 11 / 9 / never | never / 12 / 14 |
| **0.001** | never / 14 / never | never / never / 14 |

**Note on 0.05:** This is the threshold used in platform integration tests (`test_iteration28.py`). On the study profile it would stop **every run at round 3** — rounds 2–3 deltas are ~0.028–0.039, both below 0.05. That matches ARC12's warning: an uncalibrated threshold **fires in round three**.

---

## 5. Recommended calibrated threshold

### Recommendation: **`convergence_threshold = 0.02`**, **`convergence_patience = 2`** (defaults)

**Reasoning:**

1. **Avoids round-3 false convergence.** τ = 0.05 stops all six runs at round 3 while agents are still in the initial adjustment phase (rounds 2–6 show repeated spikes to ~0.045–0.052).

2. **Stable stop round across seeds and configs.** τ ∈ [0.015, 0.025] all yield stop at **round 8** on every rehearsal run. Round 8 is the first point after the round-6 spike where two consecutive sub-threshold rounds occur (typically rounds 7–8: e.g. seed 42 RQ1-15 has δ₇ = 0.0025, δ₈ = 0.0075).

3. **Meaningful horizon reduction without over-truncation.** Counterfactual stop at round 8 saves **7 rounds** on RQ1-15 (53% of budget) and **12 rounds** on RQ1-20 (60%) vs fixed horizons — material for funder cost control while retaining post-settling dynamics.

4. **Headroom below early churn.** Minimum δ in rounds 2–6 is ~0.021; τ = 0.02 sits just under that band, so transient round-5 dips (e.g. 0.021) alone cannot trigger stop without a confirming second round.

**Alternatives considered:**

| τ | Verdict |
|---|---------|
| 0.05 | Reject — universal round-3 stop |
| 0.01 | Acceptable but slower / less uniform (some runs stop round 10) |
| 0.005 | Too strict for 15-round horizon — several runs never converge |
| 0.003 | Reject — majority of runs exceed horizon |

**GM-F / pre-reg action:** Record `convergence_threshold: 0.02` and `convergence_patience: 2` in the iter-58 config snapshot. Re-validate if mechanism flags are enabled (importance/retrieval/reflection may alter late-round δ).

---

## 6. Implications for RQ1 study design

| Config | Fixed horizon (iter-55) | With τ = 0.02, patience 2 |
|--------|-------------------------|---------------------------|
| RQ1-15 | 15 rounds | Would stop at **round 8** (all seeds) |
| RQ1-20 | 20 rounds | Would stop at **round 8** (all seeds) |

iter-55 deliberately ran **without** convergence enabled so mechanics (tokens, QA, dispersion) could be measured at full 15/20-round horizons. Future study runs should set τ = 0.02 explicitly rather than relying on omission.

**RQ2:** Not calibrated here — Lee (2020) fixture deferred; no convergence series available.

---

## 7. Reproducibility

```sql
-- Convergence series for one rehearsal run
SELECT round_number, convergence_delta
FROM global_state_snapshots
WHERE simulation_id = '8c6d1ec1968348e4b2a3b14b008d8652'
ORDER BY round_number;

-- Confirm threshold was not set
SELECT id,
       json_extract(config_snapshot, '$.convergence_threshold') AS threshold,
       json_extract(config_snapshot, '$.convergence_patience') AS patience
FROM simulation_runs
WHERE id = '8c6d1ec1968348e4b2a3b14b008d8652';
```

Counterfactual stop-round logic matches `orchestrator` streak behaviour: increment streak when δ &lt; τ, reset to 0 otherwise, stop when streak ≥ patience.

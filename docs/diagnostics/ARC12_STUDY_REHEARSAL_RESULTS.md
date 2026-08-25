# Arc 12 study rehearsal results

**Harness:** senna-iter-55
**Command:** `../scripts/run_arc12_study_rehearsal.py --study-repo-path /Users/home/cursor-projects/project-1/senna-sstrf-study --network-csv-rel-path docs/research/fixtures/ciepss_school_b_network.csv --llm-provider anthropic --seeds 42 43 44 --rounds 15 20 --skip-rq2`

## Profile

- Scenario: `ciepss_school_b`
- Agents: 8
- Visibility: `network_bounded` (+ documented network CSV)
- Network CSV: `docs/research/fixtures/ciepss_school_b_network.csv`
- Note: documented CIEPSS links from study repo (not synthetic chain)

## Interim mechanism flags (GM-F ruling pending)

- `importance_scoring_enabled`: False
- `weighted_retrieval_enabled`: False
- `reflection_enabled`: False

*GM-F formal ruling pending; iter-53 frozen defaults until ruled otherwise.*

## RQ2

**Deferred:** RQ2 (~20 documented actors + synthetic remainder) deferred — no platform scenario fixture today; pending Lee (2020) case per ARC12 §7. Re-run without --skip-rq2 when study-repo fixture and scenario exist.

## Run mechanics summary

| Label | Seed | Rounds | Status | Input tokens | Cost USD | Wall s | LLM errors | Ctx failures | Support stdev |
|-------|------|--------|--------|--------------|----------|--------|------------|--------------|---------------|
| RQ1-15 | 42 | 15 | completed | 540800 | 2.087205 | 128.917 | 0 | 0 | 0.071414 |
| RQ1-15 | 43 | 15 | completed | 503056 | 1.952478 | 129.401 | 0 | 0 | 0.046904 |
| RQ1-15 | 44 | 15 | completed | 509397 | 1.966146 | 132.406 | 0 | 0 | 0.03937 |
| RQ1-20 | 42 | 20 | completed | 918862 | 3.366861 | 169.18 | 0 | 0 | 0.050436 |
| RQ1-20 | 43 | 20 | completed | 915151 | 3.343803 | 155.18 | 0 | 0 | 0.02222 |
| RQ1-20 | 44 | 20 | completed | 864217 | 3.178236 | 184.516 | 0 | 0 | 0.016583 |

*Mechanics only — substantive outputs not read, cited, or scored (Arc 12 standing constraint).*

## QA summary

- **6/6** runs reached terminal `completed`
- **0** `[LLM error]` transcript entries across all runs
- **0** context-length failures
- **Total cost:** US$15.90 | **Total wall-clock:** ~900 s (~15 min)

## Simulation IDs

| Label | Seed | Simulation ID |
|-------|------|---------------|
| RQ1-15 | 42 | `8c6d1ec1968348e4b2a3b14b008d8652` |
| RQ1-15 | 43 | `5e7d44a5da1d47cfb9a6dc7d2a590876` |
| RQ1-15 | 44 | `2f995f368c814d0e9b142f6c689bd720` |
| RQ1-20 | 42 | `fa54ad08d90a459ca352fb6d8aaf9dff` |
| RQ1-20 | 43 | `a91dcb4cd3f545ab9f2c96fcaeab7de2` |
| RQ1-20 | 44 | `5332c81e67f3402f9a11f35c68db9072` |

## ARC12 §2 watch items (mechanics only)

### 1. Context growth (`token_totals_by_round`)

Per-run input tokens grow from ~3,446 (round 1) to ~62–90k (final round). RQ1-20 final-round input tokens per seed: 90,107 / 87,941 / 81,910. No context-length failures observed at 20 rounds × 8 agents on Anthropic tier — but round-20 per-round input (~80–90k) is ~26× round 1 and warrants monitoring if rounds or agent count increase further.

### 2. `peer_context_max_chars` / `working_memory_last_k` at scale

All runs used Arc 1 defaults from `config_snapshot`: `peer_context_max_chars=1200`, `working_memory_last_k=2`. At 8 agents / 15–20 rounds these settings remain active (not overridden) but peer context is a small fraction of total prompt growth — the dominant driver is cumulative transcript/history, not peer snippet size alone.

### 3. `group_addressed_proportion`

**0.25** on all six runs (network-bounded visibility with documented CIEPSS edges — broadcast turns are 25% of total).

### 4. State-extraction provenance

All LLM turns recorded `state_update_source=model_parsed` (120 turns for 15-round runs; 160 for 20-round runs). No repair/heuristic fallback observed.

### 5. Dispersion on study profile (`final_round_support_stdev`)

RQ1-15: 0.039–0.071 | RQ1-20: 0.017–0.050 — non-zero on 8-agent study profile (contrast with near-zero ablation baseline on 3-agent toy profile).

### 6. Elicitation / Likert structures

`likert_self_report_enabled=false` on scenario (not exercised). `round_outcomes` present for all 20 rounds on RQ1-20 sample check — round completion machinery intact. No structural failures detected (mechanics check only).

# MiroFish MVP — 500-Agent Scale Feasibility Note

*Iteration 20 addendum. Companion to `SCALE_LIMITS_AND_COST.md`.*

---

## 1. Context

Iteration 20 raised `agent_limit` to **200** and added cohort aggregation in the export
bundle. This note provides a thesis-grade cost/latency analysis across four scale tiers
(50 / 100 / 200 / 500 agents) to guide experiment design and hardware planning.

---

## 2. Turn-count model

```
total_turns = agent_limit × total_rounds
```

| Scale tier | Agents | Rounds | Total turns |
|------------|--------|--------|-------------|
| Small      | 50     | 4      | 200         |
| Medium     | 100    | 4      | 400         |
| Large      | 200    | 4      | 800         |
| Thesis max | 500    | 4      | 2 000       |

With `simulation_mode = sample_k_per_round` and `speakers_per_round = k`:

```
total_turns = k × total_rounds
```

At k = 20 and 4 rounds that is **80 turns** regardless of pool size — the primary
scaling lever for thesis-scale runs.

---

## 3. Wall-clock latency estimates

Assumptions:
- **LM Studio (local, Mac mini M2 Pro):** ~1.5 s average per LLM turn (128-token
  response, quantised 7B model).
- **`llm_concurrency_cap`:** parallel cap used in Iteration 19.
- Formula: `wall_ms ≈ (total_turns / concurrency_cap) × avg_turn_latency_ms`

| Scale   | Turns | Cap | Sequential time | Parallel time (cap) |
|---------|-------|-----|-----------------|---------------------|
| 50 ag   | 200   | 1   | ~300 s (5 min)  | — (cap unused)      |
| 50 ag   | 200   | 8   | —               | ~38 s               |
| 100 ag  | 400   | 8   | ~600 s (10 min) | ~75 s               |
| 200 ag  | 800   | 8   | ~1 200 s        | ~150 s              |
| 200 ag  | 800   | 16  | —               | ~75 s               |
| 500 ag* | 2 000 | 16  | ~3 000 s        | ~188 s              |

*500-agent runs require `agent_limit` raised beyond Iteration 20's ceiling of 200.
They are architecturally feasible but not yet exposed via the API.

**Takeaway:** `llm_concurrency_cap = 8–16` brings even 200-agent / 4-round runs within
the ~2-minute range on local hardware.

---

## 4. Token budget (Anthropic cost leg)

Assumptions:
- **Input:** ~1 800 tokens per turn (system + working memory + peer context + RAG).
- **Output:** ~300 tokens per turn.
- **Hybrid routing:** first turn of each round uses Anthropic; rest use LM Studio.
- **Claude 3.5 Haiku pricing (Apr 2026):** $0.80 / M input, $4.00 / M output.

```
anthropic_turns = agent_count × 1          (1 frontier turn per round, per agent)
                = agent_count             (per round)
```

Actually with hybrid routing policy `frontier_first_turn_of_round`,
only **1** Anthropic call fires per round (the first turn of that round):

```
anthropic_turns = total_rounds = 4
input_tokens = 4 × 1 800 = 7 200
output_tokens = 4 × 300 = 1 200
cost = (7 200 / 1 000 000) × $0.80 + (1 200 / 1 000 000) × $4.00
     ≈ $0.006 + $0.005 = ~$0.01 per run (any scale, hybrid routing)
```

For **full-Anthropic runs** (`llm_provider = anthropic`):

| Scale | Turns | Input tokens | Output tokens | Estimated cost |
|-------|-------|-------------|---------------|----------------|
| 50    | 200   | 360 K        | 60 K          | ~$0.53         |
| 100   | 400   | 720 K        | 120 K         | ~$1.06         |
| 200   | 800   | 1.44 M       | 240 K         | ~$2.11         |
| 500*  | 2 000 | 3.6 M        | 600 K         | ~$5.28         |

---

## 5. DB write patterns and aiosqlite limits

Each turn writes:
- **1 row** to `agent_turns` (transcript)
- **1 row** to `agent_state_snapshots`
- Minor updates to `simulation_runs` (current_round, status)

At 800 turns (200 agents × 4 rounds) that is **1 600 sequential DB writes** (aiosqlite
serialises all writes). At ~1 ms per write, DB I/O adds ~1.6 s overhead — negligible.

At 2 000 turns (500-agent scenario), DB writes add ~2 s. Still acceptable for a
research tool. For production throughput, consider:

1. **Batch inserts** — collect all turns in a round, insert in one `executemany`.
2. **WAL mode** — enable `PRAGMA journal_mode = WAL` for concurrent readers during
   long runs.

These are tracked as follow-up items; they are not blockers at the 200-agent ceiling.

---

## 6. Cohort aggregation cost

`compute_cohort_summary` is a pure in-memory Python function that reads from the
already-fetched `agent_state_snapshots` list. No additional DB query is issued.

| Snapshots | Groups | Computation time (estimate) |
|-----------|--------|----------------------------|
| 800       | 10     | < 1 ms                     |
| 2 000     | 20     | < 5 ms                     |

No performance concern at thesis scale.

---

## 7. Recommended configurations per tier

| Tier               | Agents | `sample_k` | `llm_concurrency_cap` | `llm_provider`   | Notes                                      |
|--------------------|--------|------------|----------------------|------------------|--------------------------------------------|
| Pilot / debug      | 3–10   | N/A (RR)   | 4                    | lmstudio         | Fast iteration, full round-robin           |
| Module test        | 20–50  | N/A or 10  | 8                    | lmstudio         | Parallelism starts paying off              |
| Thesis chapter run | 50–100 | 20         | 8                    | hybrid           | Sample-k keeps turns bounded; Anthropic frontier turn only |
| Population study   | 100–200| 20–40      | 16                   | lmstudio         | Full local; use population_csv + stratified sampling |
| Maximum (future)   | 200–500| 20–50      | 16                   | lmstudio         | Beyond current API ceiling; requires `agent_limit` raise + WAL |

---

## 8. Hard limits under current architecture

| Limit | Value | Bottleneck |
|-------|-------|------------|
| `agent_limit` ceiling | 200 | API validation (`le=200`, Iteration 20) |
| `speakers_per_round` ceiling | 200 | API validation (`le=200`, Iteration 20) |
| `llm_concurrency_cap` ceiling | 16 | API validation (`le=16`, Iteration 19) |
| Max LLM output tokens | 8 192 | API validation (`le=8192`) |
| Max total_rounds | 25 | API validation (`le=25`) |
| SQLite write serialisation | ~1 ms/write | aiosqlite single-writer model |

500-agent runs require relaxing the `agent_limit` ceiling and enabling WAL mode.
They are not recommended for the Mac mini without profiling first.

---

*Last updated: 2026-04-06 — Iteration 20*

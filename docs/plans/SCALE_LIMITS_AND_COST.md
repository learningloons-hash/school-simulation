# MiroFish MVP — scale limits & rough cost model

Operational reference for runs on the Mac mini + LM Studio / optional Anthropic. Not a SLA.

## API & engine limits (current)

| Knob | Limit | Notes |
|------|--------|------|
| **`agent_limit`** | **1–50** | Validated on `POST /simulations/run` (raised in Iteration 9). |
| **Soft warning** | **`agent_limit > 20`** | `config_snapshot.scale_warning` is **true**; UI shows a short heads-up — still full sequential LLM cost. |
| **`total_rounds`** | **1–25** | Per request. |
| **LLM calls per run** | **`agent_limit × total_rounds`** (sequential) | One completion per agent per round; no batching. |
| **Hybrid routing** | First turn of each round may use **Anthropic** | Rest use LM Studio — see `config_snapshot.hybrid_routing_policy`. |

## Latency shape

- Turns run **in order** inside each round; wall-clock time ≈ **sum of per-turn LLM latency**.
- **RAG** (when on): extra **embedding** calls for chunk index build + one query embed per turn (cached chunks amortize over turns).

## Cost (order of magnitude)

- **LM Studio (local):** marginal **$0** API cost; cost is **electricity + hardware + your time**.
- **Anthropic:** billed per **input/output tokens**; hybrid runs charge on **~`total_rounds`** frontier turns (plus any full-anthropic run).
- **Rule of thumb:** doubling **`agent_limit`** or **`total_rounds`** roughly doubles **turn count** and thus **time + token spend** (for cloud provider legs).

## When “more agents” stops being a slider tweak

- Above **~50** (and long before that in practice), thesis-grade **500-person** scenarios should use a **population + sampling** design (see `BRIEF_FOR_JOAN.md` §2–4), not raising **`agent_limit`** alone.

## Reproducibility

- **`random_seed`** and full **`config_snapshot`** on the run row support replay analysis; future work may snapshot **sampling decisions** for large-population modes.

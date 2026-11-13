# M3 — Claude Sonnet 5.5 study pin

**Milestone:** M3 (Senna v3 platform). **Branch:** `m3-sonnet55-pin`.

## Study profile

| Field | Value |
|-------|--------|
| `model_profile_id` | `anthropic_sonnet_5_5` |
| API `model` | `claude-sonnet-5-5` |
| Default thinking | `{"type": "between_tools"}` |
| Default effort | `medium` |
| Built-in default | unchanged — `anthropic_default` remains `claude-haiku-5-5` |

Select the study pin on a run via `POST /simulations/run`:

```json
{
  "llm_provider": "anthropic",
  "model_profile_id": "anthropic_sonnet_5_5",
  "anthropic_thinking_type": "between_tools",
  "anthropic_effort": "medium"
}
```

Environment defaults (when the resolved Anthropic model is Sonnet 5.5): `ANTHROPIC_THINKING_TYPE`, `ANTHROPIC_EFFORT` in `backend/.env` (see `config.py`). The same defaults apply when `ANTHROPIC_MODEL=claude-sonnet-5-5` without the study profile.

## Central resolution (all call paths)

`llm/router.py` **`llm_complete`** resolves thinking and effort via `resolve_wire_anthropic_thinking_effort` for every Anthropic call when the model is Sonnet 5.5. `llm/claude_client.py` applies the same resolver as a safety net before the HTTP request.

**Call paths (all go through `llm_complete`):**

| Call site (`llm_call_site` / log `call_site`) | Module |
|-----------------------------------------------|--------|
| `agent_turn`, `likert_round_end` | `simulation/orchestrator.py` |
| `importance_per_turn`, `importance_per_round_batch` | `simulation/importance_scoring.py` |
| `reflection` | `simulation/reflection.py` |
| `analyze_simulation` | `api/simulations.py` |
| `agent_plan` | `agent/orchestrator.py` |
| `scenario_catalog_llm_fill` | `api/scenario_catalog.py` |
| `scenario_generate_from_brief` | `api/scenarios_generate.py` |
| `architectural_interview_rubric` | `diagnostics/architectural_interview.py` (`complete_with_profile`) |

Queued runs also resolve thinking/effort in `queue_simulation_run` before the orchestrator starts (`simulation/orchestrator.py` uses `resolve_anthropic_request_config` so missing run kwargs still get Sonnet defaults).

## Anthropic request fields (verified 2026-11-12)

Source: [Claude Sonnet 5.5 migration guide](https://platform.claude.com/docs/en/models/sonnet-5-5/migration-guide) — example request uses:

- `model` — e.g. `claude-sonnet-5-5`
- `max_tokens`
- `messages`
- `thinking` — e.g. `{"type": "between_tools"}`
- `output_config` — e.g. `{"effort": "medium"}`

Senna sends these on **every** Messages API call when the resolved model id is `claude-sonnet-5-5` (or a dated suffix). Temperature is **not** sent (existing behaviour).

## Validation (fail closed before HTTP)

| Rule | Reason |
|------|--------|
| `thinking.type == "disabled"` on Sonnet 5.5 | API returns HTTP 400 |
| `between_tools` with `effort` `xhigh` or `max` | API returns HTTP 400 |
| Invalid thinking type (not `between_tools` or `adaptive`) | Config error |
| Invalid effort (not low/medium/high/xhigh/max) | Config error |

`between_tools` is valid only with `low`, `medium`, or `high`.

## Sonnet 5.5 `max_tokens` floors

On Sonnet 5.5, `max_tokens` covers thinking plus text. `sonnet_55_effective_max_tokens` in `llm/anthropic_request.py` raises the cap per call site (conservative study floors):

| Call site | Floor |
|-----------|-------|
| `agent_turn` | 2048 |
| `likert_round_end` | 1024 |
| `importance_per_turn` | 512 |
| `importance_per_round_batch` | 1536 |
| `reflection` | 1024 |

When the queued model is Sonnet 5.5, `config_snapshot.run_manifest.sonnet_55_max_tokens_floors` records these constants.

## Price map

Exact id `claude-sonnet-5-5` maps to `PROVIDER_PRICE_MAP["anthropic_sonnet_5_5"]` (not the generic `anthropic_sonnet` $3/$15 bucket).

| Rate | USD / MTok |
|------|------------|
| Input | 2.00 |
| Output | 10.00 |
| Cache read | 0.10 |
| Cache write (5 min) | 2.50 |
| Cache write (1 h) | 4.00 |

`price_map_date`: **2026-11-12** (source: Anthropic pricing, fetched 2026-11-12). Thinking tokens bill as **output**; preflight and `estimated_cost_usd` use output token counts from the API when present.

## Run manifest (`config_snapshot`)

Each queued run stores:

- `anthropic_model_resolved`, `anthropic_thinking`, `anthropic_effort`
- `anthropic_price_map_key`, `anthropic_price_map_date`
- `run_manifest` — resolved model, thinking, effort, price map date, optional `sonnet_55_max_tokens_floors`
- `run_manifest.llm_request_log_file_pattern` — `{simulation_id}_llm_requests.jsonl`

## Request payload logging (two locations)

### 1. Per simulation run

File: `{transcript_dir}/{simulation_id}_llm_requests.jsonl` (default `transcript_dir`: `./data/transcripts`).

### 2. Ad-hoc / tooling calls

File: `{llm_request_log_dir}/adhoc_requests.jsonl` (default `llm_request_log_dir`: `./data/llm_requests`). Used for analyze, agent plan, scenario generate/fill, rubric interview, and any `llm_complete` outside a run-scoped logger.

Every log line is JSONL (one object per request). Logged fields (no API keys or headers):

| Field | Description |
|-------|-------------|
| `model_id` | Anthropic or LM Studio model id |
| `thinking` | `thinking` object sent on the wire (Anthropic Sonnet 5.5) |
| `effort` | `output_config.effort` when sent |
| `max_tokens` | Effective cap after Sonnet floors |
| `temperature` | Intended temperature (Anthropic omit) |
| `seed` | Run `random_seed` when recorded (not sent to Anthropic) |
| `call_site` | See call-path table above |

## Response parsing

Anthropic content blocks with `type: "thinking"` are skipped; agent output uses only `type: "text"` blocks (concatenated), so thinking blocks do not break state/Likert parsing.

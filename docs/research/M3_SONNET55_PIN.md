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

Environment defaults (when the resolved Anthropic model is Sonnet 5.5): `ANTHROPIC_THINKING_TYPE`, `ANTHROPIC_EFFORT` in `backend/.env` (see `config.py`).

## Anthropic request fields (verified 2026-11-12)

Source: [Claude Sonnet 5.5 migration guide](https://platform.claude.com/docs/en/models/sonnet-5-5/migration-guide) — example request uses:

- `model` — e.g. `claude-sonnet-5-5`
- `max_tokens`
- `messages`
- `thinking` — e.g. `{"type": "between_tools"}`
- `output_config` — e.g. `{"effort": "medium"}`

Senna sends these on every Anthropic Messages API call when the resolved model id is `claude-sonnet-5-5` (or a dated suffix). Temperature is **not** sent (existing behaviour).

## Validation (fail closed before HTTP)

| Rule | Reason |
|------|--------|
| `thinking.type == "disabled"` on Sonnet 5.5 | API returns HTTP 400 |
| `between_tools` with `effort` `xhigh` or `max` | API returns HTTP 400 |
| Invalid thinking type (not `between_tools` or `adaptive`) | Config error |
| Invalid effort (not low/medium/high/xhigh/max) | Config error |

`between_tools` is valid only with `low`, `medium`, or `high`.

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
- `run_manifest` — resolved model, thinking, effort, price map date
- `run_manifest.llm_request_log_file_pattern` — `{simulation_id}_llm_requests.jsonl`

## Request payload log (per LLM call)

File: `{transcript_dir}/{simulation_id}_llm_requests.jsonl` (JSONL, one object per line).

Logged fields (no API keys or headers):

| Field | Description |
|-------|-------------|
| `model_id` | Anthropic or LM Studio model id |
| `thinking` | `thinking` object sent on the wire (Anthropic only) |
| `effort` | `output_config.effort` when sent |
| `max_tokens` | Request cap |
| `temperature` | Intended temperature (Anthropic omit) |
| `seed` | Run `random_seed` recorded for audit (not sent to Anthropic) |
| `call_site` | e.g. `agent_turn`, `likert_round_end` |

When no run logger is attached, Anthropic calls still emit a structured `anthropic_request` line at INFO.

## Response parsing

Anthropic content blocks with `type: "thinking"` are skipped; agent output uses only `type: "text"` blocks (concatenated), so thinking blocks do not break state/Likert parsing.

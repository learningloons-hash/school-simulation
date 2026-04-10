# Review: Iteration 4
Date: 2026-04-02
Reviewer: Claude Opus (Architect)
Verdict: PASS_WITH_ISSUES

## Iteration Delta
- All 5 critical issues from iteration-2 review addressed: system/user prompt split, max_tokens raised to 1024, structured `<state>` JSON with keyword fallback, error handling via `run_simulation_task_guarded`, Claude API connector via router
- Config snapshot now persisted per run for reproducibility
- YAML scenario loading with fallback to embedded Python defaults
- Context clipping for reasoning-model chain-of-thought (strips `<state>`, trims thinking, tail-caps)
- Cross-round evolution instruction and peer context labeling (`[Round R, turn T]`)
- LM Studio error surfacing with parsed error body
- Test count: 4 → 18. Covers prompt shape, state parse, failure guard, YAML registry, context clip
- `.gitignore` and Python version pin (`>=3.11,<3.13`)

## Previous Review Issues — Status

| Iteration-2 Issue | Status | Notes |
|---|---|---|
| C1: Prompt is debug string | ✅ FIXED | System/user separation in `prompt_templates.py`. Persona identity in system, round context in user. |
| C2: max_tokens=64 | ✅ FIXED | Default 1024, configurable per-run (64–8192). |
| C3: Keyword state update | ⚠️ PARTIALLY | `<state>` JSON parse preferred, keyword fallback retained. See I1 below. |
| C4: No error handling | ✅ FIXED | `run_simulation_task_guarded` with failure_reason column. |
| C5: No Claude connector | ✅ FIXED | `claude_client.py` + `router.py` with `lmstudio`/`anthropic` dispatch. |
| I1: No config snapshot | ✅ FIXED | Full config JSON persisted at run creation. |
| I2: No YAML personas | ✅ FIXED | `scenarios/data/psle_reform_mvp.yaml` with loader + fallback. |
| I3: Duplicate venvs | ⚠️ PARTIAL | `.gitignore` added but both dirs may still exist on disk. |
| I4: Python 3.14 | ✅ FIXED | `pyproject.toml` pins `>=3.11,<3.13`. |
## Critical Issues

None. No blocking issues for iteration progression.

## Important Issues

### I1: `<state>` JSON + keyword fallback is a validity concern
- Severity: IMPORTANT
- Files: `backend/src/mirofish_backend/simulation/orchestrator.py` (`_apply_state_from_response`, `_apply_state_update_keyword`)
- Problem: The keyword fallback silently activates when the LLM doesn't produce a `<state>` block. This means two runs could use fundamentally different state-update mechanisms without any signal in the data. An examiner would ask: "How do you know which state updates came from structured extraction vs keyword counting?" Currently there's no per-turn flag recording which path was taken.
- Fix: Add a `state_source` field to `agent_turns` (or a new column): `"structured"`, `"keyword_fallback"`, or `"llm_error"`. Log it per turn. This lets you measure structured-parse success rate per model and flag runs where fallback dominated. For thesis validity, you'll want to report: "X% of turns used structured extraction, Y% fell back to heuristic."
- Thesis note: Long-term, consider a **dedicated extraction pass** — a second LLM call that reads the agent's response and outputs only the state JSON. This decouples state assessment from the agent's willingness to follow formatting instructions. But the current approach is adequate for Phase 1 if you track and report the parse rate.

### I2: Anthropic API key could leak into config_snapshot
- Severity: IMPORTANT
- Files: `backend/src/mirofish_backend/api/simulations.py` (lines ~150-170)
- Problem: `config_snapshot` records `anthropic_model` and `lmstudio_base_url` but not the API key. Good. However, the `anthropic_api_key` flows through `run_simulation_task_guarded` kwargs — if anyone adds logging of kwargs or expands config_snapshot, it could leak. There's no explicit redaction guard.
- Fix: Add a comment `# SECURITY: never persist anthropic_api_key` near the config_snapshot dict. Optionally, add a `_REDACT_KEYS` set in the config snapshot builder that strips sensitive fields. Also: the empty-string default for `anthropic_api_key` means a user who forgets to set it gets a confusing httpx error deep in the run, not a clear early failure.
- Quick win: In `run_simulation_task` (or the guarded wrapper), if `provider == "anthropic"` and `anthropic_api_key` is empty/whitespace, raise `ValueError("ANTHROPIC_API_KEY not set")` immediately before entering the round loop.

### I3: Prompt system message still dumps beliefs as raw dict
- Severity: IMPORTANT
- Files: `backend/src/mirofish_backend/llm/prompt_templates.py` (line 20)
- Problem: `f"- Beliefs: {beliefs}\n"` produces `- Beliefs: {'trust_in_moe_policy': 0.55, 'risk_aversion': 0.45, ...}` — a Python dict repr in the system prompt. Similarly demographics. This is better than iteration 2's flat dump, but for a thesis instrument the system prompt should read as natural prose or structured YAML, not Python syntax.
- Fix: Convert beliefs and demographics to readable format: either YAML-style (`trust_in_moe_policy: 0.55`) or natural prose (`You have moderate trust in MOE policy (0.55/1.0) and low risk aversion (0.45/1.0)`). A simple helper: `"\n".join(f"  {k}: {v}" for k, v in beliefs.items())`.

### I4: YAML personas lack psychological profile fields
- Severity: IMPORTANT
- Files: `backend/src/mirofish_backend/scenarios/data/psle_reform_mvp.yaml`
- Problem: The architecture spec requires: `openness_to_change`, `policy_compliance_tendency`, `professional_identity_strength`, `risk_aversion`, `workload_sensitivity` as explicit persona dimensions. Currently these are partially embedded in `beliefs` (e.g., `risk_aversion: 0.6`) but not in a standardized `psychological_profile` section. The system prompt doesn't use them distinctly.
- Fix: Add a `psychological_profile` block to each persona in the YAML. Update `PersonaTemplate` dataclass and the system prompt builder to include these as a distinct section. This matters because these dimensions are directly tied to Lipsky/Spillane/Trinidad theoretical constructs — examiners will look for explicit operationalization.
### I5: Context clipping obscures audit trail — but acceptable with DB logging
- Severity: MINOR
- Files: `backend/src/mirofish_backend/llm/context_clip.py`
- Problem: Clipping peer `raw_response` for prompts means the LLM sees truncated context. The review request asks: "Does clipping undermine auditability?"
- Answer: **No, this is fine.** Full `raw_response` is persisted in `agent_turns.raw_response` in the DB. The clipped version only appears in the prompt context. The `raw_prompt` column stores the full prompt including clipped peer text, so you can always trace what the agent actually saw. The only risk is if someone assumes `raw_prompt` contains full peer responses — add a brief note in methodology docs that peer context is clipped for token budget but full responses are in the transcript table.

### I6: No token counting per turn
- Severity: IMPORTANT
- Files: `backend/src/mirofish_backend/simulation/orchestrator.py`, `backend/src/mirofish_backend/llm/router.py`
- Problem: The architecture spec requires `token_count_input` and `token_count_output` per agent turn. Neither the LM Studio client nor the Claude client extracts token usage from the response. This data is essential for: (a) cost tracking across model comparison runs, (b) reporting in the thesis methodology, (c) detecting when agents hit max_tokens (truncated output).
- Fix: Both APIs return usage data. LM Studio: `data["usage"]["prompt_tokens"]` and `data["usage"]["completion_tokens"]`. Anthropic: `data["usage"]["input_tokens"]` and `data["usage"]["output_tokens"]`. Return a `(text, input_tokens, output_tokens)` tuple from both clients. Add columns to `agent_turns` and persist.

## Minor Issues

### M1: `__import__("uuid")` anti-pattern still in repo.py
- Files: `backend/src/mirofish_backend/db/repo.py`
- Fix: Replace with `import uuid` at top of file.

### M2: Frontend still uses inline styles, no UI library
- Files: `frontend/src/App.tsx`
- This is fine for now but will need shadcn/ui + Tailwind before thesis defense presentation.

### M3: Anthropic model default is `claude-3-5-haiku-20241022`
- Files: `backend/src/mirofish_backend/config.py` (line 22)
- This is an older model string. For Phase 1 comparison runs you'll want `claude-sonnet-4-6` or `claude-opus-4-6`. Not a code issue — just update the env var when running.

## Answers to Focus Questions

**1. Is `<state>` JSON + keyword fallback adequate for a thesis instrument?**
Adequate for Phase 1 if you: (a) track parse success rate per turn (see I1), (b) report the rate in methodology, (c) acknowledge keyword fallback as a limitation. A dedicated extraction pass is better long-term but not blocking.

**2. Does clipping peer raw_response undermine auditability?**
No. Full text in DB. Clipped text in prompt. Both are logged. Document the distinction in methodology. (See I5.)

**3. Anthropic path failure modes?**
Empty API key produces a confusing error deep in the run. Add early validation (see I2). Also: httpx timeout at 120s may be too short for Opus on complex prompts — consider making it configurable. The `anthropic-version: 2023-06-01` header is old but still works; update to latest when convenient.

**4. Does agent exclusion + labels correctly address multi-round continuity?**
Yes. The implementation is solid: current agent excluded from "others" block, round/turn labels on peer lines, evolution instruction for round > 1, widened interaction window on first turn of later rounds, default policy text for unscheduled rounds references prior dialogue. This is good design for maintaining conversational continuity without self-echo.

**5. Gaps vs long-term architecture?**
See Architecture Alignment table below. Major gaps: RAG pipeline, validity module, hybrid/comparison router modes, 3-layer memory, FSBB scenario.
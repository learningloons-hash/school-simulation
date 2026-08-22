# senna-iter-51 — Reflection (closeout)

## Delivered

- **Trigger:** After each agent turn once importance is known — per-turn mode immediately after scoring; batch mode at round end. Accumulates `importance_score` for unlinked observations; fires when sum ≥ `reflection_trigger_threshold` (default **150**, exposed as tunable config — not documented as validated best practice).
- **Synthesis:** Dedicated LLM call via `reflection_prompts.py` v1; parse provenance `model_parsed` / `repaired` / `fallback`.
- **Persist:** `agent_reflections` table with `source_turn_ids` JSON, `accumulated_importance`, token counts.
- **Retrieval:** Reflections merged into self-memory pool; prompt lines prefixed `[reflection]`; weighted path embeds via iter-50 memory index.
- **Config/API:** `reflection_enabled`, `reflection_trigger_threshold`, `reflection_prompt_version` — Settings, POST `/simulations/run`, preflight, `config_snapshot`, `reflection_audit` at run end.
- **Export:** `EXPORT_VERSION` → **14**; `agent_reflections` in bundle + ZIP CSV.

## Trigger timing (documented choice)

**After each agent turn** (not end-of-round batch), once that turn's importance is available — keeps provenance aligned with the triggering observations.

## Architectural interview

No automated interview re-run this iter. Export includes full reflection + provenance for iter-47 tooling to consume later. **Interview `reflection` category improvement vs real baseline not measured here** — that remains a manual / iter-52+ finding.

## Tests

`tests/test_senna_iter51_reflection.py` — parse paths, flag-off regression, threshold fire/no-fire, provenance + export.

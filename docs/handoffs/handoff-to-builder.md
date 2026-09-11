# Handoff to Builder

**Ritual:** Architect seeds this file before each Builder session. Builder implements **only** what is under **Active task** below. When finished (tests pass, commit), Builder fills [`handoff-to-architect.md`](./handoff-to-architect.md) and stops.

---

## Active task — mirror persona-rich run artefacts to senna-sstrf-study (GM-F 2026-09-11 ruling filed)

**Spec:** GM-F ruled persona differentiation **PASS** on the 2026-09-11 sq_reading_culture
persona-rich run (R10 support stdev 0.19 rich vs 0.06 neutral, range 0.62 vs 0.20 — see
`docs/research/runs/sq_reading_culture/2026-09-11-persona-rich/GM_RULING_PERSONA_DIFFERENTIATION.md`).
Ops already committed the safe/public fixes to `school-simulation`/`main` at `514860e`: the
`SIMULATION_RUN_WORKFLOW.md` Step 8 redaction + persona-blinding rules, and both harness
scripts (`run_sq_reading_persona_rich.py`, `run_sq_reading_partc.py`) — including a fix to the
packaging bug that had been blanking real `support_level`/`resistance_level`/`workload_stress`
cells (a blanket configured-value scrub was matching real measurement values, not a missing
redaction pattern). **Do not redo that part.**

**What's left — private/study-repo material only**, per
`docs/handoffs/GM_UPDATE_PROVENANCE_2026-09-09.md` ("sq_reading run artefacts... — Ops
history" is private, mirrored to `senna-sstrf-study`, not authoritative on
`school-simulation`). These files are written to disk under
`docs/research/runs/sq_reading_culture/2026-09-11-persona-rich/` but not committed anywhere:

| File | Purpose |
|------|---------|
| `GM_RULING_PERSONA_DIFFERENTIATION.md` | The filed GM ruling |
| `analyst_output/ANALYSIS_BLIND_12RUNS.md` | Blind content analysis |
| `analyst_label_key.json` | Runner-held RUN-A…L → simulation/cell/seed key |
| `PERSONA_RICH_MECHANICS_REPORT.md` | Mechanics report |
| `persona_rich_manifest.json` | Run manifest |
| `analyst_redaction_check.json` | Automated redaction scan result |

**Task:**

1. Commit these files using whatever mechanism currently gets sq_reading / validity-v2
   material into `senna-sstrf-study` — check how the 2026-09-10 Part C run's equivalent
   directory (`docs/research/runs/sq_reading_culture/2026-09-10/`) got there. **Do not assume
   the `sstrf-local` branch is the active mechanism** — its tip is a stale August commit
   (`4701365`, senna-iter-44) unrelated to this material; confirm before using it.
2. Push to `senna-sstrf-study`.
3. Do **not** touch `school-simulation`/`main`'s `.gitignore` or force-add these files there —
   they stay off the public repo per the classification above.
4. Report back the local commit hash and what it became on the study remote, in the same
   style as `docs/handoffs/GM_UPDATE_PROVENANCE_2026-09-09.md`'s verifier table.

---

## Completed (do not redo)

- **Persona differentiation build + live run (GM-F 2026-09-11)** — `sq_reading_culture_rich.yaml`
  + `sq_reading_culture_adverse_rich.yaml`, `scripts/run_sq_reading_persona_rich.py`,
  `test_sq_reading_culture_rich_fixtures.py` (Builder); live 6-run execute + blind 12-run
  analyst package (Ops/Runner); **GM ruled PASS** 2026-09-11. Gap flagged: `belief_posture`
  not in GM persona spec — omitted (orchestrator defaults to neutral).

- Arc 12 (`senna-iter-54`–`58`, pre-reg signed)
- `sstrf-validity-v2` Parts A–D harness (`ddcd417`…`f02adef`); live sims + elicitation complete; scoring escalated to human-only
- **`scenario-context-field` Part A** (`b122a0d`) — `ScenarioConfig.context` + prompt injection + sentinel test
- **`scenario-context-field` Part B** (`c238fa9`) — `sq_reading_culture` / `sq_reading_culture_adverse` fixtures + provenance + round-trip serialize

### Part B spec (closed)

| Deliverable | Status |
|-------------|--------|
| `sq_reading_culture.yaml` + `sq_reading_culture_adverse.yaml` in `scenarios/data/` | ✅ |
| Identical `policy_events` + persona roster; context only differs | ✅ |
| Provenance JSON committed | ✅ (`dirty: true` — study repo untracked; context authored in-product) |
| `scenario_config_to_document()` round-trips `context` | ✅ |
| Tests in `test_sq_reading_culture_fixtures.py` | ✅ |

**Gap flagged:** Study-repo adverse YAML had round-5 policy shock — removed for context-only differentiation. Context strings are GM-F ecological contrasts, not CIEPSS site claims. MT department role still absent (known gap from source).

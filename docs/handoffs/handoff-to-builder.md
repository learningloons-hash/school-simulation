# Handoff to Builder

**Ritual:** Architect seeds this file before each Builder session. Builder implements **only** what is under **Active task** below. When finished (tests pass, commit), Builder fills [`handoff-to-architect.md`](./handoff-to-architect.md) and stops.

---

## Active task — backfill 2026-09-10 Part C run to senna-sstrf-study (Mark, 2026-09-11)

**Context:** the persona-rich mirror (previous Active task) is done — reported by Cursor as
committed to `senna-sstrf-study` at `f5e77ec` (push range `437d72b` → `f5e77ec`), via direct
commit to the separate checkout at `/Users/home/cursor-projects/project-1/senna-sstrf-study`,
same mechanism used for the 2026-09-01 and 2026-09-03-tempsweep syncs. **Not** via
`sstrf-local` in this repo. Ops could not independently verify this push (no reachable
`senna-sstrf-study` checkout or GitHub network access from the Ops session) — take the report
at face value pending anyone with access double-checking `git log` on that checkout.

That same report surfaced a gap: **`docs/research/runs/sq_reading_culture/2026-09-10/`
(the Part C run) has no record in `senna-sstrf-study` at all**, before or after the
2026-09-11 commit — it only ever existed in the gitignored mirofish-mvp working tree. Mark
has decided (2026-09-11) to backfill it, using the same file selection as the persona-rich
commit — the ops-bundle documents only, not the bulk redacted/raw zips or the run log (Mark
confirmed 2026-09-11: `analyst_package/`, `exports/`, and `run.log` stay local-only for both
runs, consistent with the tempsweep precedent).

**Files to commit** (all under `docs/research/runs/sq_reading_culture/2026-09-10/`):

| File | Purpose |
|------|---------|
| `PARTC_EXECUTION_STATUS.md` | Execution status record |
| `PARTC_MECHANICS_REPORT.md` | Mechanics report |
| `analyst_label_key.json` | Runner-held RUN-A…L → simulation/cell/seed key |
| `analyst_output/ANALYSIS_BLIND_12RUNS.md` | Blind content analysis |
| `analyst_redaction_check.json` | Automated redaction scan result |
| `partc_manifest.json` | Run manifest |

**Explicitly excluded** (stay local-only, do not commit): `analyst_package/*.zip` (12 files),
`exports/*.zip` (16 files), `run.log`.

**Task:**

1. Commit the six files above to `senna-sstrf-study`, same mechanism as the persona-rich
   commit (direct commit to the separate local checkout, not `sstrf-local`).
2. Push.
3. Do **not** touch `school-simulation`/`main` — this material stays off the public repo per
   `docs/handoffs/GM_UPDATE_PROVENANCE_2026-09-09.md`'s classification, same as before.
4. Report back the local commit hash and what it became on the study remote, same
   verifier-table style as the last two reports.

---

## Completed (do not redo)

- **Persona differentiation build + live run (GM-F 2026-09-11)** — `sq_reading_culture_rich.yaml`
  + `sq_reading_culture_adverse_rich.yaml`, `scripts/run_sq_reading_persona_rich.py`,
  `test_sq_reading_culture_rich_fixtures.py` (Builder); live 6-run execute + blind 12-run
  analyst package (Ops/Runner); **GM ruled PASS** 2026-09-11. Gap flagged: `belief_posture`
  not in GM persona spec — omitted (orchestrator defaults to neutral).
- **Mirror persona-rich run artefacts to senna-sstrf-study** — reported complete by Cursor,
  `f5e77ec` (push range `437d72b` → `f5e77ec`); 6 files (GM ruling, mechanics report,
  manifest, label key, redaction check, blind analysis). `analyst_package/`, `exports/`,
  `run.log` left local-only per Mark's 2026-09-11 decision.

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

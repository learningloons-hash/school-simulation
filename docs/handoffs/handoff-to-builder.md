# Handoff to Builder

**Ritual:** Architect seeds this file before each Builder session. Builder implements **only** what is under **Active task** below. When finished (tests pass, commit), Builder fills [`handoff-to-architect.md`](./handoff-to-architect.md) and stops.

---

## Active task — commit full export data (both runs) to senna-sstrf-study (GM-F, 2026-09-11 — supersedes local-only decision)

**GM-F overruled the earlier "leave it local" call.** The headline persona-differentiation
finding (R10 support stdev 0.19 rich vs 0.06 neutral) is a computed statistic pulled from
`agent_state_snapshots.csv` inside the export zips. If the zips live only on one Mac mini,
nobody can check the number — the exact problem closed for the pre-registration, one layer
down. Raw + redacted exports for **both** runs now go to `senna-sstrf-study`, alongside the
ops bundle. Findings/platform stay public; research data stays private — same split already
in force, just applied completely this time. Total size across both runs is ~4.6MB (checked:
1.2M + 648K + 1.1M + 1.7M) — the size objection doesn't hold. Nothing in them is sensitive:
invented personas, a public programme description, LLM-generated text.

**Ops has already added SHA-256 hashes** of every export and analyst-package zip into both
manifests (`persona_rich_manifest.json`, `partc_manifest.json`), under new keys
`export_sha256` and `analyst_package_sha256` (filename → hex digest), per GM-F: "anyone
verifying it needs to confirm they're looking at the same bytes we were." Spot-checked one
hash against `sha256sum` directly — matches. **Do not regenerate the manifests or re-zip
anything** — commit the files as they are on disk now; the hashes describe those exact bytes.

**Commit everything under both run directories** (all of
`docs/research/runs/sq_reading_culture/2026-09-11-persona-rich/` and
`docs/research/runs/sq_reading_culture/2026-09-10/`), i.e. the ops-bundle documents already
identified plus, for each run:

| Directory | Files |
|-----------|-------|
| `analyst_package/` | 12 zips (RUN-A…L), persona-rich and Part C each |
| `exports/` | 6 zips (persona-rich), 17 zips (Part C) |

`run.log` in each run directory is **still excluded** (execution log, not needed to
reproduce the statistic, not mentioned in GM-F's ruling) — flag if that should change too.

**Task:**

1. Commit the full contents of both run directories (ops bundle + `analyst_package/` +
   `exports/`, manifests already updated with hashes) to `senna-sstrf-study`, same mechanism
   as the prior sync (direct commit to the separate local checkout, not `sstrf-local`).
2. Push.
3. Do **not** touch `school-simulation`/`main` — this material stays off the public repo per
   `docs/handoffs/GM_UPDATE_PROVENANCE_2026-09-09.md`'s classification, unchanged.
4. Report back local commit hash + what it became on the study remote, same verifier-table
   style as before, and confirm zip count committed per run directory (18 for persona-rich,
   29 for Part C, plus the ops-bundle documents).

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

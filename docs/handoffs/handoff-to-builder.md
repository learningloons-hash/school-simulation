# Handoff to Builder

**Ritual:** Architect seeds this file before each Builder session. Builder implements **only** what is under **Active task** below. When finished (tests pass, commit), Builder fills [`handoff-to-architect.md`](./handoff-to-architect.md) and stops.

---

## Active task — *(none — awaiting Architect seed for next workstream)*

---

## Completed (do not redo)

- **Full export data + SHA-256 hashes → senna-sstrf-study (GM-F, 2026-09-11)** — reported
  complete by Cursor: `92a16c6` (push range `f5e77ec` → `92a16c6`), 54 files. Both run
  directories (`2026-09-10` Part C: 29 zips + 6 ops docs; `2026-09-11-persona-rich`: 18 zips
  + manifest hash update) fully committed — ops bundle, `analyst_package/`, `exports/`, both
  manifests carrying `export_sha256` / `analyst_package_sha256`. `run.log` excluded in both,
  as scoped. `school-simulation` untouched. Ops could not independently verify (no reachable
  `senna-sstrf-study` checkout or working GitHub auth from the Ops session — `git fetch study`
  now fails on missing credentials rather than the earlier 403, still no path through).
  **Flagged by Cursor, not yet actioned:** the zips needed `git add -f` — `senna-sstrf-study`'s
  own `.gitignore` still blocks `docs/research/runs/**/*.zip` by default, so every future
  commit under these paths needs the same force-add until/unless gitignore exceptions are
  added there. Worth a small follow-up if this pattern continues (mirofish-mvp hit the same
  shape of problem with `validity_v2_scoring_manifest.json` — deep-nested negation patterns
  don't reliably re-include a file once a parent directory is `.gitignore`d, so the practical
  fix is a scoped `!path` exception per committed path, not a blanket unignore).

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

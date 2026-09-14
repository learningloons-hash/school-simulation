# Handoff to Builder

**Ritual:** Architect seeds this file before each Builder session. Builder implements **only** what is under **Active task** below. When finished (tests pass, commit), Builder fills [`handoff-to-architect.md`](./handoff-to-architect.md) and stops.

---

## Active task — *(none — awaiting Architect seed)*

---

## Completed — align `senna-sstrf-study` `.gitignore` with data policy (Architect seed 2026-09-14)

**Repo:** work in the **separate** `senna-sstrf-study` checkout (`/Users/home/cursor-projects/project-1/senna-sstrf-study` or equivalent). **Not** `school-simulation` / `mirofish-mvp` — different policy there, out of scope.

**Problem:** `.gitignore` lines 47–49 still exclude zips, export JSON, and elicitation JSON under `docs/research/runs/`. Policy reversed 2026-09-11 (GM-F): research data belongs in the **private** repo. All 47 export zips at `92a16c6` are tracked only via `git add -f`. Next run silently drops exports → unverifiable findings.

**Architect correction on negation:** the earlier “deep-nested negation is unreliable” note in Completed below applied to **directory** excludes (parent ignored → child cannot be re-included). Rules 47–49 are **file globs**, not directory excludes — negations *would* work here. **Do not** add per-run `!` exceptions; delete the obsolete rules instead.

---

### Decision 1 — delete rules 47–49

**DELETE** the block (comment + three lines):

```
# SSTRF runtime exports contain substantive simulation text; keep only metric summaries
docs/research/runs/**/*_export.json
docs/research/runs/**/*.zip
docs/research/runs/**/elicitation/*.json
```

**Replace** with a one-line policy comment, e.g.:

```
# Research run artefacts (exports, elicitation, zips) are committed in this private repo.
```

**Do not preserve** rules “because they exist.” Nothing else under `docs/research/runs/` needs a blanket exclude.

**Already covered elsewhere (do not duplicate):**

| Material | Exclusion | Where |
|----------|-----------|--------|
| `run.log` | `*.log` (line 37) | ✅ keep |
| Source PDFs | `docs/research/sources/*.pdf` (line 44) | ✅ keep |
| `backend/data/`, sqlite, transcripts | lines 13–21 | ✅ keep |

---

### Decision 2 — line 50: **keep**, deliberately

**KEEP** (with explicit comment):

```
# CIEPSS validity scoring only: trial-label → simulation_id map; decodes blind human-scoring packets.
# Excluded even in this private repo — scoring worksheets may be shared without this key.
docs/research/runs/ciepss_school_b/scoring/trial_label_map.json
```

**Not** the same as `analyst_label_key.json` in sq_reading run dirs — those **are** committed alongside blind packages in the private repo by design (`92a16c6`).

---

### Deliverables

| # | Deliverable |
|---|-------------|
| 1 | `.gitignore` edit per decisions above |
| 2 | **Regression guard** — `backend/tests/test_study_repo_gitignore.py` (or `scripts/` + test): create a temp mini-repo (or use `git check-ignore --no-index`) and assert a representative **export zip**, **`*_export.json`**, and **elicitation json** under `docs/research/runs/` are **not** ignored; then create a fresh run dir with a dummy zip, `git add -A` (no `--force`), assert zip is staged |
| 3 | **Manifest hash ↔ git tracking** — `scripts/validate_run_manifest_git_tracking.py` + test: for every `export_sha256` / `analyst_package_sha256` entry in run manifests under `docs/research/runs/`, assert the file is tracked (`git ls-files --error-unmatch`): `exports/{key}` and `analyst_package/{key}` relative to manifest directory. Fail loudly on mismatch. Run against committed manifests at `2026-09-10/partc_manifest.json` and `2026-09-11-persona-rich/persona_rich_manifest.json` |
| 4 | Commit + push to `senna-sstrf-study` `main` |

---

### Acceptance (Architect will check)

| Check | How |
|-------|-----|
| **(a)** | `git check-ignore --no-index -v` → **no match** for: (1) `docs/research/runs/sq_reading_culture/2026-09-10/exports/0080425ca6be466d80146d4b97266307.zip`, (2) any `docs/research/runs/**/*_export.json` path if one exists on disk, (3) any `docs/research/runs/**/elicitation/*.json` under `ciepss_school_b/validity_v2/` |
| **(b)** | New test passes: dummy zip stages with `git add -A` without `-f` |
| **(c)** | `git status` after `.gitignore` change shows **no** unexpected new tracked files before commit (rule change must not sweep in previously-correct exclusions like `trial_label_map.json` or `*.log`) |
| **(d)** | `validate_run_manifest_git_tracking.py` exits 0 on current `92a16c6` manifests |

---

### Out of scope

- `school-simulation` / `mirofish-mvp` `.gitignore`
- Re-committing or rewriting `92a16c6` artefacts
- Changing manifest hash contents (read-only validation)

When done: fill [`handoff-to-architect.md`](./handoff-to-architect.md) with commit hash + `git check-ignore` / test output.

**Closed:** `46c57c2` on `senna-sstrf-study` `main` (pushed).

---

## Completed (do not redo)

- **`senna-sstrf-study` `.gitignore` data policy** (`46c57c2`) — delete export zip/json/elicitation excludes; keep `trial_label_map.json`; regression test + manifest validator

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
  **Correction (Architect, 2026-09-14):** that generalization was wrong for this case — the
  senna-sstrf-study rules were file-glob excludes, not directory excludes, so a plain negation
  would have worked. Fixed by deleting the obsolete rules outright instead (see below), which
  is cleaner than negation either way. Resolved: `46c57c2`.

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

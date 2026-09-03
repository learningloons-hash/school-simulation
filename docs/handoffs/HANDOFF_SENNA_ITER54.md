# HANDOFF_SENNA_ITER54 — Fixture Reunification, Confound Test, Individuation Report

**Owner:** GM-F → Senna-Ops → Cursor Architect → Cursor Builder
**Date:** 2026-08-24
**Arc:** 12 — Freeze and Study Readiness (`docs/handoffs/HANDOFF_SENNA_ARC12.md`)
**Iteration:** `senna-iter-54` (expansion of ARC12 §1; do not start `senna-iter-55`)
**Predecessor:** Arc 11 closed **PASS WITH ISSUES** (GM-F, 2026-08-24) — [`senna-iter-53-closeout.md`](../iterations/senna-iter-53-closeout.md)
**Status:** **Option 1 decided (Mark, 2026-08-24).** Ready to seed Architect. Comprehensive — no shortcuts, per Mark's instruction.

---

## 0. Context — what GM-F ruled and why this doc exists

GM-F's Arc 11 ruling, for the record (binds everything below):

- **Arc 11: PASS WITH ISSUES.** Build scope complete, 12/12 clean, the reliability bug was handled correctly (redone from fresh simulation, not salvaged).
- **Open question answered: not the contradiction case.** Contradiction requires a test; MemBench was ceilinged so there wasn't one. The prioritisation hypothesis stays **untested**, not refuted.
- **Arc 12 pre-registration does NOT wait on MemBench/interview resolution.** That pre-reg governs the SSTRF study, scored by an independent judge against CIEPSS propositions. MemBench and the architectural interview are platform-development instruments answering a different question. **Do not let iter-54 or any later iteration block on "fixing" those diagnostics.**
- **iter-51's DoD was unsatisfiable** (reflection category was already at the 2.00 ceiling before reflection was built) — GM-F's error in the original handoff, not a build defect. No action item.
- **Three things the closeout missed, now binding on iter-54's design:**
  1. The Arc 11 ablation tested a configuration the study will never run (dolphin-8b, 3 agents, 5 rounds, `fsbb_comparator`, synthetic chain network) against a study spec that is Anthropic, 8 actors, 15–20 rounds, `ciepss_school_b`, documented network. Every dimension differs.
  2. The interview ceiling is ~60% saturated, not partial: `reflection` sits at 2.00 in all four Arc 11 arms, `self_knowledge` at 2.00 in all four, `planning` only moves 2.00→1.89. Three of five categories carry no dynamic range at all.
  3. The Arc 11 ablation network was not identical to the Arc 10 baseline network — an uncontrolled variable that should have been flagged as a limitation in the closeout and wasn't.
- **The dispersion finding is the arc's most important result, not a footnote.** Baseline cross-agent interview-score stdev ≈ 0.00 (agents give each other's answers); `+importance+retrieval` raises it to ≈ 0.31. Report it in Part C as a **study-validity finding**: if the shipped architecture produces near-identical actors, the study's propositions (P1 on authority, P3 on self-concept, P4 on adaptation scale) cannot be tested regardless of scoring quality.
- **Blocking defect:** `backend/src/mirofish_backend/scenarios/data/ciepss_school_b.yaml` is not in the platform repo — caught by `.gitignore` (line 50) in the 2026-08-18 repo split, lives only on the study side (`study` remote → `senna-sstrf-study.git`). The platform cannot currently load the case the study is meant to run.

**Mark's ruling (2026-08-24): go with Option 1** (fixture stays in the study repo; platform loads it via the existing `user_scenarios` config path, not a repo restructure). Be comprehensive — no shortcuts. This doc is the full architect/builder spec for `senna-iter-54`. **Per standing feedback ([[feedback_architect_incremental_commits]]), each part below is independently committable — commit and close out per part, not once at the end of the iteration.**

---

## 1. Part A — Fixture reunification (Option 1, decided)

### 1.0 Why Option 1, for the record (resolves-in-a-year requirement)

| # | Option | Verdict |
|---|---|---|
| **1** | **Fixture stays in the study repo; platform loads external scenario config via the existing `user_scenarios` DB path.** | **Chosen.** `backend/src/mirofish_backend/scenarios/loader.py::load_scenario_for_run(sqlite_path, scenario_id)` already checks a `user_scenarios` SQLite table before falling back to the package registry. `db/repo.py` already has `upsert_user_scenario`, `get_user_scenario_row`, `list_user_scenario_rows`, `user_scenario_exists`. Zero schema/loader changes needed for the scenario document itself — only a seeding script (§1.2) and, if the fixture uses RAG, a matching mechanism for corpus text (§1.3, a genuine gap this doc found that ARC12 didn't scope). |
| 2 | Fixture lives in the public repo | Rejected. Re-introduces the exact coupling the 2026-08-18 split removed, and is only viable if the YAML is confirmed to contain no protected material — narrower and more fragile than Option 1 regardless. |
| 3 | Study repo vendored as a submodule at a pinned commit | Rejected as heavier than the problem needs. A submodule requires `--recurse-submodules` on every clone (or a documented follow-up step everyone will forget at least once), CI credentials for a private repo, and duplicates a loading mechanism (non-bundled scenario) the codebase already has via `user_scenarios`. |

### 1.1 Pre-flight checklist — Architect does this FIRST, before writing any code

Do these in order; each gates the next. Report results in the iter-54 closeout even if the answer changes scope.

1. **Get a local checkout of `senna-sstrf-study`** (the `study` git remote already configured on `main`: `https://github.com/learningloons-hash/senna-sstrf-study.git`). Note the exact commit hash you check out.
2. **Open `ciepss_school_b.yaml` directly and confirm GM-F's non-negotiable constraint**: it contains only roster, roles, network, policy events, and `# source: p.N` provenance comments — no reproduced CIEPSS/MOE source text. This has not been verified by anyone in this handoff chain yet (Ops does not have access to the study repo from the cloud session). **If it fails this check, stop and escalate to GM-F before writing any code — Option 1 (or any option) is off the table until the content itself is clean.**
3. **Check `rag_enabled` and `rag_corpus_paths` on the scenario document.** This determines whether §1.3 (corpus reunification) is in scope for this iteration:
   - If `rag_enabled: false` or absent → skip §1.3 entirely, note that in the closeout.
   - If `rag_enabled: true` → §1.3 is required. Read the referenced corpus file(s) too and apply the **same** "no reproduced source text" scrutiny — corpus files are, by design, meant to hold real briefing text, so this check is not a formality here. If the corpus text itself is the copyrighted/MOE material, it stays local-only under §1.3's mechanism; it must never be considered for the public repo (Option 2 above is not a fallback for corpus files even if it were chosen for the YAML).
4. **Locate the exact relative paths** of the YAML and (if applicable) the corpus directory inside the study repo checkout, and the study repo's default branch/tag convention. The seeding script (§1.2) takes these as arguments — there's no way to hardcode them correctly without this step.

### 1.2 Scenario document reunification — the seeding script

**New file:** `scripts/seed_scenario_from_study_repo.py`.

Mirror the validation path the platform already uses for user-authored scenarios (`backend/src/mirofish_backend/api/scenario_catalog.py::create_user_scenario`) rather than inventing a bespoke bypass:

```
validate_scenario_document(doc, is_update=<user_scenario_exists(...)>, allowed_corpus_paths=<list_allowed_corpus_paths()>)
```

**CLI arguments:**

| Flag | Required | Notes |
|---|---|---|
| `--study-repo-path` | yes | Local path to the `senna-sstrf-study` checkout. |
| `--scenario-id` | no, default `ciepss_school_b` | Kept generic — this script is the general "reunify an externally-held scenario" tool, not a one-off. |
| `--yaml-rel-path` | yes | Path to the scenario YAML *relative to `--study-repo-path`* (confirmed in §1.1 step 4). |
| `--corpus-rel-dir` | no | Path to the corpus directory relative to `--study-repo-path`, if `rag_enabled`. |
| `--sqlite-path` | no, default from `Settings` (same convention as `run_arc11_ablation.py --sqlite-path`) | Target DB to seed. Run once per environment that needs the scenario (dev machine, study-run machine). |
| `--force` | no | Re-seed even if `user_scenario_exists()` is already true — the script is idempotent (`upsert`) by default, `--force` is only needed to bypass a confirmation prompt on overwrite. |

**Behavior, in order:**

1. Resolve `--study-repo-path` to an absolute path; fail loudly if it isn't a git repo (`git -C <path> rev-parse --show-toplevel`).
2. **Check the study repo's working tree is clean** (`git -C <path> status --porcelain`). If dirty, **abort by default** with a clear message — an uncommitted local edit means the commit hash recorded in provenance (§1.4) would not actually describe what got seeded, which defeats the entire point of provenance. Allow a `--allow-dirty` escape hatch for local iteration, but it must print a loud warning and the emitted manifest must record `"dirty": true` so nobody mistakes it for a clean provenance record later.
3. Capture `source_commit = git -C <path> rev-parse HEAD` and `source_repo = git -C <path> remote get-url origin` (fall back to the `--study-repo-path` itself if no remote, with a warning).
4. Read and `yaml.safe_load` the file at `<study-repo-path>/<yaml-rel-path>`.
5. **If `--corpus-rel-dir` given:** copy every file under it into `backend/src/mirofish_backend/scenarios/data/<scenario_id>/` (creating the directory). This is the local, gitignored home for corpus text — see §1.3 for why this location and not something new. Do this *before* validation, so `list_allowed_corpus_paths()` (which scans that directory live) picks the files up.
6. Run `validate_scenario_document(...)`. **Errors abort the script with a non-zero exit and the full error list printed** — no partial/best-effort seeding. Warnings are printed but non-blocking, matching existing behavior in `scenario_catalog.py`.
7. `upsert_user_scenario(sqlite_path, scenario_id=..., display_name=..., document_json=json.dumps(doc), scenario_doc_version="1", source_repo=source_repo, source_commit=source_commit)` — see §1.4 for the two new kwargs.
8. Write/overwrite the manifest at `docs/diagnostics/<scenario_id>_provenance.json` (§1.4).
9. Print a summary: scenario id, sqlite path written to, source commit, corpus file count copied (if any), and the exact command to re-run this later (so it's copy-pasteable into a setup doc).

### 1.3 Corpus reunification (only if `rag_enabled: true` — confirm in §1.1 step 3)

**This is a real gap ARC12's handoff did not scope, and Ops's first draft of this handoff missed it too.** `backend/src/mirofish_backend/rag/corpus.py::load_scenario_corpus_texts()` hardcodes its root to `backend/src/mirofish_backend/scenarios/data/` on the **local filesystem** — it has no DB-backed override path the way scenario documents do. Fixing the scenario YAML's loading path (§1.2) does nothing for corpus text if the fixture uses RAG; that's a second, independent reunification problem.

**Chosen mechanism:** the seeding script (§1.2 step 5) copies corpus files into `backend/src/mirofish_backend/scenarios/data/<scenario_id>/` locally at seed time — the same directory `load_scenario_corpus_texts()` already resolves relative paths against, so **no code change is needed in `rag/corpus.py` or `validate.py`** — `list_allowed_corpus_paths()` already scans that directory fresh on every call. This keeps the whole reunification story to one mechanism (seed locally, gitignore locally, never commit) instead of two.

**`.gitignore` addition required** (mirror the existing single-file entry at line 50): add a directory entry, e.g.

```
backend/src/mirofish_backend/scenarios/data/ciepss_school_b/
```

right next to the existing `ciepss_school_b.yaml` line, so a future `git status` doesn't show the copied corpus files as untracked-and-alarming, and nobody accidentally `git add -A`s real CIEPSS source text into the public repo.

### 1.4 Provenance — schema change + manifest (this is what `iter-58` cites)

ARC12 §5 requires the frozen pre-registration to name "Fixture commit hash and repo — **study repo**, not `origin`." Two things carry that forward:

**Schema (`backend/src/mirofish_backend/db/schema.py`):** add columns to `user_scenarios` using the existing idempotent pattern (used ~20 times already in that file, e.g. `await _ensure_column(db, "simulation_runs", "converged_at_round", "INTEGER")`):

```python
await _ensure_column(db, "user_scenarios", "source_repo", "TEXT")
await _ensure_column(db, "user_scenarios", "source_commit", "TEXT")
await _ensure_column(db, "user_scenarios", "seeded_at", "TIMESTAMP")
```

**`db/repo.py`:** extend `upsert_user_scenario()` with optional `source_repo: str | None = None, source_commit: str | None = None` kwargs (default `None` so the two existing callers in `scenario_catalog.py` — user-authored scenarios via the UI — are unaffected and correctly show `NULL` provenance, since they aren't reunified fixtures). Update the `INSERT ... ON CONFLICT` SQL to set `seeded_at = CURRENT_TIMESTAMP` alongside the two new columns. Extend `get_user_scenario_row()` and `list_user_scenario_rows()` to return the new columns too — half-plumbing this through would leave provenance write-only, which is its own kind of shortcut.

**Manifest file, committed to the public repo** (safe — pointers only, no fixture content): `docs/diagnostics/ciepss_school_b_provenance.json`:

```json
{
  "scenario_id": "ciepss_school_b",
  "source_repo": "<resolved from git remote get-url origin in the study checkout>",
  "source_commit": "<full 40-char SHA>",
  "yaml_rel_path": "<confirmed in §1.1 step 4>",
  "corpus_rel_dir": "<confirmed in §1.1 step 4, or null>",
  "seeded_at": "<UTC ISO 8601, from the seeding run that produced this file>",
  "dirty": false
}
```

This file — not the DB row, which is local/runtime state and not committed — is what `iter-58`'s pre-registration should cite for "fixture commit hash and repo." Flag this pointer explicitly in the `iter-54` closeout so whoever writes `iter-58` doesn't have to rediscover it.

### 1.5 Tests — what CI can and cannot prove

The real `ciepss_school_b.yaml` is private, study-repo-only content. Public-repo CI has no access to it and must not be made to depend on it. Split verification accordingly — this split *is* the "no shortcuts" answer here, not a shortcut:

**`backend/tests/test_senna_iter54_scenario_reunification.py`** (naming convention matches `test_senna_iter52_arc11_ablation.py`), runs in normal CI, uses a small synthetic fixture — **not real CIEPSS content**:

- Check in `backend/tests/fixtures/dummy_external_scenario.yaml` — a minimal scenario (2–3 personas is enough) with `rag_enabled: true` and one short corpus `.txt`, shaped like a stand-in for `ciepss_school_b` but containing nothing sensitive.
- Test the seeding script's internals directly (import and call its functions, not subprocess) against a temp sqlite path and a temp "fake study repo" directory (a plain dir is enough; git-clean-check logic can be tested separately against a real temp git repo with `git init`).
- Assert: `user_scenario_exists()` is true after seeding; `load_scenario_for_run(tmp_sqlite, "dummy_external_scenario")` resolves and returns a `ScenarioConfig` with the expected personas; the corpus file lands under `scenarios/data/dummy_external_scenario/` and `load_scenario_corpus_texts()` picks it up; the `user_scenarios` row has non-null `source_repo`/`source_commit`/`seeded_at`; re-running the seeder (idempotency) doesn't duplicate rows or error.
- Assert the dirty-working-tree guard: seeding against a repo with an uncommitted change aborts by default and records `"dirty": true` only under `--allow-dirty`.

**Manual integration step — explicitly NOT part of default `pytest`, run once locally by whoever has the study repo checked out** (Architect, Builder, or Mark — whoever runs it, report the evidence in the closeout):

```bash
python3 scripts/seed_scenario_from_study_repo.py \
  --study-repo-path <path to senna-sstrf-study checkout> \
  --yaml-rel-path <confirmed in §1.1> \
  --scenario-id ciepss_school_b \
  --corpus-rel-dir <confirmed in §1.1, if applicable>
```

Then run one short smoke simulation against `ciepss_school_b` through the normal simulation API/CLI path (small round count — this is a load-bearing smoke check, not a study run; per the Arc 12 standing constraint, **do not read, cite, or score its substantive output**). Confirm it reaches terminal status with no errors. Record the simulation id and a one-line result in the `iter-54` closeout as the actual evidence that discharges ARC12's literal DoD ("the platform loads `ciepss_school_b` and runs a smoke simulation from a clean checkout").

### 1.6 Setup documentation (the "resolves in a year" deliverable)

Add a short section — new file `docs/SETUP_STUDY_FIXTURES.md`, linked from `docs/handoffs/README.md`'s table — covering: clone `senna-sstrf-study` at (or after) the commit in `ciepss_school_b_provenance.json`; run the seeding command from §1.5 with that checkout; verify with the smoke-simulation step. This is the artifact someone reads in a year when the local DB has been wiped or they're on a new machine.

### 1.7 DoD for Part A

- `dummy_external_scenario` CI test suite passes (§1.5).
- `ciepss_school_b` loads and a smoke simulation reaches terminal status from a clean checkout, evidence recorded in the closeout (§1.5 manual step).
- `docs/diagnostics/ciepss_school_b_provenance.json` committed and accurate.
- `docs/SETUP_STUDY_FIXTURES.md` exists and someone other than its author could follow it cold.
- `.gitignore` updated per §1.3 if corpus reunification was in scope.

---

## 2. Part B — The confound test (six runs, Anthropic tier)

### Sequencing — read before scheduling this

**Part B does not depend on Part A.** The Arc 11 ablation's `AblationRunProfile` defaults to `scenario_id="fsbb_comparator"`, `agent_limit=3`, `total_rounds=5` (`backend/src/mirofish_backend/diagnostics/arc11_ablation.py:36`) — the confound test is a same-shape rerun of the existing Arc 11 harness on the Anthropic tier, not a `ciepss_school_b` run. It needs no fixture. **Run Part B in parallel with Part A**, not queued behind it — Part A's pre-flight checklist (§1.1) may surface something that changes scope (e.g., corpus content that fails the source-text check), and there's no reason to let that block a $10, few-hour test that answers an independent question.

**ARC12 §1 Part B doesn't name a scenario explicitly** ("same scenario and same network CSV in both conditions"). Use `fsbb_comparator` at the existing `agent_limit=3, rounds=5` profile — that's the only way this test is commensurable with the Arc 11 numbers it's meant to explain.

### What's already built

- `scripts/run_arc11_ablation.py` already supports `--llm-provider anthropic`, `--conditions` (subset selection), `--seeds`, `--interview-profile-id anthropic_default --judge-profile-id anthropic_default`. No new CLI surface needed.
- `build_network_csv_for_scenario(scenario_id, agent_limit)` (`arc11_ablation.py:81`) builds the network deterministically from `get_scenario(scenario_id).personas[:agent_limit]` in fixed order — no randomness, no seed-dependence. **Both conditions in a single script invocation already get an identical network CSV for free**, satisfying "same network CSV in both conditions" with no code change. This network is a synthetic chain, not a documented CIEPSS network — acceptable for Part B (only needs internal consistency between its two arms), but flagging again for whoever scopes `iter-55` in detail: there is currently no code path that loads a real documented network CSV instead of synthesizing one. Out of scope here.

### Design (exactly this — do not expand)

- Two conditions only: `baseline` and `+importance+retrieval+reflection`.
- Three seeds each (42, 43, 44) — six runs total.
- Anthropic tier for the simulation itself, not just the interview/judge.
- Same scenario (`fsbb_comparator`, `agent_limit=3`, `rounds=5`) and same network CSV in both conditions (already guaranteed).
- Report: architectural interview by category (all five, including the three at ceiling — report the ceiling explicitly, don't drop saturated categories from the table), MemBench, between-agent dispersion, input tokens, cost, wall-clock.

**Reference invocation** (confirm exact flag names against current `--help` before running):

```bash
cd backend && uv run python3 ../scripts/run_arc11_ablation.py \
  --conditions baseline "+importance+retrieval+reflection" \
  --seeds 42 43 44 \
  --llm-provider anthropic \
  --interview-profile-id anthropic_default \
  --judge-profile-id anthropic_default \
  --json-out ../docs/diagnostics/arc12_confound_results.json \
  --markdown-out ../docs/diagnostics/arc12_confound_results.md
```

Estimated cost ~US$10 (GM-F's figure) — report actual metered cost against this estimate; flag if materially over.

**QA bar, matching Arc 11's own** (per `senna-iter-53-closeout.md`): confirm zero `[LLM error]` transcript entries and zero context-length failures across all six runs before treating results as valid. If any run needs a redo, redo it from a fresh simulation (not a salvage) — same standard GM-F praised in the Arc 11 ruling.

### Interpretation (fixed in advance, per GM-F)

- `memory_retrieval` recovers toward 2.00 in the full-stack arm ⇒ the Arc 11 decline was the 8B local model degrading under longer prompts; mechanisms are not implicated.
- The decline persists on the Anthropic tier ⇒ it is a mechanism effect; mechanisms stay off.

### DoD

Six runs complete cleanly. Results committed (`docs/diagnostics/arc12_confound_results.{json,md}`) alongside a short report — interview-by-category (all five), MemBench, dispersion, tokens, cost, wall-clock — plus the interpretation call per the fixed rule above. **No reading, citing, or scoring of substantive transcript content** — mechanics only, per the Arc 12 standing constraint.

---

## 3. Part C — The individuation report

**Deliverable, decided:** `docs/diagnostics/ARC12_INDIVIDUATION_FINDING.md`, committed alongside Part B's results (same commit is fine — they share source data).

Contents:

1. State the Arc 11 dispersion result plainly: baseline cross-agent interview-score stdev ≈ 0.00; `+importance+retrieval` ≈ 0.31; `+importance+retrieval+reflection` ≈ 0.27 (per `senna-iter-53-closeout.md` dispersion table).
2. Report the **same dispersion metric from Part B's six runs**, on the Anthropic tier, explicitly and separately from Part B's mechanism-vs-model interpretation call — two different questions answered by the same six runs.
3. Frame the result against the study's own propositions: P1 (authority), P3 (self-concept), P4 (adaptation scale) all require agents to diverge from each other; a platform that produces near-identical actors cannot test them regardless of scoring quality. This is a **study-validity argument**, not a quality-of-mechanism argument — say so explicitly, because it changes who rules on it (GM-F rules on defaults with this as evidence; Ops does not conclude it).
4. Does not pre-empt GM-F's ruling on mechanism defaults — presents the evidence, states the implication, stops there.

### DoD

Report exists, is evidence-only, and is legible to someone who hasn't read the Arc 11 closeout.

---

## 4. `senna-iter-54` combined DoD (per ARC12 §1)

- Fixture loads (Part A, §1.7) — from a clean checkout, with a documented setup step, test asserts resolution.
- Six runs complete (Part B).
- A written recommendation on mechanism defaults, with quality, cost, and dispersion evidence (Parts B + C together).
- **GM-F ruling required before `iter-55` begins** — the `iter-54 → iter-55` gate from ARC12 §8, unchanged here.

**Commit boundaries** (per [[feedback_architect_incremental_commits]] — commit per part, never batch to the end of the iteration):

1. Commit 1: Part A — schema change, `upsert_user_scenario` extension, seeding script, `dummy_external_scenario` fixture + tests, `.gitignore` update, `docs/SETUP_STUDY_FIXTURES.md`. (Provenance manifest and the manual smoke-test evidence land here too, once §1.1–§1.5 are actually run against the real study repo.)
2. Commit 2: Part B — the six-run results files.
3. Commit 3: Part C — the individuation report.
4. Commit 4 (or folded into 3): `iter-54` closeout doc.

---

## 5. Explicitly out of scope for this handoff

- `senna-iter-55` (study-scale rehearsal) — not started, not scoped further here. Two heads-up items carried forward for whoever expands it: (a) the "CIEPSS documented network" language in ARC12 §2 has no implementation path today — the only network-builder in the codebase synthesizes a chain topology; (b) confirm whether `ciepss_school_b`'s persona count and roles actually match "8 actors (RQ1)" as ARC12 assumes, once §1.1's pre-flight read happens.
- Any study run. Nothing in `iter-54` reads, cites, or scores substantive outputs.
- Re-running the Arc 11 sweep, or any change to the Arc 11 mechanism defaults ahead of GM-F's ruling on this iteration's evidence.
- CLAUDE.md's Arc Status table has no rows for Arc 9 or Arc 10 (jumps 8 → 11) — pre-existing gap, not touched by this handoff, flagged separately to Mark.

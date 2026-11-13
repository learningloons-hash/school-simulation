# M-RENAME: Remove Senna naming

**Repo:** [learningloons-hash/school-simulation](https://github.com/learningloons-hash/school-simulation) (public)  
**Milestone:** M-RENAME (research/platform track — not a numbered UX Arc)  
**Branch:** `m-rename-mirofish`  
**Base:** `main` **after** [PR #16](https://github.com/learningloons-hash/school-simulation/pull/16) (`m3-sonnet55-pin`) **has been merged**. Do not branch from pre-#16 `main`. Do not stack this work on `m3-sonnet55-pin` if #16 is still open.  
**PR:** one branch, one PR, for Mark to merge. Builder does not merge or deploy.  
**Inventory date:** 2026-11-13 (Asia/Singapore). Counts below are from an exhaustive local `git grep -i -I mirofish` (GitHub code search indexes only the default branch and can miss files).

---

## 1. Goal

Remove all `mirofish` / `Senna` / `MIROFISH` names from the **build**: package names, module paths, identifiers, config keys, env-var prefixes that actually exist, docker/service names, scripts, UI/API product strings, frontend package identity, and **active** docs titles.

Keep Senna only as an **attribution** in a new root `README.md` and a new root `NOTICE` file. The suggested “no Senna source code is included” clause is **unverified** and **requires Mark / legal confirmation** before it is treated as a fact.

This rename does **not** settle whether Senna is a derivative work of Senna, and it does **not** change `LICENSE`.

---

## 2. Preconditions

1. [PR #16](https://github.com/learningloons-hash/school-simulation/pull/16) is merged into `main`.
2. Builder starts from that updated `main` (`git fetch` and confirm the #16 commit is on `origin/main`). Head of #16 at inventory time: `94521ee`. Pre-#16 `main` was `bb00410`.
3. No other open feature branch is assumed. If local or remote work exists on `m-rename-mirofish`, stop and report; do not force-push or reset `--hard`.

---

## 3. Workflow conventions (fold into the existing arc cycle)

There is **no** root `AGENTS.md` and **no** root `README.md` today. Canonical workflow lives in:

| File | Use |
|------|-----|
| `CLAUDE.md` | Arc status table, review protocol, ports, design system. Update the project-context line that still says the codebase is `school-simulation/`. Add an M-RENAME row or a short “Research milestones” note; do **not** invent a new Arc number. |
| `docs/handoffs/SENNA_AGENT_CYCLE.md` | GM / Architect / Builder loop, closeouts, `SESSION_STATE`. Update stale `school-simulation/` and old remote URL `learningloons-hash/school-simulation`. |
| `docs/handoffs/HANDOFF_TO_BUILDER.md` | Active builder starters (still say “Senna (formerly Senna) in `school-simulation`”). Update those templates. |
| `docs/SESSION_STATE.md` | Cross-session truth. Update Current Status after the work ships. |
| `docs/iterations/senna-iter-N-closeout.md` | Pattern for closeouts. Write `docs/iterations/senna-m-rename-closeout.md`. |
| `.gitignore` **docs/research/ allowlist** | `docs/research/` is ignored except explicit `!docs/research/…` exceptions. After #16 the allowlist is: `SSTRF_RATER_CALIBRATION_SET.md`, `PREREG_SSTRF_RQ1_V2.md`, `SSTRF_RQ1_SCORING_SYSTEM_V2.md`, `M3_SONNET55_PIN.md`, plus two scoring result files under `docs/research/runs/…`. If you add a research doc, add a `!` exception. **Prefer** putting this milestone’s handoff at `docs/handoffs/HANDOFF_SENNA_M_RENAME.md` (handoffs are tracked, except `HANDOFF_SSTRF_*`). |

This milestone is a **single builder pass + architect review + one PR**, like other research milestones (M3), not a five-iteration Arc.

**Tests:** `cd backend && uv run pytest` (or `PYTHONPATH=src pytest tests/` if not using `uv`).  
**Frontend:** `cd frontend && npm run build`. Typecheck with `cd frontend && npx tsc --noEmit` (there is no `typecheck` script in `package.json`; do not have to add one).  
**Install:** `cd backend && uv sync --python 3.12` (Python 3.11 or 3.12; `.python-version` pins 3.12). This is **not** a `pip install -e` repo, though `uv` uses the package in `backend/`.

---

## 4. Inventory (authoritative counts)

GitHub `search_code` for `repo:learningloons-hash/school-simulation mirofish` reported ~213 files on default-branch index and does **not** include PR #16. **Do not trust it.** Builder must re-grep the post-#16 tree exhaustively (case-insensitive) at the start and end of the work.

### 4.1 Content matches

| Ref | Files with a content hit | Matching lines |
|-----|--------------------------|----------------|
| `main` @ `bb00410` | **214** | **1,004** |
| `m3-sonnet55-pin` @ `94521ee` (post-#16 expected `main`) | **216** | **1,020** |

PR #16 adds content hits in exactly two new files (import lines only):

- `backend/src/senna_backend/llm/anthropic_request.py`
- `backend/src/senna_backend/llm/llm_request_log.py`

`docs/research/M3_SONNET55_PIN.md` (allowlisted in #16’s `.gitignore`) has **no** `mirofish` string. `.env.example` on #16 still documents `uv run senna-backend` and `SQLITE_PATH=./data/mirofish.sqlite`.

### 4.2 Path matches (package directory)

| Ref | Files under `backend/src/senna_backend/` |
|-----|-----------------------------------------------|
| `main` @ `bb00410` | **86** |
| after #16 | **88** (the two new LLM modules above) |

**38** of those files have **no** `mirofish` in file content (empty/`__init__` modules, parsers, scenario YAML/corpus, etc.). They still move with `git mv`. There is **no** `school-simulation/` folder on `main`.

### 4.3 Hits by bucket (on `main` @ `bb00410`; +2 package files / +16 lines after #16)

| Bucket | Files | Lines | Action |
|--------|------:|------:|--------|
| Package source (`backend/src/senna_backend/`) | 48 | 191 | `git mv` + rewrite imports, loggers, product strings |
| Tests (`backend/tests/`) | 64 | 392 | Import / patch-string rewrites only |
| Backend meta (`pyproject.toml`, `.env.example`, `uv.lock`) | 3 | 6 | Rename dist/script; regenerate lock |
| Backend scripts | 1 | 3 | Import rewrite (`lmstudio_profile_smoke.py`) |
| Root scripts (`scripts/`) | 16 | 83 | Imports, paths, one env var |
| `.gitignore` | 1 | 3 | Update package-path exceptions |
| `CLAUDE.md` | 1 | 1 | Update project-context line |
| Active docs (`NEW_LAPTOP_PLATFORM_SETUP.md`, `SESSION_STATE.md`, `SETUP_STUDY_FIXTURES.md`, `USER_GUIDE_FRONTEND.md`, `domain-packs.md`) | 5 | 16 | Must update |
| Handoffs | 17 | 145 | Update **active templates**; mechanical identifier replace in dated arc handoffs |
| Iteration closeouts | 37 | 104 | Mechanical identifier replace |
| Reviews | 8 | 41 | Mechanical identifier replace |
| Plans | 2 | 2 | Mechanical identifier replace |
| ADR-001 | 1 | 3 | Mechanical identifier replace |
| `references/ARCHITECTURE.md` | 1 | 2 | Must update (active title is still “Senna”) |
| Diagnostics | 8 | 8 | Mixed — see §6 allowlist |
| `docs/research/PREREG_SSTRF_RQ1_V2.md` | 1 | 4 | **Allowlist — do not edit** (published study text) |
| Frontend | **0** | 0 | Already `senna-frontend`; `<title>Senna</title>`; no `localStorage` / `sessionStorage` keys |
| Docker / Compose / `.github` CI | **0** | 0 | None in the tree |

Tests **without** a `mirofish` string (still run them; no import rewrite needed unless they break after the package move): `test_membench_adapter.py`, `test_senna_iter58_freeze.py`, `test_sstrf_rq1_scoring.py`.

---

## 5. Name map (decisions)

| Kind | Old | New |
|------|-----|-----|
| Import package / source dir | `senna_backend` / `backend/src/senna_backend/` | `senna_backend` / `backend/src/senna_backend/` |
| Distribution name (`pyproject` / `uv.lock`) | `senna-backend` | `senna-backend` |
| Console script | `senna-backend` | `senna-backend` (keep old name as a **deprecated alias**, §5.1) |
| Uvicorn target | `senna_backend.main:app` | `senna_backend.main:app` |
| FastAPI title | `Senna` | `Senna` |
| `GET /health` `service` | `senna-backend` | `senna-backend` |
| Logger names | `logging.getLogger("senna_backend…")` (12 call sites on `main`) | `senna_backend…` |
| Default SQLite file | `./data/mirofish.sqlite` | **Do not orphan Roach data** — §5.2 |
| Export zip filename | `mirofish_run_{simulation_id}.zip` | `senna_run_{simulation_id}.zip` for **new** exports only (§5.3) |
| Script env var | `MIROFISH_BACKEND_URL` (only in `scripts/agent_ask_demo.py`) | `SENNA_BACKEND_URL`, with fallback (§5.4) |
| Frontend package / UI title | already `senna-frontend` / `Senna` | no change |
| localStorage keys | none found | no migration |
| Historical folder/repo nickname in docs | `school-simulation` | “this repo” / `school-simulation` in **active** docs |
| `LICENSE` | Apache-2.0, “Copyright 2026 Ministry of Education, Singapore” | **Do not touch** |

Prompt / docstring product strings that still say “Senna” (e.g. planner system prompt in `agent/orchestrator.py`, scenario-author prompt in `api/scenarios_generate.py`, “Senna simulation engine” in `simulation/interaction_policy.py`) become “Senna”.

### 5.1 Deprecated CLI alias (required)

Keep `senna-backend` as a second `[project.scripts]` entry pointing at the same `senna_backend.main:run_dev` (or a thin wrapper that logs a **one-line DeprecationWarning** then calls `run_dev`). This keeps existing Roach/Mac muscle memory (`uv run senna-backend`) working. Document `uv run senna-backend` as the supported command in `.env.example` and `docs/NEW_LAPTOP_PLATFORM_SETUP.md`.

The string `senna-backend` may therefore remain in `pyproject.toml` (and `uv.lock` if the alias is locked) as **back-compat fallback code**, which acceptance allows.

### 5.2 SQLite default path — do not orphan data (required)

`Settings.sqlite_path` currently defaults to `./data/mirofish.sqlite`, overridable by unprefixed `SQLITE_PATH` (see §5.4). Existing DBs on Roach and the Mac live at that path.

**Rule:**

- If `SQLITE_PATH` (or an explicit settings override) is set, use it unchanged.
- Else if `./data/mirofish.sqlite` exists and `./data/senna.sqlite` does not, **keep using** `./data/mirofish.sqlite` and log a single INFO that the legacy filename was detected (do not move, copy, or delete the file).
- Else default to `./data/senna.sqlite` (new installs).

The literal `mirofish.sqlite` may remain in this fallback (and in a short comment in `.env.example`). Update `scripts/sstrf_scoring_evidence.py` the same way: prefer an explicit env/path, then existing legacy file, then the new default. Do **not** edit the historical mention in `docs/diagnostics/ARC12_CONVERGENCE_CALIBRATION.md` (allowlisted).

### 5.3 Export zip name

`api/simulations.py` builds `filename = f"mirofish_run_{simulation_id}.zip"`. No other in-repo reader of that pattern was found. New exports use `senna_run_{simulation_id}.zip`. Do not rename files already on disk. If any download/content-disposition helper assumes the old prefix, accept both.

### 5.4 Environment variables — do **not** add `env_prefix="SENNA_"`

`Settings` has **no** `env_prefix`. Roach’s `.env` already uses **unprefixed** names that match field names: `SQLITE_PATH`, `HOST`, `PORT`, `LLM_PROVIDER`, `ANTHROPIC_API_KEY`, `ANTHROPIC_MODEL`, `LMSTUDIO_*`, `OPENAI_*`, `OPENROUTER_*`, `LLM_TEMPERATURE`, `LLM_MAX_TOKENS`, plus `SENNA_RELOAD` (already Senna-branded). Adding `env_prefix="SENNA_"` would **break** existing `.env` files and is **forbidden**.

The only `MIROFISH_*` env var in the tree is `MIROFISH_BACKEND_URL` in `scripts/agent_ask_demo.py`. Change that script to read `SENNA_BACKEND_URL`, then fall back to `MIROFISH_BACKEND_URL`, then `http://127.0.0.1:8100`. If the legacy var is used, print a deprecation warning.

---

## 6. What may still contain “mirofish” after the PR

Case-insensitive grep must return **only**:

1. **`README.md` attribution** (new).
2. **`NOTICE`** (new).
3. **Back-compat fallback code**, each with a short comment that it is legacy:
   - deprecated console-script alias `senna-backend`;
   - SQLite default fallback for `./data/mirofish.sqlite`;
   - `MIROFISH_BACKEND_URL` fallback in `agent_ask_demo.py`;
   - any reader that still accepts `mirofish_run_*.zip`.
4. **Explicitly allowlisted historical / study artifacts** (do **not** edit these):
   - `docs/research/PREREG_SSTRF_RQ1_V2.md` (signed/published pre-reg text; 4 path mentions);
   - `docs/diagnostics/ARC12_PLATFORM_FREEZE.json`;
   - `docs/diagnostics/*_provenance.json` (five files; recorded `yaml_rel_path` values);
   - `docs/diagnostics/ARC12_CONVERGENCE_CALIBRATION.md` (records extraction from `backend/data/mirofish.sqlite`).
5. Optionally, a one-line pointer in an active doc (“see `NOTICE`”) is fine, but do not repeat a full Senna write-up outside README/NOTICE.

**Historical markdown** (iteration closeouts, reviews, dated `HANDOFF_SENNA_ARC*.md`, ADRs, plans): do a **mechanical identifier replace** (`senna_backend` → `senna_backend`, `school-simulation` → the current repo / “this repository”, command examples, etc.). Do not invent new historical claims. This is preferred so the leftover grep set stays small. If a passage is a verbatim recorded quote that would be misleading to alter, leave it and list the file in the PR as an extra allowlist entry.

**Do not alter** historical run outputs, transcripts, `backend/data/**`, on-disk SQLite files, export zips, or study artifacts in `data/` (gitignored runtime). Old outputs keep old names.

---

## 7. README + NOTICE (new)

There is no root README today. Add both files.

**Draft attribution** (same substance in both places; README can be a short project intro plus this paragraph):

> Senna was originally inspired by [Senna](https://github.com/666ghj/Senna) (AGPL-3.0).  
> **[REQUIRES MARK / LEGAL CONFIRMATION before treating as a fact:]** No Senna source code is included.

Builder must leave the confirmation flag visible in the PR description and in `NOTICE` (e.g. a comment line or a clearly marked sentence) until Mark confirms. Do not present the clause as already verified.

Do **not** copy Senna’s license text into `LICENSE`. Do **not** relicense. Credit only, and only if the wording Mark confirms is accurate.

---

## 8. Implementation steps

1. Confirm #16 is on `origin/main`. Branch `m-rename-mirofish` from that tip.
2. Re-run exhaustive greps; record file and line counts in the closeout (starting baseline).
3. `git mv backend/src/senna_backend backend/src/senna_backend`. Preserve history. Do not copy-delete.
4. Update `backend/pyproject.toml`: package name, scripts (new + deprecated alias), `package-data`.
5. Rewrite imports and string references across package, tests, and scripts. **Test-file import rewrites and `monkeypatch.setattr("senna_backend…")` / patch-target string updates are allowed and expected.** Do **not** change test assertions or test logic except where a product string is itself the assertion (health `service`, FastAPI title, export filename for **new** zips).
6. Apply product-string changes (`FastAPI` title, `/health`, loggers, prompts).
7. Implement SQLite and env-var fallbacks (§5.2, §5.4) and the export-zip rename (§5.3).
8. `cd backend && uv lock` (and `uv sync`) so `uv.lock` matches `senna-backend`.
9. Update `.gitignore` package-path exceptions to `backend/src/senna_backend/…` (keep the `ciepss_school_b.yaml` ignore rule). Keep the #16 `!docs/research/M3_SONNET55_PIN.md` exception.
10. Update active docs, `CLAUDE.md`, handoff templates, `SESSION_STATE.md`, architecture/user-guide titles, and mechanically replace identifiers in historical markdown (§6).
11. Add `README.md`, `NOTICE`, `docs/handoffs/HANDOFF_SENNA_M_RENAME.md` (can be a short pointer to this milestone), and `docs/iterations/senna-m-rename-closeout.md`.
12. Run acceptance (§9). Open a PR. Do not merge.

---

## 9. Acceptance

- Case-insensitive grep for `mirofish` (tracked files, excluding nothing the builder can edit) returns **only** the classes in §6. Report the leftover list in the closeout and PR.
- `cd backend && uv run pytest`: totals **equal the post-#16 `main` baseline**. Expected pre-#16 / #16 reported baseline: **527 passed, 15 failed, 2 skipped**. The same 15 tests must fail; no new failures; no tests flipped from fail to pass by accident unless the only change is an import path and you can show the failure is identical. The **15 failure nodeids were not recorded in-repo**; builder must first run pytest on post-#16 `main` (or the merge tip), **list the 15 failing nodeids**, then compare. The 2 skipped tests are likely the `@pytest.mark.manual` cases in `test_iteration17.py` and `test_senna_arc8_integration.py` — confirm. Report exact passed / failed / skipped counts and the failure list.
- `cd frontend && npm run build` passes.
- `cd frontend && npx tsc --noEmit` passes.
- Backend still defaults to port **8100**; frontend to **3100** (`docs/NEW_LAPTOP_PLATFORM_SETUP.md`, Vite `VITE_PORT` / `VITE_BACKEND_PORT`). A local start check (`uv run senna-backend` or `uv run uvicorn senna_backend.main:app --host 0.0.0.0 --port 8100`, and `npm run dev` / `npm run build`) is required; `GET /health` returns `{"status":"healthy","service":"senna-backend"}`.
- Package dir `backend/src/senna_backend/` is gone; `backend/src/senna_backend/` is in its place via `git mv`.
- `LICENSE` is byte-for-byte unchanged.
- No secrets, no runtime data, no transcripts, no SQLite files in the commit.
- History of the moved package is preserved (`git log --follow` on a moved file still works).

---

## 10. Don’ts

- Do not merge or deploy.
- Do not edit `LICENSE`.
- Do not change test logic beyond import / patch-path / asserted product-string updates. Import rewrites in tests **are** allowed.
- Do not add `Settings` `env_prefix="SENNA_"` or rename `SQLITE_PATH` / `ANTHROPIC_API_KEY` / other unprefixed settings env vars.
- Do not delete, move, or rewrite historical run outputs, transcripts, data dirs, or on-disk databases.
- Do not rewrite allowlisted freeze / provenance JSON or the signed pre-reg (§6).
- Do not put secrets in the repo or in the PR.
- Do not force-push, `git reset --hard`, `git clean`, or delete a checkout.
- Do not launch live paid LLM calls as part of this milestone.
- Do not treat the “no Senna source code is included” sentence as confirmed.

---

## 11. Mark’s local migration (Roach and this Mac)

Do this **after Mark merges the M-RENAME PR**, on **each** checkout (Roach and the Mac). Fast-forward only. Check for uncommitted or unpushed work first. Never `reset --hard` or force-pull.

```bash
# 1) In the school-simulation checkout — stop if this prints anything unexpected
git status
git status -sb
git log --oneline @{u}..HEAD 2>/dev/null || true   # unpushed commits, if upstream is set

# 2) Fast-forward to the merged main only (refuses to merge if you have diverged)
git fetch origin
git checkout main
git pull --ff-only origin main

# 3) Reinstall the renamed package (this repo uses uv, not pip install -e)
cd backend
uv sync --python 3.12

# 4) .env: you should NOT need to rename variables.
#    SQLITE_PATH, ANTHROPIC_API_KEY, LLM_PROVIDER, etc. stay as they are.
#    If SQLITE_PATH is unset, the backend will keep using ./data/mirofish.sqlite
#    when that file already exists. Do not delete or rename that file.
#    Optional: add a comment in .env, or set SQLITE_PATH explicitly.
#    The old command still works (deprecated):  uv run senna-backend
#    Preferred:                                 uv run senna-backend
#    or:  uv run uvicorn senna_backend.main:app --host 0.0.0.0 --port 8100

# 5) Frontend (name already senna-frontend; still port 3100)
cd ../frontend
npm install
npm run build   # or: npm run dev

# 6) If you have personal aliases, systemd units, or shell scripts that call
#    `uv run senna-backend` or `uvicorn senna_backend.main:app`, update
#    them when convenient. The deprecated CLI alias keeps the old command working
#    until you do.
```

If `git pull --ff-only` refuses, stop and keep the local work. Do not rebase or reset without Mark’s OK.

---

## 12. Open confirmation (does not block the build)

- Mark / legal must confirm the NOTICE sentence that “No Senna source code is included.” Until then, ship the draft with the confirmation flag visible.
- Employer / copyright review of `LICENSE` remains a separate blocker and is out of scope for this PR.


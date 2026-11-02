# New laptop: Senna platform setup (for LLM agents)

Instructions for an assistant helping install **Senna** on a fresh machine. For **new data / new projects**, separate from legacy study runs in `senna-sstrf-study`.

**Repo:** [school-simulation](https://github.com/learningloons-hash/school-simulation)

---

## Quick start

### Windows (PowerShell)

```powershell
git clone https://github.com/learningloons-hash/school-simulation.git
cd school-simulation\backend
copy .env.example .env
# Edit .env: ANTHROPIC_API_KEY, LLM_PROVIDER=anthropic, SQLITE_PATH=./data/my_project.sqlite
uv python install 3.12
uv sync --python 3.12
cd ..\frontend
npm install
```

Two terminals (from `backend/` after editing `.env`):

```powershell
# Terminal 1 — no reload (reload kills runs)
uv run uvicorn mirofish_backend.main:app --host 0.0.0.0 --port 8100

# Terminal 2
cd ..\frontend
npm run dev
```

Open **http://127.0.0.1:3100**. Smoke test: **psle_reform_mvp**, 2 rounds, 2 agents → status **completed** and transcript has **no** `[LLM error]` lines.

### macOS / Linux

Same flow with `cp` instead of `copy`, `export VAR=value` instead of `$env:VAR`.

Optional one-shot scripts: see `scripts/windows/` when present (`setup.ps1`, `start.ps1`).

---

## Hard rules

- **Never** read, print, or commit `.env` or API keys.
- **Python 3.11 or 3.12** only (`backend/.python-version` pins **3.12** for `uv`).
- **`backend/.env`** is loaded automatically when the file exists; shell exports override it.
- Use a **dedicated** `SQLITE_PATH` per project (e.g. `./data/new_project.sqlite`).

---

## Anthropic defaults (2026)

- Retired model **`claude-3-5-haiku-20241022`** → use **`claude-haiku-4-5-20251001`** (or newer Haiku id from Anthropic docs).
- Senna **does not send `temperature`** to Anthropic (current models reject it). Claude runs use the provider default → **not word-for-word reproducible** even with a fixed seed. Exports record `llm_temperature: null` and `anthropic_temperature_omitted: true` for pure Anthropic runs.
- `LLM_TEMPERATURE` still applies to LM Studio, OpenAI, and OpenRouter.

Set in `.env`:

```bash
LLM_PROVIDER=anthropic
ANTHROPIC_API_KEY=<your key>
ANTHROPIC_MODEL=claude-haiku-4-5-20251001
```

If `LLM_PROVIDER` is omitted and only `ANTHROPIC_API_KEY` is set, the backend infers **`anthropic`**.

---

## Dev server: do not use reload for real runs

`mirofish-backend` (uvicorn) uses **`reload=False`** by default. Opt-in only: `SENNA_RELOAD=1` (watches `src/`, excludes `.venv` and `data/`).

**Symptom:** run stuck at “Round 0 of 2”, status `running` forever → worker restarted mid-run. Orphan runs are marked **failed** on next startup with `failure_reason=server restarted during run`.

Prefer:

```bash
cd backend && uv run uvicorn mirofish_backend.main:app --host 0.0.0.0 --port 8100
```

---

## Manual steps (agents / troubleshooting)

### Clone

```bash
git clone https://github.com/learningloons-hash/school-simulation.git
cd school-simulation && git log -1 --oneline
```

### Backend

```bash
cd backend
uv python install 3.12
uv sync --python 3.12
cp .env.example .env   # Windows: copy .env.example .env
```

### Frontend

```bash
cd frontend && npm install && npm run dev
```

Ports: backend **8100**, frontend **3100** (Vite proxies API including **`/experiments`**).

### Smoke test pass criteria

- Status **completed** (not **failed** with `failure_reason`).
- Transcript lines are real dialogue, **not** `[LLM error] …`.

### Isolate from old work

New `SQLITE_PATH`, new `scenario_id`, new study folder if using `senna-sstrf-study`.

---

## Troubleshooting

| Symptom | Likely fix |
|--------|------------|
| Stuck at Round 0 / `running` forever | Backend reload restarted worker; use no-reload uvicorn; restart backend to fail orphans |
| 404 on Anthropic | Retired model id in `.env` — update `ANTHROPIC_MODEL` |
| 400 temperature deprecated | Update platform (Anthropic path omits temperature) |
| UI **completed** but empty/broken transcript | All turns `[LLM error]` — read `failure_reason` or transcript; fix API key/model |
| LM Studio failures | Start Local Server; match `LMSTUDIO_MODEL` to loaded model |
| Wrong Python | `cd backend && uv sync --python 3.12` |
| Windows `export` / `cp` fails | Use PowerShell `$env:NAME="value"` and `copy` (see Quick start) |

---

## Out of scope unless asked

- Private `senna-sstrf-study` clone
- CIEPSS validity pipelines
- Production / Tailscale deployment

---

## One-line summary

Clone → `uv sync` + `npm install` → configure **`backend/.env`** (`LLM_PROVIDER=anthropic` + key) → start backend **without reload** + frontend → smoke run with no `[LLM error]` lines.

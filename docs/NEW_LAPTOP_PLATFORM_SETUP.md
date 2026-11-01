# New laptop: Senna platform setup (for LLM agents)

Instructions for an assistant (e.g. Claude) helping install **Senna** from this repo on a fresh machine. Intended for **new data / new projects**, separate from legacy study runs in `senna-sstrf-study`.

**Product:** Senna · **Repo:** [school-simulation](https://github.com/learningloons-hash/school-simulation) (clone folder is often `mirofish-mvp` or `school-simulation`).

---

## Agent role

Install and run the simulation platform from the **public** GitHub repo. Do **not** assume access to the private repo `senna-sstrf-study` unless the user clones it and has GitHub access.

---

## Hard rules

- **Never** read, print, or commit `.env` files or API keys.
- **Never** hardcode tokens in source.
- Use **Python 3.11 or 3.12 only** (`requires-python = >=3.11,<3.13` in `backend/pyproject.toml`). Do not use Python 3.13+ for the backend venv.
- Backend settings come from **environment variables** (`backend/src/mirofish_backend/config.py` does not auto-load `.env`). After copying `backend/.env.example`, **export** variables in the shell (or use direnv / similar) before starting the backend.
- Use a **dedicated SQLite file** for the new project: `SQLITE_PATH=./data/<new_project_name>.sqlite` (create `backend/data/` if needed).

---

## Prerequisites

| Tool | Purpose |
|------|--------|
| Git + GitHub auth | Clone (HTTPS + credential helper, or SSH) |
| [uv](https://docs.astral.sh/uv/) | Python deps; run backend |
| Node.js (LTS) | Frontend (`frontend/`) |
| LM Studio (optional) | Local LLM at `http://127.0.0.1:1234/v1` when `LLM_PROVIDER=lmstudio` |
| Cloud API keys (optional) | Anthropic / OpenAI / OpenRouter profiles |

Ask the user: **macOS or Windows**, and **local LM Studio vs cloud API** for runs.

---

## Step 1 — Clone platform

```bash
git clone https://github.com/learningloons-hash/school-simulation.git
cd school-simulation
git checkout main
git log -1 --oneline
```

Record the commit hash for reproducibility. Pin to a specific commit if the user needs a frozen baseline.

Skip `senna-sstrf-study` unless they need versioned study exports and manifests.

---

## Step 2 — Backend

```bash
cd backend
uv sync
uv run python -c "import sys; assert sys.version_info[:2] in ((3,11),(3,12)), sys.version"
```

Copy the env template locally (user fills secrets; do not paste keys into chat):

```bash
cp .env.example .env
```

See `backend/.env.example` for all keys. Minimum for a **local** smoke test (set `LMSTUDIO_MODEL` to the exact id shown in LM Studio → Local Server):

```bash
export SQLITE_PATH="./data/new_project.sqlite"
export LLM_PROVIDER=lmstudio
export LMSTUDIO_BASE_URL=http://127.0.0.1:1234/v1
export LMSTUDIO_MODEL="<model id from LM Studio>"
export LLM_TEMPERATURE=0.0
export LLM_MAX_TOKENS=1024
```

**Anthropic-only** (no LM Studio):

```bash
export LLM_PROVIDER=anthropic
export ANTHROPIC_API_KEY="<set in shell, not in chat>"
export ANTHROPIC_MODEL=claude-3-5-haiku-20241022
```

Start backend (default **0.0.0.0:8100**):

```bash
cd backend
uv run mirofish-backend
```

Verify:

```bash
curl -s http://127.0.0.1:8100/health
curl -s http://127.0.0.1:8100/capabilities | head
```

Optional:

```bash
cd backend && uv run pytest -q
```

---

## Step 3 — Frontend

```bash
cd frontend
npm install
npm run dev
```

Open **http://127.0.0.1:3100**. Vite proxies API routes to backend port **8100** (see `frontend/vite.config.ts`).

If browser API calls fail, confirm backend is listening on 8100. The **Experiments** tab uses `/experiments`; add a matching proxy in `vite.config.ts` if that tab is required on day one.

---

## Step 4 — Smoke test (“working”)

1. **Run** tab → scenario **`psle_reform_mvp`** (or another from `/capabilities`).
2. Small run: e.g. **2 rounds**, **2 agents**, fixed **random_seed**.
3. Wait for **completed** (or **failed** with `failure_reason`).
4. Check Transcript, Outcomes, and export JSON/ZIP.

For LM Studio: Local Server on, model loaded, id matches `LMSTUDIO_MODEL`.

---

## Step 5 — Isolate from old Senna work

- Dedicated **`SQLITE_PATH`** (do not reuse old `.sqlite` unless importing on purpose).
- New **`scenario_id`** / new scenario YAML or Scenarios UI entries.
- If using a study repo later: new tree only, e.g. `docs/research/runs/<new_project>/`.

---

## Step 6 — Report back to the user

- OS; Python and Node versions  
- Platform git commit  
- `SQLITE_PATH` (path only)  
- LLM mode (lmstudio / anthropic / hybrid)  
- `/health` result and one completed smoke run (simulation id prefix is fine)  
- URLs: backend `:8100`, frontend `:3100`

---

## Troubleshooting

| Symptom | Likely fix |
|--------|------------|
| Backend won’t start | Wrong Python; run `uv sync` from `backend/` |
| LLM errors in transcript | LM Studio off, wrong model id, or missing API key |
| Blank UI | Browser console errors |
| Old DB concerns | Back up `*.sqlite` before migrating; fresh `SQLITE_PATH` for new work |
| Cost / slowness | Fewer agents/rounds; check Run preflight |

---

## Out of scope (unless user asks)

- Restoring bundles from `senna-sstrf-study`
- CIEPSS validity pipelines or pre-registration
- Always-on server / Tailscale deployment

---

## One-line summary

Clone **school-simulation** → `uv` backend + `npm` frontend → export env vars → LLM endpoint → fresh **`SQLITE_PATH`** = runnable platform. Private study repo is optional.

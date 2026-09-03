# Study fixture reunification (senna-iter-54 Part A)

The CIEPSS study scenario (`ciepss_school_b`) lives in the private study repo, not in this platform repo. Use the seeding script to load it into the local SQLite `user_scenarios` table before running study-scale simulations.

## Prerequisites

- Platform repo cloned (`mirofish-mvp`)
- Study repo cloned: `https://github.com/learningloons-hash/senna-sstrf-study.git`
- Backend dependencies installed (`cd backend && uv sync`)

## Pin the fixture commit

Open [`docs/diagnostics/ciepss_school_b_provenance.json`](diagnostics/ciepss_school_b_provenance.json) and check out the study repo at (or after) the recorded `source_commit`:

```bash
cd /path/to/senna-sstrf-study
git fetch origin
git checkout <source_commit from provenance.json>
```

Ensure the working tree is clean before seeding (`git status --porcelain` should be empty).

## Seed into local SQLite

From the platform repo root:

```bash
python3 scripts/seed_scenario_from_study_repo.py \
  --study-repo-path /path/to/senna-sstrf-study \
  --yaml-rel-path backend/src/mirofish_backend/scenarios/data/ciepss_school_b.yaml \
  --scenario-id ciepss_school_b
```

Optional flags:

- `--sqlite-path` — target DB (defaults to `SQLITE_PATH` from backend settings / `.env`)
- `--force` — skip overwrite confirmation when the scenario already exists
- `--allow-dirty` — local iteration only; manifest records `"dirty": true`

The script validates the YAML, upserts `user_scenarios`, and writes/updates `docs/diagnostics/ciepss_school_b_provenance.json` with repo URL, commit hash, and seed timestamp. **Cite that manifest file** (not the DB row) for pre-registration fixture provenance.

`ciepss_school_b` does not use RAG (`rag_enabled` absent) — no corpus copy step is required.

## Verify with a smoke simulation

After seeding, run one short simulation through the normal API or CLI (small round count). Confirm it reaches terminal status without errors. Record simulation id and status only — do not read or score substantive output.

Example (adjust paths and flags to your environment):

```bash
cd backend && uv run python3 -c "
import asyncio
from mirofish_backend.config import get_settings
from mirofish_backend.api.simulations import SimulationRunRequest, queue_simulation_run, wait_for_simulation_terminal

async def main():
    s = get_settings()
    req = SimulationRunRequest(scenario_id='ciepss_school_b', total_rounds=2, agent_limit=3)
    resp = await queue_simulation_run(s, req)
    status = await wait_for_simulation_terminal(s.sqlite_path, simulation_id=resp.id, timeout_seconds=600)
    print(resp.id, status)

asyncio.run(main())
"
```

## Re-seeding after a DB wipe

Repeat the seed command above. The script is idempotent (`upsert`). If the study repo has moved forward, update your checkout to the commit in `ciepss_school_b_provenance.json` (or re-seed from a newer pinned commit and commit an updated manifest).

## CI vs local

Public CI uses `backend/tests/test_senna_iter54_scenario_reunification.py` with synthetic `dummy_external_scenario` fixtures — it does not access the private study repo.

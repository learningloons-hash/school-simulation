# Senna

Senna is a multi-agent simulation platform for structured stakeholder and school-policy scenarios. This repository contains the Senna backend (FastAPI) and frontend (React/Vite).

- Backend: `cd backend && uv sync --python 3.12 && uv run senna-backend` (port **8100**)
- Frontend: `cd frontend && npm install && npm run dev` (port **3100**)
- Health: `GET /health` → `{"status":"healthy","service":"senna-backend"}`

## Attribution

Senna was originally inspired by [MiroFish](https://github.com/666ghj/MiroFish) (AGPL-3.0).

See [`NOTICE`](NOTICE) and [`LICENSE`](LICENSE) for licensing terms on this repository.

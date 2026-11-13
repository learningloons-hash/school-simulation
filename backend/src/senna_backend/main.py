import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from senna_backend.config import get_settings
from senna_backend.db.schema import init_db
from senna_backend.api.agent import router as agent_router
from senna_backend.api.capabilities import router as capabilities_router
from senna_backend.api.scenario_catalog import router as scenario_catalog_router
from senna_backend.api.scenarios_generate import router as scenarios_generate_router
from senna_backend.api.experiments import router as experiments_router
from senna_backend.api.simulations import router as simulations_router

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
)
logger = logging.getLogger("senna_backend")


@asynccontextmanager
async def lifespan(app: FastAPI):
    from senna_backend.db.repo import fail_orphaned_running_simulations

    settings = get_settings()
    logger.info("Initializing database at %s", settings.sqlite_path)
    await init_db(settings.sqlite_path)
    n = await fail_orphaned_running_simulations(
        settings.sqlite_path,
        failure_reason="server restarted during run",
    )
    if n:
        logger.warning("Marked %s simulation(s) failed after server restart", n)
    yield


def create_app() -> FastAPI:
    settings = get_settings()

    app = FastAPI(title="Senna", version="0.1.0", lifespan=lifespan)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(experiments_router)
    app.include_router(simulations_router)
    app.include_router(agent_router)
    app.include_router(scenario_catalog_router)
    app.include_router(scenarios_generate_router)
    app.include_router(capabilities_router)

    @app.get("/health")
    async def health() -> dict:
        return {"status": "healthy", "service": "senna-backend"}

    return app


app = create_app()


def run_dev() -> None:
    """
    Development entrypoint.

    Uses env vars `HOST` and `PORT` to override defaults.
    """
    import os

    import uvicorn

    settings = get_settings()
    host = os.getenv("HOST", settings.host)
    port = int(os.getenv("PORT", str(settings.port)))

    reload = os.getenv("SENNA_RELOAD", "0") == "1"
    uvicorn.run(
        "senna_backend.main:app",
        host=host,
        port=port,
        reload=reload,
        reload_dirs=["src"] if reload else None,
        reload_excludes=[".venv/*", "data/*", "**/.venv/**", "**/data/**"] if reload else None,
    )


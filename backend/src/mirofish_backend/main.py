import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from mirofish_backend.config import get_settings
from mirofish_backend.db.schema import init_db
from mirofish_backend.api.agent import router as agent_router
from mirofish_backend.api.capabilities import router as capabilities_router
from mirofish_backend.api.scenario_catalog import router as scenario_catalog_router
from mirofish_backend.api.scenarios_generate import router as scenarios_generate_router
from mirofish_backend.api.experiments import router as experiments_router
from mirofish_backend.api.simulations import router as simulations_router

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
)
logger = logging.getLogger("mirofish_backend")


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    logger.info("Initializing database at %s", settings.sqlite_path)
    await init_db(settings.sqlite_path)
    yield


def create_app() -> FastAPI:
    settings = get_settings()

    app = FastAPI(title="MiroFish MVP", version="0.1.0", lifespan=lifespan)

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
        return {"status": "healthy", "service": "mirofish-backend"}

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

    uvicorn.run(
        "mirofish_backend.main:app",
        host=host,
        port=port,
        reload=True,
    )


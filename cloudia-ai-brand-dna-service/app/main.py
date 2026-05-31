import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.api.app import register_routes

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("CloudIA Brand DNA Service starting")
    try:
        from app.media import storage
        storage.ensure_bucket()
        logger.info("MinIO bucket ready")
    except Exception as exc:
        logger.warning("MinIO not available at startup: %s", exc)
    yield
    logger.info("CloudIA Brand DNA Service shutting down")


def create_app() -> FastAPI:
    settings = get_settings()

    app = FastAPI(
        title="CloudIA Brand DNA Service",
        version="1.0.0",
        description="Canonical client identity and brand context for all CloudIA agent workforces",
        lifespan=lifespan,
    )

    origins = [o.strip() for o in settings.allowed_origins.split(",")]
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    register_routes(app)
    return app


app = create_app()

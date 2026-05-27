import os
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.config import get_settings
from backend.media.storage import ensure_bucket

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    if not settings.encryption_key:
        raise RuntimeError("ENCRYPTION_KEY is not set — refusing to start without token encryption.")
    ensure_bucket()
    logger.info("CloudIA Content Agent API started")
    yield
    logger.info("CloudIA Content Agent API shutting down")


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title="CloudIA Content Agent API",
        version="1.0.0",
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

    from backend.api.app import register_routes
    register_routes(app)

    return app


app = create_app()

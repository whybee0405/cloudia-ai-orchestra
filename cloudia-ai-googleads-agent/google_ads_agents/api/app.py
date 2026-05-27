"""FastAPI application factory for the CloudIA Google Ads Agent API.

Responsibilities:
- Instantiate the FastAPI app with metadata
- Mount all API routes from api.routes
- Add CORS middleware (permissive in development, locked in production)
- Register the /health endpoint
- Configure logging on startup via a lifespan event handler
"""

import logging
import pathlib
from contextlib import asynccontextmanager
from collections.abc import AsyncGenerator

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.base import BaseHTTPMiddleware

import config
from api.routes import router

_FRONTEND_DIR = pathlib.Path(__file__).parent.parent / "frontend"


# ── Logging ────────────────────────────────────────────────────────────────────

def _configure_logging() -> None:
    """Configure root logger using the LOG_LEVEL from config.

    Called once during application startup. All modules that obtain a logger
    via logging.getLogger(__name__) will inherit this level automatically.
    """
    numeric_level = getattr(logging, config.LOG_LEVEL.upper(), logging.INFO)
    logging.basicConfig(
        level=numeric_level,
        format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S",
    )
    logging.getLogger(__name__).info(
        "Logging configured at level=%s (environment=%s)",
        config.LOG_LEVEL.upper(),
        config.ENVIRONMENT,
    )


# ── Lifespan ───────────────────────────────────────────────────────────────────

@asynccontextmanager
async def _lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Run startup and shutdown logic around the application lifecycle.

    Startup:
        - Configure logging so it is ready before the first request.

    Shutdown:
        - Placeholder for any cleanup (e.g. closing connection pools).
    """
    _configure_logging()
    logger = logging.getLogger(__name__)
    logger.info(
        "CloudIA Google Ads Agent API starting up "
        "(environment=%s, version=%s)",
        config.ENVIRONMENT,
        "1.0.0",
    )
    yield
    logger.info("CloudIA Google Ads Agent API shutting down")


# ── API Key authentication middleware ──────────────────────────────────────────

_STATE_MUTATING_METHODS = {"POST", "PUT", "PATCH", "DELETE"}
_AUTH_EXEMPT_PATHS = {"/health", "/docs", "/redoc", "/openapi.json", "/", "/app"}


class ApiKeyMiddleware(BaseHTTPMiddleware):
    """Require X-API-Key header on all state-mutating routes when API_SECRET_KEY is set.

    GET requests are allowed through unauthenticated to support read-only UIs.
    Static file paths (/app/*) are always exempt.
    """

    async def dispatch(self, request: Request, call_next):
        secret = config.API_SECRET_KEY
        if not secret:
            return await call_next(request)

        path = request.url.path
        method = request.method

        # Exempt static frontend, docs, health, and GET requests
        if (
            path.startswith("/app")
            or path in _AUTH_EXEMPT_PATHS
            or method not in _STATE_MUTATING_METHODS
        ):
            return await call_next(request)

        provided = request.headers.get("X-API-Key", "")
        if provided != secret:
            return JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content={"detail": "Invalid or missing X-API-Key header"},
            )
        return await call_next(request)


# ── CORS origins ───────────────────────────────────────────────────────────────

def _get_cors_origins() -> list[str]:
    """Return allowed CORS origins based on the current environment.

    In development, all origins are permitted so that local frontends (e.g.
    running on arbitrary ports) can reach the API without configuration.

    In production/staging, only explicitly listed origins are allowed.
    Extend this list with actual production domain(s) before going live.

    Returns:
        List of allowed origin strings, or ["*"] for development.
    """
    if config.ENVIRONMENT == "development":
        return ["*"]

    # Production: lock down to known origins.
    return [
        "https://dashboard.cloudia.co.za",
        "https://adsagent.cloudia.co.za",
        "https://app.cloudia.co.za",
    ]


# ── Application factory ────────────────────────────────────────────────────────

def create_app() -> FastAPI:
    """Construct and return the configured FastAPI application.

    This function is the single source of truth for app configuration. It is
    called at module level so that ASGI servers (uvicorn, gunicorn+uvicorn)
    can import the app object directly via ``api.app:app``.

    Returns:
        Configured FastAPI application instance.
    """
    application = FastAPI(
        title="CloudIA Google Ads Agent API",
        version="1.0.0",
        description=(
            "Human-in-the-loop Google Ads management system for CloudIA. "
            "All agent decisions are queued for human approval before execution."
        ),
        lifespan=_lifespan,
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
    )

    # ── CORS ──────────────────────────────────────────────────────────────────
    cors_origins = _get_cors_origins()
    application.add_middleware(
        CORSMiddleware,
        allow_origins=cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ── API key auth ───────────────────────────────────────────────────────────
    application.add_middleware(ApiKeyMiddleware)

    # ── API routes ────────────────────────────────────────────────────────────
    application.include_router(router)

    # ── Frontend static files ─────────────────────────────────────────────────
    if _FRONTEND_DIR.exists():
        application.mount(
            "/app",
            StaticFiles(directory=str(_FRONTEND_DIR), html=True),
            name="frontend",
        )

        @application.get("/", include_in_schema=False)
        def serve_root() -> RedirectResponse:
            return RedirectResponse(url="/app/")

    # ── Health endpoint ───────────────────────────────────────────────────────
    @application.get(
        "/health",
        summary="Health check",
        tags=["System"],
        response_model=dict,
    )
    def health() -> dict[str, str]:
        """Return a simple liveness check response.

        Used by load balancers, container orchestrators, and uptime monitors
        to verify the API process is alive and serving requests.

        Returns:
            Dict with status='ok' and the current environment name.
        """
        return {"status": "ok", "environment": config.ENVIRONMENT}

    return application


# ── Module-level app instance (imported by ASGI server) ───────────────────────

app: FastAPI = create_app()

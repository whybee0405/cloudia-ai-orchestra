"""
FastAPI application factory for the CloudIA Website Agents API.

Authentication: simple ``X-API-Key`` header checked against ``settings.secret_key``.
This is an internal operator tool — not a public SaaS endpoint.

Routers:
  /api/projects   — project & client CRUD + pipeline control
  /api/approvals  — approval gate management
  /api/content    — generated content review & editing
  /api/settings   — platform credentials & system health
  /ws/projects/*  — WebSocket real-time events (no API key required)
"""

from __future__ import annotations

from contextlib import asynccontextmanager

import structlog
from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware

from backend.config import settings

log = structlog.get_logger()


# ---------------------------------------------------------------------------
# Lifespan
# ---------------------------------------------------------------------------


@asynccontextmanager
async def lifespan(app: FastAPI):  # type: ignore[type-arg]
    log.info("cloudia_api_starting", environment=settings.environment)
    yield
    log.info("cloudia_api_stopping")


# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------


app = FastAPI(
    title="CloudIA Website Agents API",
    version="1.0.0",
    lifespan=lifespan,
    # Only expose /docs in development to avoid leaking internal routes
    docs_url="/docs" if settings.environment == "development" else None,
    redoc_url="/redoc" if settings.environment == "development" else None,
    openapi_url="/openapi.json" if settings.environment == "development" else None,
)

# ---------------------------------------------------------------------------
# Middleware
# ---------------------------------------------------------------------------

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Auth dependency
# ---------------------------------------------------------------------------


async def verify_api_key(request: Request) -> None:
    """Validate the ``X-API-Key`` header against the configured secret.

    Raises HTTP 401 if the key is missing or incorrect.
    """
    key = request.headers.get("X-API-Key")
    if not key or key != settings.secret_key:
        log.warning(
            "api_auth_failed",
            path=request.url.path,
            method=request.method,
        )
        raise HTTPException(status_code=401, detail="Invalid API key")


# ---------------------------------------------------------------------------
# Routers
# ---------------------------------------------------------------------------

from backend.api.routes import projects, approvals, content  # noqa: E402
from backend.api.routes import settings as settings_router   # noqa: E402
from backend.api import websocket                            # noqa: E402

app.include_router(
    projects.router,
    prefix="/api/projects",
    tags=["projects"],
    dependencies=[Depends(verify_api_key)],
)
app.include_router(
    approvals.router,
    prefix="/api/approvals",
    tags=["approvals"],
    dependencies=[Depends(verify_api_key)],
)
app.include_router(
    content.router,
    prefix="/api/content",
    tags=["content"],
    dependencies=[Depends(verify_api_key)],
)
app.include_router(
    settings_router.router,
    prefix="/api/settings",
    tags=["settings"],
    dependencies=[Depends(verify_api_key)],
)
# WebSocket router — auth handled differently (no X-API-Key header on WS)
app.include_router(websocket.router)


# ---------------------------------------------------------------------------
# Health check
# ---------------------------------------------------------------------------


@app.get("/health", tags=["system"])
async def health() -> dict:
    """Liveness check — returns 200 if the API process is alive."""
    return {"status": "ok", "environment": settings.environment}

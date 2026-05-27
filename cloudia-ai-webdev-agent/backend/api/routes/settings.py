"""
Settings and system health routes for the CloudIA API.

/api/settings          — system status (DB, Redis, Celery health)
/api/settings/credentials  — platform credential CRUD + live connection test
"""

from __future__ import annotations

from datetime import datetime, UTC

import structlog
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, text
from sqlalchemy.orm import Session

from backend.api.schemas import CredentialCreate, CredentialOut, SystemStatus
from backend.db.models import Client, PlatformCredential
from backend.db.session import get_session

log = structlog.get_logger()

router = APIRouter()


# ---------------------------------------------------------------------------
# Helper — ORM → schema
# ---------------------------------------------------------------------------


def _cred_to_out(cred: PlatformCredential) -> CredentialOut:
    return CredentialOut(
        id=cred.id,
        client_id=cred.client_id,
        platform=cred.platform,
        site_url=cred.site_url,
        shop_name=cred.shop_name,
        is_active=cred.is_active,
        last_verified_at=cred.last_verified_at,
    )


# ---------------------------------------------------------------------------
# System status
# ---------------------------------------------------------------------------


@router.get("/", response_model=SystemStatus)
def system_status(
    db: Session = Depends(get_session),
) -> SystemStatus:
    """Check DB, Redis, and Celery worker health."""
    db_connected = False
    try:
        db.execute(text("SELECT 1"))
        db_connected = True
    except Exception as exc:
        log.error("health_db_failed", error=str(exc))

    redis_connected = False
    try:
        import redis  # noqa: PLC0415

        from backend.config import settings  # noqa: PLC0415

        r = redis.Redis.from_url(settings.redis_url, socket_connect_timeout=2)
        r.ping()
        redis_connected = True
        r.close()
    except Exception as exc:
        log.warning("health_redis_failed", error=str(exc))

    celery_worker_active = False
    try:
        from backend.tasks.pipeline_tasks import run_content_agent  # noqa: PLC0415

        app = run_content_agent.app
        inspector = app.control.inspect(timeout=2)
        active = inspector.active()
        celery_worker_active = bool(active)
    except Exception as exc:
        log.warning("health_celery_failed", error=str(exc))

    return SystemStatus(
        db_connected=db_connected,
        redis_connected=redis_connected,
        celery_worker_active=celery_worker_active,
    )


# ---------------------------------------------------------------------------
# Credentials
# ---------------------------------------------------------------------------


@router.post("/credentials/", response_model=CredentialOut, status_code=201)
def add_credentials(
    data: CredentialCreate,
    db: Session = Depends(get_session),
) -> CredentialOut:
    """Store platform credentials encrypted at rest."""
    client = db.get(Client, data.client_id)
    if client is None:
        raise HTTPException(
            status_code=404,
            detail=f"Client {data.client_id} not found",
        )

    existing = db.scalars(
        select(PlatformCredential).where(
            PlatformCredential.client_id == data.client_id,
            PlatformCredential.platform == data.platform,
            PlatformCredential.site_url == data.site_url,
        )
    ).first()
    if existing:
        raise HTTPException(
            status_code=409,
            detail=(
                f"Credentials for client {data.client_id} / {data.platform} / "
                f"{data.site_url} already exist (id={existing.id}). "
                "Delete the existing record before adding new credentials."
            ),
        )

    cred = PlatformCredential(
        client_id=data.client_id,
        platform=data.platform,
        site_url=data.site_url,
        api_url=data.api_url,
        shop_name=data.shop_name,
        api_version=data.api_version,
        is_active=True,
    )

    if data.access_token:
        cred.access_token = data.access_token
    if data.app_password:
        cred.app_password = data.app_password

    db.add(cred)
    db.commit()
    db.refresh(cred)

    log.info(
        "credentials_added",
        credential_id=cred.id,
        platform=cred.platform,
        client_id=cred.client_id,
    )
    return _cred_to_out(cred)


@router.get("/credentials/", response_model=list[CredentialOut])
def list_credentials(
    db: Session = Depends(get_session),
) -> list[CredentialOut]:
    """Return all stored platform credentials (token values never returned)."""
    creds = db.scalars(
        select(PlatformCredential).order_by(PlatformCredential.created_at.desc())
    ).all()
    return [_cred_to_out(c) for c in creds]


@router.get("/credentials/{cred_id}/test")
def test_connection(
    cred_id: int,
    db: Session = Depends(get_session),
) -> dict:
    """Verify stored credentials by making a live API call."""
    cred = db.get(PlatformCredential, cred_id)
    if cred is None:
        raise HTTPException(
            status_code=404,
            detail=f"Credential {cred_id} not found",
        )

    log.info("credential_test_started", credential_id=cred_id, platform=cred.platform)

    if cred.platform == "wordpress":
        if not cred.app_password:
            raise HTTPException(
                status_code=400,
                detail="WordPress credentials are missing an application password",
            )
        try:
            from backend.platforms.wordpress.client import WordPressClient  # noqa: PLC0415

            with WordPressClient(
                site_url=cred.site_url,
                username="admin",
                app_password=cred.app_password,
            ) as wp:
                wp.verify_connection()

            cred.last_verified_at = datetime.now(UTC).replace(tzinfo=None)
            db.commit()
            log.info("credential_test_passed", credential_id=cred_id, platform="wordpress")
            return {
                "status": "ok",
                "platform": "wordpress",
                "site_url": cred.site_url,
                "credential_id": cred_id,
            }
        except Exception as exc:
            cred.last_verified_at = None
            db.commit()
            log.warning(
                "credential_test_failed",
                credential_id=cred_id,
                platform="wordpress",
                error=str(exc),
            )
            raise HTTPException(
                status_code=400,
                detail=f"WordPress connection failed: {exc}",
            ) from exc

    elif cred.platform == "shopify":
        if not cred.access_token:
            raise HTTPException(
                status_code=400,
                detail="Shopify credentials are missing an access token",
            )
        try:
            from backend.platforms.shopify.client import ShopifyClient  # noqa: PLC0415

            with ShopifyClient(
                shop_url=cred.site_url,
                access_token=cred.access_token,
            ) as shopify:
                shop_info = shopify.get_shop_info()

            cred.last_verified_at = datetime.now(UTC).replace(tzinfo=None)
            db.commit()
            log.info("credential_test_passed", credential_id=cred_id, platform="shopify")
            return {
                "status": "ok",
                "platform": "shopify",
                "shop_name": shop_info.get("name"),
                "shop_domain": shop_info.get("domain"),
                "credential_id": cred_id,
            }
        except Exception as exc:
            cred.last_verified_at = None
            db.commit()
            log.warning(
                "credential_test_failed",
                credential_id=cred_id,
                platform="shopify",
                error=str(exc),
            )
            raise HTTPException(
                status_code=400,
                detail=f"Shopify connection failed: {exc}",
            ) from exc

    else:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown platform '{cred.platform}'. Expected 'wordpress' or 'shopify'.",
        )


@router.delete("/credentials/{cred_id}")
def delete_credential(
    cred_id: int,
    db: Session = Depends(get_session),
) -> dict:
    """Permanently delete a stored credential record."""
    cred = db.get(PlatformCredential, cred_id)
    if cred is None:
        raise HTTPException(
            status_code=404,
            detail=f"Credential {cred_id} not found",
        )

    db.delete(cred)
    db.commit()

    log.info("credential_deleted", credential_id=cred_id)
    return {"detail": "Credential deleted", "credential_id": cred_id}

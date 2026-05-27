"""OAuth initiation and callback routes for all platforms."""
import secrets
import logging
from datetime import datetime, timezone, timedelta
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
import redis as redis_lib

from backend.db.session import get_db
from backend.db.models import PlatformAccount, Client
from backend.platforms.base import encrypt
from backend.config import get_settings

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/oauth", tags=["oauth"])

_redis: redis_lib.Redis | None = None


def get_redis() -> redis_lib.Redis:
    global _redis
    if _redis is None:
        _redis = redis_lib.from_url(get_settings().redis_url, decode_responses=True)
    return _redis


STATE_TTL = 600  # 10 minutes


def _store_state(state: str, client_id: int, platform: str) -> None:
    get_redis().setex(f"oauth_state:{state}", STATE_TTL, f"{client_id}:{platform}")


def _consume_state(state: str) -> tuple[int, str] | None:
    """Return (client_id, platform) and DELETE the state key (one-time use)."""
    key = f"oauth_state:{state}"
    r = get_redis()
    value = r.get(key)
    if not value:
        return None
    r.delete(key)
    parts = value.split(":", 1)
    return int(parts[0]), parts[1]


@router.get("/initiate/{client_id}/{platform}")
def initiate_oauth(client_id: int, platform: str, db: Session = Depends(get_db)):
    client = db.get(Client, client_id)
    if not client:
        raise HTTPException(404, "Client not found")

    settings = get_settings()
    state = secrets.token_urlsafe(32)
    _store_state(state, client_id, platform)

    base_url = settings.oauth_callback_base_url
    redirect_uri = f"{base_url}/oauth/callback/{platform}"

    url = _build_oauth_url(platform, state, redirect_uri, settings)
    return {"oauth_url": url, "state": state}


def _build_oauth_url(platform: str, state: str, redirect_uri: str, settings) -> str:
    from backend.platforms.meta import MetaPlatform
    from backend.platforms.google import GooglePlatform
    from backend.platforms.linkedin import LinkedInPlatform
    from backend.platforms.tiktok import TikTokPlatform
    from backend.platforms.twitter import TwitterPlatform

    if platform in ("instagram", "facebook", "whatsapp"):
        return MetaPlatform().get_oauth_url(settings.meta_app_id, redirect_uri, state, platform)
    if platform in ("youtube", "google_business"):
        return GooglePlatform().get_oauth_url(settings.google_client_id, redirect_uri, state, platform)
    if platform == "linkedin":
        return LinkedInPlatform().get_oauth_url(settings.linkedin_client_id, redirect_uri, state)
    if platform == "tiktok":
        return TikTokPlatform().get_oauth_url(settings.tiktok_client_key, redirect_uri, state)
    if platform == "twitter":
        code_challenge = secrets.token_urlsafe(32)
        return TwitterPlatform().get_oauth_url(settings.twitter_client_id, redirect_uri, state, code_challenge)
    raise HTTPException(400, f"Unsupported platform: {platform}")


@router.get("/callback/{platform}")
def oauth_callback(platform: str, code: str, state: str, db: Session = Depends(get_db)):
    result = _consume_state(state)
    if not result:
        raise HTTPException(400, "Invalid or expired OAuth state")

    client_id, stored_platform = result
    if stored_platform != platform:
        raise HTTPException(400, "Platform mismatch in OAuth state")

    settings = get_settings()
    base_url = settings.oauth_callback_base_url
    redirect_uri = f"{base_url}/oauth/callback/{platform}"

    tokens = _exchange_code(platform, code, redirect_uri, settings)
    _save_account(client_id, platform, tokens, db)
    return {"status": "connected", "platform": platform}


def _exchange_code(platform: str, code: str, redirect_uri: str, settings) -> dict:
    from backend.platforms.meta import MetaPlatform
    from backend.platforms.google import GooglePlatform
    from backend.platforms.linkedin import LinkedInPlatform
    from backend.platforms.tiktok import TikTokPlatform
    from backend.platforms.twitter import TwitterPlatform

    if platform in ("instagram", "facebook", "whatsapp"):
        return MetaPlatform().exchange_code(code, settings.meta_app_id, settings.meta_app_secret, redirect_uri)
    if platform in ("youtube", "google_business"):
        return GooglePlatform().exchange_code(code, settings.google_client_id, settings.google_client_secret, redirect_uri)
    if platform == "linkedin":
        return LinkedInPlatform().exchange_code(code, settings.linkedin_client_id, settings.linkedin_client_secret, redirect_uri)
    if platform == "tiktok":
        return TikTokPlatform().exchange_code(code, settings.tiktok_client_key, settings.tiktok_client_secret, redirect_uri)
    raise HTTPException(400, f"Unsupported platform: {platform}")


def _save_account(client_id: int, platform: str, tokens: dict, db: Session) -> None:
    access_token = tokens.get("access_token", "")
    refresh_token = tokens.get("refresh_token")
    expires_in = tokens.get("expires_in")
    expires_at = (datetime.now(timezone.utc) + timedelta(seconds=expires_in)) if expires_in else None

    existing = db.query(PlatformAccount).filter_by(client_id=client_id, platform=platform).first()
    if existing:
        existing.access_token = encrypt(access_token)
        existing.refresh_token = encrypt(refresh_token) if refresh_token else existing.refresh_token
        existing.token_expires_at = expires_at
        existing.is_active = True
        existing.last_verified_at = datetime.now(timezone.utc)
    else:
        account = PlatformAccount(
            client_id=client_id,
            platform=platform,
            access_token=encrypt(access_token),
            refresh_token=encrypt(refresh_token) if refresh_token else None,
            token_expires_at=expires_at,
            is_active=True,
            last_verified_at=datetime.now(timezone.utc),
        )
        db.add(account)
    db.commit()

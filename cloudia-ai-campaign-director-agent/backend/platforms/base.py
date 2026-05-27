"""BasePlatform — OAuth token management and encryption."""
import logging
from datetime import datetime, timedelta, timezone
from cryptography.fernet import Fernet, InvalidToken

from backend.config import get_settings
from backend.db.models import PlatformAccount

logger = logging.getLogger(__name__)

_fernet: Fernet | None = None


def _get_fernet() -> Fernet:
    global _fernet
    if _fernet is None:
        key = get_settings().encryption_key
        if not key:
            raise RuntimeError("ENCRYPTION_KEY not set — cannot encrypt/decrypt tokens")
        _fernet = Fernet(key.encode() if isinstance(key, str) else key)
    return _fernet


def encrypt(value: str) -> str:
    return _get_fernet().encrypt(value.encode()).decode()


def decrypt(value: str) -> str:
    return _get_fernet().decrypt(value.encode()).decode()


class BasePlatform:
    platform_name: str = "base"

    def get_valid_token(self, account: PlatformAccount) -> str:
        """Return a valid access token, refreshing if needed."""
        if account.token_expires_at:
            expires_at = account.token_expires_at
            if expires_at.tzinfo is None:
                expires_at = expires_at.replace(tzinfo=timezone.utc)
            if expires_at < datetime.now(timezone.utc) + timedelta(minutes=5):
                return self.refresh_token(account)
        return decrypt(account.access_token)

    def refresh_token(self, account: PlatformAccount) -> str:
        """Platform-specific token refresh. Must update account in DB and return new token."""
        raise NotImplementedError(f"{self.platform_name} does not implement token refresh")

    def _store_tokens(self, account: PlatformAccount, access_token: str, refresh_token: str | None,
                      expires_at: datetime | None, db) -> None:
        """Encrypt and persist tokens. Never log raw tokens."""
        account.access_token = encrypt(access_token)
        if refresh_token:
            account.refresh_token = encrypt(refresh_token)
        account.token_expires_at = expires_at
        account.last_verified_at = datetime.now(timezone.utc)
        db.commit()

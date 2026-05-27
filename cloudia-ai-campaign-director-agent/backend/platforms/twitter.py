"""X (Twitter) API v2."""
import httpx
from backend.platforms.base import BasePlatform, decrypt
from backend.db.models import PlatformAccount

TW_BASE = "https://api.twitter.com/2"
TW_AUTH = "https://twitter.com/i/oauth2/authorize"


class TwitterPlatform(BasePlatform):
    platform_name = "twitter"

    def get_oauth_url(self, client_id: str, redirect_uri: str, state: str, code_challenge: str) -> str:
        return (
            f"{TW_AUTH}?response_type=code&client_id={client_id}"
            f"&redirect_uri={redirect_uri}&scope=tweet.write+users.read+offline.access"
            f"&state={state}&code_challenge={code_challenge}&code_challenge_method=S256"
        )

    def exchange_code(self, code: str, client_id: str, client_secret: str,
                      redirect_uri: str, code_verifier: str) -> dict:
        r = httpx.post("https://api.twitter.com/2/oauth2/token", data={
            "code": code, "grant_type": "authorization_code",
            "client_id": client_id, "redirect_uri": redirect_uri, "code_verifier": code_verifier,
        }, auth=(client_id, client_secret), timeout=30)
        r.raise_for_status()
        return r.json()

    def refresh_token(self, account: PlatformAccount) -> str:
        from backend.config import get_settings
        s = get_settings()
        r = httpx.post("https://api.twitter.com/2/oauth2/token", data={
            "refresh_token": decrypt(account.refresh_token), "grant_type": "refresh_token",
        }, auth=(s.twitter_client_id, s.twitter_client_secret), timeout=30)
        r.raise_for_status()
        return r.json()["access_token"]

    def publish_tweet(self, account: PlatformAccount, text: str, media_id: str | None = None) -> str:
        token = self.get_valid_token(account)
        payload = {"text": text[:280]}
        if media_id:
            payload["media"] = {"media_ids": [media_id]}
        r = httpx.post(f"{TW_BASE}/tweets", json=payload,
                       headers={"Authorization": f"Bearer {token}"}, timeout=60)
        r.raise_for_status()
        return r.json()["data"]["id"]

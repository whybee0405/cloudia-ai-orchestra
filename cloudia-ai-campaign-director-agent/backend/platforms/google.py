"""Google platform — Google Business Profile + YouTube."""
import logging
import httpx
from datetime import datetime, timezone, timedelta
from backend.platforms.base import BasePlatform, decrypt
from backend.db.models import PlatformAccount

logger = logging.getLogger(__name__)
GOOGLE_AUTH = "https://oauth2.googleapis.com/token"
GMB_BASE = "https://mybusiness.googleapis.com/v4"
YOUTUBE_BASE = "https://www.googleapis.com/upload/youtube/v3"


class GooglePlatform(BasePlatform):
    platform_name = "google"

    def get_oauth_url(self, client_id: str, redirect_uri: str, state: str, platform: str) -> str:
        scopes = {
            "google_business": "https://www.googleapis.com/auth/business.manage",
            "youtube": "https://www.googleapis.com/auth/youtube.upload",
        }.get(platform, "https://www.googleapis.com/auth/business.manage")
        return (
            f"https://accounts.google.com/o/oauth2/v2/auth"
            f"?client_id={client_id}&redirect_uri={redirect_uri}"
            f"&response_type=code&scope={scopes}&state={state}&access_type=offline"
        )

    def exchange_code(self, code: str, client_id: str, client_secret: str, redirect_uri: str) -> dict:
        r = httpx.post(GOOGLE_AUTH, data={
            "code": code, "client_id": client_id, "client_secret": client_secret,
            "redirect_uri": redirect_uri, "grant_type": "authorization_code",
        }, timeout=30)
        r.raise_for_status()
        return r.json()

    def refresh_token(self, account: PlatformAccount) -> str:
        from backend.config import get_settings
        s = get_settings()
        r = httpx.post(GOOGLE_AUTH, data={
            "refresh_token": decrypt(account.refresh_token),
            "client_id": s.google_client_id,
            "client_secret": s.google_client_secret,
            "grant_type": "refresh_token",
        }, timeout=30)
        r.raise_for_status()
        return r.json()["access_token"]

    def publish_google_business_post(self, account: PlatformAccount, caption: str, image_url: str | None = None) -> str:
        token = self.get_valid_token(account)
        location_name = account.account_id
        payload = {
            "languageCode": "en",
            "summary": caption,
            "topicType": "STANDARD",
        }
        if image_url:
            payload["media"] = [{"mediaFormat": "PHOTO", "sourceUrl": image_url}]
        r = httpx.post(f"{GMB_BASE}/{location_name}/localPosts",
                       json=payload, headers={"Authorization": f"Bearer {token}"}, timeout=60)
        r.raise_for_status()
        return r.json().get("name", "")

    def publish_youtube_video(self, account: PlatformAccount, video_bytes: bytes, title: str,
                              description: str, tags: list[str]) -> str:
        token = self.get_valid_token(account)
        params = {"part": "snippet,status", "uploadType": "multipart"}
        metadata = {
            "snippet": {"title": title[:100], "description": description[:5000], "tags": tags[:500]},
            "status": {"privacyStatus": "public"},
        }
        r = httpx.post(f"{YOUTUBE_BASE}/videos", params=params,
                       headers={"Authorization": f"Bearer {token}"},
                       files={"metadata": (None, str(metadata), "application/json"), "video": video_bytes},
                       timeout=300)
        r.raise_for_status()
        return r.json()["id"]

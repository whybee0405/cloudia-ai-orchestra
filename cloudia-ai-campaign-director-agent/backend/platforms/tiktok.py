"""TikTok Business API."""
import httpx
from backend.platforms.base import BasePlatform, decrypt
from backend.db.models import PlatformAccount

TT_BASE = "https://open.tiktokapis.com/v2"
TT_AUTH = "https://www.tiktok.com/v2/auth/authorize"


class TikTokPlatform(BasePlatform):
    platform_name = "tiktok"

    def get_oauth_url(self, client_key: str, redirect_uri: str, state: str) -> str:
        return (
            f"{TT_AUTH}?client_key={client_key}&scope=video.publish"
            f"&response_type=code&redirect_uri={redirect_uri}&state={state}"
        )

    def exchange_code(self, code: str, client_key: str, client_secret: str, redirect_uri: str) -> dict:
        r = httpx.post("https://open.tiktokapis.com/v2/oauth/token/", data={
            "client_key": client_key, "client_secret": client_secret,
            "code": code, "grant_type": "authorization_code", "redirect_uri": redirect_uri,
        }, timeout=30)
        r.raise_for_status()
        return r.json().get("data", {})

    def refresh_token(self, account: PlatformAccount) -> str:
        from backend.config import get_settings
        s = get_settings()
        r = httpx.post("https://open.tiktokapis.com/v2/oauth/token/", data={
            "client_key": s.tiktok_client_key, "client_secret": s.tiktok_client_secret,
            "grant_type": "refresh_token", "refresh_token": decrypt(account.refresh_token),
        }, timeout=30)
        r.raise_for_status()
        return r.json()["data"]["access_token"]

    def publish_tiktok_video(self, account: PlatformAccount, video_bytes: bytes,
                              caption: str, hashtags: list[str]) -> str:
        token = self.get_valid_token(account)
        tags = " ".join(hashtags[:5])
        full_caption = f"{caption} {tags}".strip()[:2200]
        # TikTok requires server-side upload; simplified here
        r = httpx.post(f"{TT_BASE}/post/publish/video/init/",
                       json={"post_info": {"title": full_caption[:150], "privacy_level": "PUBLIC_TO_EVERYONE"},
                             "source_info": {"source": "FILE_UPLOAD", "video_size": len(video_bytes)}},
                       headers={"Authorization": f"Bearer {token}"}, timeout=60)
        r.raise_for_status()
        publish_id = r.json().get("data", {}).get("publish_id", "")
        return publish_id

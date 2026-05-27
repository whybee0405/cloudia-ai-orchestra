"""LinkedIn Marketing API."""
import httpx
from datetime import datetime, timezone, timedelta
from backend.platforms.base import BasePlatform, decrypt
from backend.db.models import PlatformAccount

LI_BASE = "https://api.linkedin.com/v2"
LI_AUTH = "https://www.linkedin.com/oauth/v2"


class LinkedInPlatform(BasePlatform):
    platform_name = "linkedin"

    def get_oauth_url(self, client_id: str, redirect_uri: str, state: str) -> str:
        return (
            f"{LI_AUTH}/authorization?response_type=code&client_id={client_id}"
            f"&redirect_uri={redirect_uri}&state={state}"
            f"&scope=w_member_social,r_liteprofile"
        )

    def exchange_code(self, code: str, client_id: str, client_secret: str, redirect_uri: str) -> dict:
        r = httpx.post(f"{LI_AUTH}/accessToken", data={
            "grant_type": "authorization_code", "code": code,
            "redirect_uri": redirect_uri, "client_id": client_id, "client_secret": client_secret,
        }, timeout=30)
        r.raise_for_status()
        return r.json()

    def refresh_token(self, account: PlatformAccount) -> str:
        from backend.config import get_settings
        s = get_settings()
        r = httpx.post(f"{LI_AUTH}/accessToken", data={
            "grant_type": "refresh_token",
            "refresh_token": decrypt(account.refresh_token),
            "client_id": s.linkedin_client_id,
            "client_secret": s.linkedin_client_secret,
        }, timeout=30)
        r.raise_for_status()
        return r.json()["access_token"]

    def publish_linkedin_post(self, account: PlatformAccount, caption: str, image_url: str | None = None) -> str:
        token = self.get_valid_token(account)
        author = f"urn:li:organization:{account.account_id}"
        payload = {
            "author": author,
            "lifecycleState": "PUBLISHED",
            "specificContent": {
                "com.linkedin.ugc.ShareContent": {
                    "shareCommentary": {"text": caption},
                    "shareMediaCategory": "NONE" if not image_url else "IMAGE",
                }
            },
            "visibility": {"com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"},
        }
        r = httpx.post(f"{LI_BASE}/ugcPosts", json=payload,
                       headers={"Authorization": f"Bearer {token}", "X-Restli-Protocol-Version": "2.0.0"},
                       timeout=60)
        r.raise_for_status()
        return r.headers.get("x-restli-id", "")

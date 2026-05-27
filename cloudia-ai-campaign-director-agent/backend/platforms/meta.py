"""Meta platform — Facebook, Instagram, WhatsApp (Meta Graph API)."""
import logging
import httpx
from datetime import datetime, timezone, timedelta
from backend.platforms.base import BasePlatform, decrypt
from backend.db.models import PlatformAccount

logger = logging.getLogger(__name__)
GRAPH_BASE = "https://graph.facebook.com/v19.0"


class MetaPlatform(BasePlatform):
    platform_name = "meta"

    def get_oauth_url(self, app_id: str, redirect_uri: str, state: str, platform: str) -> str:
        scopes = {
            "instagram": "instagram_basic,instagram_content_publish,pages_show_list,pages_read_engagement",
            "facebook": "pages_show_list,pages_read_engagement,pages_manage_posts",
            "whatsapp": "whatsapp_business_management,whatsapp_business_messaging",
        }.get(platform, "pages_show_list")
        return (
            f"https://www.facebook.com/dialog/oauth"
            f"?client_id={app_id}&redirect_uri={redirect_uri}"
            f"&state={state}&scope={scopes}"
        )

    def exchange_code(self, code: str, app_id: str, app_secret: str, redirect_uri: str) -> dict:
        r = httpx.get(f"{GRAPH_BASE}/oauth/access_token", params={
            "client_id": app_id, "client_secret": app_secret,
            "redirect_uri": redirect_uri, "code": code,
        }, timeout=30)
        r.raise_for_status()
        return r.json()

    def refresh_token(self, account: PlatformAccount) -> str:
        from backend.config import get_settings
        s = get_settings()
        old_token = decrypt(account.access_token)
        r = httpx.get(f"{GRAPH_BASE}/oauth/access_token", params={
            "grant_type": "fb_exchange_token",
            "client_id": s.meta_app_id,
            "client_secret": s.meta_app_secret,
            "fb_exchange_token": old_token,
        }, timeout=30)
        r.raise_for_status()
        data = r.json()
        new_token = data["access_token"]
        expires_in = data.get("expires_in", 5184000)
        expires_at = datetime.now(timezone.utc) + timedelta(seconds=expires_in)
        return new_token

    def publish_instagram_image(self, account: PlatformAccount, image_url: str, caption: str) -> str:
        token = self.get_valid_token(account)
        ig_id = account.account_id
        # Step 1: create container
        r = httpx.post(f"{GRAPH_BASE}/{ig_id}/media", params={
            "image_url": image_url, "caption": caption, "access_token": token,
        }, timeout=60)
        r.raise_for_status()
        container_id = r.json()["id"]
        # Step 2: publish
        r2 = httpx.post(f"{GRAPH_BASE}/{ig_id}/media_publish", params={
            "creation_id": container_id, "access_token": token,
        }, timeout=60)
        r2.raise_for_status()
        return r2.json()["id"]

    def publish_instagram_reel(self, account: PlatformAccount, video_url: str, caption: str) -> str:
        token = self.get_valid_token(account)
        ig_id = account.account_id
        r = httpx.post(f"{GRAPH_BASE}/{ig_id}/media", params={
            "media_type": "REELS", "video_url": video_url, "caption": caption, "access_token": token,
        }, timeout=120)
        r.raise_for_status()
        container_id = r.json()["id"]
        r2 = httpx.post(f"{GRAPH_BASE}/{ig_id}/media_publish", params={
            "creation_id": container_id, "access_token": token,
        }, timeout=60)
        r2.raise_for_status()
        return r2.json()["id"]

    def publish_instagram_story(self, account: PlatformAccount, image_url: str) -> str:
        token = self.get_valid_token(account)
        ig_id = account.account_id
        r = httpx.post(f"{GRAPH_BASE}/{ig_id}/media", params={
            "image_url": image_url, "media_type": "STORIES", "access_token": token,
        }, timeout=60)
        r.raise_for_status()
        container_id = r.json()["id"]
        r2 = httpx.post(f"{GRAPH_BASE}/{ig_id}/media_publish", params={
            "creation_id": container_id, "access_token": token,
        }, timeout=60)
        r2.raise_for_status()
        return r2.json()["id"]

    def publish_facebook_post(self, account: PlatformAccount, message: str, image_url: str | None = None) -> str:
        token = self.get_valid_token(account)
        page_id = account.page_id or account.account_id
        params = {"message": message, "access_token": token}
        if image_url:
            params["link"] = image_url
        r = httpx.post(f"{GRAPH_BASE}/{page_id}/feed", params=params, timeout=60)
        r.raise_for_status()
        return r.json()["id"]

    def publish_whatsapp_broadcast(self, account: PlatformAccount, message: str, media_path: str | None = None) -> str:
        token = self.get_valid_token(account)
        phone_number_id = account.account_id
        payload = {"messaging_product": "whatsapp", "to": "broadcast", "type": "text",
                   "text": {"body": message}}
        r = httpx.post(f"{GRAPH_BASE}/{phone_number_id}/messages",
                       json=payload, headers={"Authorization": f"Bearer {token}"}, timeout=60)
        r.raise_for_status()
        return r.json().get("messages", [{}])[0].get("id", "")

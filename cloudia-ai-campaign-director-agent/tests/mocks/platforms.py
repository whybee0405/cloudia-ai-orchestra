"""Mock platform clients for Meta, Google, LinkedIn, TikTok, Twitter."""
from unittest.mock import MagicMock


class MockMetaPlatform:
    """Tracks calls and supports configurable failure modes."""

    def __init__(self):
        self.calls = []
        self._mode = "success"

    def set_mode(self, mode: str):
        self._mode = mode  # success | auth_failure | rate_limit | media_too_large | invalid_format

    def _check_mode(self):
        import httpx
        if self._mode == "auth_failure":
            raise Exception("401 Unauthorized — re-auth required")
        if self._mode == "rate_limit":
            raise Exception("429 Rate limit exceeded")
        if self._mode == "media_too_large":
            raise Exception("Media file too large")
        if self._mode == "invalid_format":
            raise Exception("Unsupported media format")

    def publish_instagram_image(self, account, media_url, caption):
        self._check_mode()
        call = {"method": "publish_instagram_image", "account_id": account.account_id, "caption": caption}
        self.calls.append(call)
        return f"ig_image_{len(self.calls)}"

    def publish_instagram_reel(self, account, media_url, caption):
        self._check_mode()
        call = {"method": "publish_instagram_reel", "account_id": account.account_id, "caption": caption}
        self.calls.append(call)
        return f"ig_reel_{len(self.calls)}"

    def publish_facebook_post(self, account, caption, media_url=None):
        self._check_mode()
        call = {"method": "publish_facebook_post", "account_id": account.account_id, "caption": caption}
        self.calls.append(call)
        return f"fb_{len(self.calls)}_987654"

    def publish_whatsapp_broadcast(self, account, message):
        self._check_mode()
        call = {"method": "publish_whatsapp_broadcast", "account_id": account.account_id}
        self.calls.append(call)
        return f"wamid.{len(self.calls)}"

    def get_oauth_url(self, app_id, redirect_uri, state, platform):
        return f"https://facebook.com/dialog/oauth?app_id={app_id}&state={state}"

    def exchange_code(self, code, app_id, app_secret, redirect_uri):
        return {"access_token": "mock_long_lived_token", "expires_in": 5184000}

    def assert_token_used(self, expected_account_id: str):
        for call in self.calls:
            if call.get("account_id") == expected_account_id:
                return True
        raise AssertionError(f"Expected account_id '{expected_account_id}' in calls: {self.calls}")

    def reset(self):
        self.calls = []
        self._mode = "success"


class MockLinkedInPlatform:
    def __init__(self):
        self.calls = []
        self._mode = "success"

    def set_mode(self, mode: str):
        self._mode = mode

    def publish_linkedin_post(self, account, caption, media_url=None):
        if self._mode != "success":
            raise Exception(f"LinkedIn error: {self._mode}")
        self.calls.append({"method": "publish_linkedin_post", "account_id": account.account_id})
        return f"urn:li:share:{len(self.calls)}"

    def get_oauth_url(self, client_id, redirect_uri, state):
        return f"https://linkedin.com/oauth/v2/authorization?client_id={client_id}&state={state}"

    def exchange_code(self, code, client_id, client_secret, redirect_uri):
        return {"access_token": "mock_li_token", "expires_in": 5184000}


class MockTikTokPlatform:
    def __init__(self):
        self.calls = []
        self._mode = "success"

    def set_mode(self, mode: str):
        self._mode = mode

    def publish_tiktok_video(self, account, media_bytes, caption, hashtags):
        if self._mode != "success":
            raise Exception(f"TikTok error: {self._mode}")
        self.calls.append({"method": "publish_tiktok_video", "account_id": account.account_id})
        return f"tiktok_video_{len(self.calls)}"

    def get_oauth_url(self, client_key, redirect_uri, state):
        return f"https://open.tiktok.com/platform/oauth/connect?client_key={client_key}&state={state}"

    def exchange_code(self, code, client_key, client_secret, redirect_uri):
        return {"access_token": "mock_tt_token", "expires_in": 86400}


class MockTwitterPlatform:
    def __init__(self):
        self.calls = []
        self._mode = "success"

    def set_mode(self, mode: str):
        self._mode = mode

    def publish_tweet(self, account, text):
        if self._mode != "success":
            raise Exception(f"Twitter error: {self._mode}")
        self.calls.append({"method": "publish_tweet", "account_id": account.account_id, "text": text})
        return f"tweet_{len(self.calls)}"

    def get_oauth_url(self, client_id, redirect_uri, state, code_challenge):
        return f"https://twitter.com/i/oauth2/authorize?client_id={client_id}&state={state}"


class MockMinIO:
    """Tracks uploads/downloads and supports failure injection."""

    def __init__(self):
        self.objects = {}
        self._mode = "success"

    def set_mode(self, mode: str):
        self._mode = mode  # success | bucket_not_found | upload_failure | download_timeout

    def upload(self, data: bytes, path: str, content_type: str = "application/octet-stream"):
        if self._mode == "upload_failure":
            raise IOError("MinIO upload failed")
        if self._mode == "bucket_not_found":
            raise Exception("Bucket 'cloudia-media' does not exist")
        self.objects[path] = data

    def download(self, path: str) -> bytes:
        if self._mode == "download_timeout":
            raise TimeoutError("MinIO download timed out")
        if path not in self.objects:
            return b"fake_file_bytes"
        return self.objects[path]

    def signed_url(self, path: str, client_id_prefix: str = None) -> str:
        if client_id_prefix and not path.startswith(f"{client_id_prefix}/"):
            raise PermissionError(f"Path {path} not accessible for client {client_id_prefix}")
        return f"https://minio.local/{path}?sig=abc123"

    def object_path(self, client_id, campaign_id, stage, subdir, filename) -> str:
        return f"{client_id}/campaigns/{campaign_id}/{stage}/{subdir}/{filename}"

    def assert_stored_at(self, expected_prefix: str):
        for path in self.objects:
            if path.startswith(expected_prefix):
                return True
        raise AssertionError(
            f"Expected file stored under '{expected_prefix}', but found: {list(self.objects.keys())}"
        )

    def reset(self):
        self.objects = {}
        self._mode = "success"

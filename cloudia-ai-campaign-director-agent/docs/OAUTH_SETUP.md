# OAuth Setup Guide

Each platform requires registering an app and obtaining credentials.  
All credentials go in `.env` (never committed to git).

---

## Architecture

- OAuth state tokens: 32-byte `secrets.token_urlsafe()`, stored in Redis with 10-minute TTL
- State consumed on first use (DELETE immediately after GET in `_consume_state()`)
- Tokens stored encrypted with Fernet before writing to DB
- `ENCRYPTION_KEY` in `.env` must be a 32-byte base64 Fernet key

Generate a fresh key:
```bash
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

---

## Meta (Instagram + Facebook + WhatsApp)

**App setup:**
1. Go to [developers.facebook.com](https://developers.facebook.com/) → Create App → Business
2. Add products: Instagram Graph API, Facebook Login, WhatsApp Business API
3. Under App Settings → Basic: copy **App ID** and **App Secret**
4. Under Facebook Login → Settings → add Valid OAuth Redirect URIs:
   `https://yourdomain.com/oauth/callback/instagram`
   `https://yourdomain.com/oauth/callback/facebook`
5. Required permissions: `instagram_basic`, `instagram_content_publish`, `pages_manage_posts`, `whatsapp_business_messaging`

**Environment variables:**
```
META_APP_ID=your_app_id
META_APP_SECRET=your_app_secret
```

**Token type:** Long-lived page access token (60 days). Refresh via `MetaPlatform.refresh_token()`.

---

## Google (YouTube + Google Business Profile)

**App setup:**
1. Go to [console.cloud.google.com](https://console.cloud.google.com/) → New Project
2. Enable APIs: YouTube Data API v3, Google Business Profile API
3. Credentials → Create OAuth 2.0 Client ID → Web application
4. Add authorised redirect URIs:
   `https://yourdomain.com/oauth/callback/youtube`
   `https://yourdomain.com/oauth/callback/google_business`
5. Download `client_secret.json`, copy Client ID and Secret

**Environment variables:**
```
GOOGLE_CLIENT_ID=your_client_id
GOOGLE_CLIENT_SECRET=your_client_secret
```

**Scopes:** `https://www.googleapis.com/auth/youtube.upload`, `https://www.googleapis.com/auth/business.manage`

---

## LinkedIn

**App setup:**
1. Go to [developer.linkedin.com](https://www.linkedin.com/developers/) → Create App
2. Associate with a LinkedIn Company Page
3. Products: Share on LinkedIn, Marketing Developer Platform
4. Auth tab → add Authorized Redirect URLs:
   `https://yourdomain.com/oauth/callback/linkedin`
5. Copy Client ID and Client Secret

**Environment variables:**
```
LINKEDIN_CLIENT_ID=your_client_id
LINKEDIN_CLIENT_SECRET=your_client_secret
```

**Scopes:** `w_member_social`, `r_organization_social`, `w_organization_social`

---

## TikTok

**App setup:**
1. Go to [developers.tiktok.com](https://developers.tiktok.com/) → Create App
2. Product: Content Posting API
3. Configure Redirect URIs:
   `https://yourdomain.com/oauth/callback/tiktok`
4. Copy Client Key and Client Secret

**Environment variables:**
```
TIKTOK_CLIENT_KEY=your_client_key
TIKTOK_CLIENT_SECRET=your_client_secret
```

**Note:** TikTok requires Business Account approval for Content Posting API.

---

## Twitter / X

**App setup:**
1. Go to [developer.twitter.com](https://developer.twitter.com/) → Projects → Create App
2. App permissions: Read and Write
3. Enable OAuth 2.0, set Callback URL:
   `https://yourdomain.com/oauth/callback/twitter`
4. Copy Client ID and Client Secret

**Environment variables:**
```
TWITTER_CLIENT_ID=your_client_id
TWITTER_CLIENT_SECRET=your_client_secret
```

**Note:** Twitter OAuth 2.0 uses PKCE. `code_challenge` generated at initiation, stored with state.

---

## OAuth Flow

```
1. Operator: GET /oauth/initiate/{client_id}/{platform}
   → State token generated, stored in Redis with 10-min TTL
   → Returns { oauth_url, state }

2. Operator: Opens oauth_url in browser, authorises
   → Platform redirects to /oauth/callback/{platform}?code=...&state=...

3. Callback handler:
   → _consume_state(state): GET then DELETE from Redis (one-time use)
   → Validates platform matches stored state
   → Exchanges code for tokens
   → Stores encrypted tokens in platform_accounts

4. Done: is_active = true, last_verified_at = now
```

---

## Token Refresh

`BasePlatform.get_valid_token(account, db)`:
- If `token_expires_at - now < 5 minutes` → calls `_refresh_token()`
- If refresh fails → sets `is_active = false`, raises `AgentError`
- Refresh tokens stored encrypted; raw values never logged

---

## Initiating OAuth for a Client

Via the Platform Accounts page in the GUI, or directly:
```
GET /api/oauth/initiate/{client_id}/instagram
→ { "oauth_url": "https://www.facebook.com/dialog/oauth?...", "state": "..." }
```

Open the URL in a browser, complete the Meta authorisation, then the callback fires automatically.

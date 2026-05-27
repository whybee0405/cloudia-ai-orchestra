# Architecture Decision Records

---

## ADR-001: Per-Client OAuth Tokens (Option B)

**Decision:** Each client has their own platform tokens stored in `platform_accounts`.

**Alternatives considered:**
- Option A: Single operator token for all clients — simpler but breaks platform ToS for posting on behalf of multiple businesses

**Rationale:** Platforms (Meta, LinkedIn, etc.) require each business page/account to authorise the app individually. A single operator token cannot post to multiple clients' accounts. Per-client tokens also enable clean revocation (removing one client doesn't affect others).

**Consequences:** OAuth flow must be completed once per client per platform. Token refresh logic must run per-account.

---

## ADR-002: Fernet Encryption for Platform Tokens

**Decision:** All `access_token` and `refresh_token` columns encrypted with Fernet before DB write.

**Rationale:** If the database is compromised, raw tokens cannot be used to post to clients' accounts. Fernet uses AES-128-CBC + HMAC-SHA256, is well-audited, and is straightforward to rotate.

**Key management:** `ENCRYPTION_KEY` env var, required at startup. App refuses to start if missing.

**Rotation:** To rotate the key, decrypt all tokens with old key, re-encrypt with new key, replace env var.

---

## ADR-003: Redis for OAuth State, Not DB

**Decision:** OAuth state tokens stored in Redis with 10-minute TTL and deleted on first use.

**Rationale:** TTL enforcement is native to Redis (no cron needed). Atomic GET+DELETE prevents replay attacks. PostgreSQL would require a cron job to purge expired states.

---

## ADR-004: Prompt Injection Mitigation via Delimiters

**Decision:** `context_builder.py` wraps all client-provided strings in `[DATA_START]...[DATA_END]`.

**Rationale:** A client could put `IGNORE PREVIOUS INSTRUCTIONS` in their company name or brief. Delimiting client data as inert content reduces (not eliminates) risk of injection affecting Claude's instructions.

**Note:** This is defence-in-depth, not a complete solution. Claude itself also has system-prompt injection resistance, but relying on that alone violates defence-in-depth.

---

## ADR-005: Two Approval Gates (not zero, not continuous)

**Decision:** Hard stops at (1) calendar_review after Planner, (2) content_batch_review after Brand Consistency.

**Alternatives considered:**
- No gates: fully autonomous — too risky, wrong content could go live
- Gate per asset: too slow for high-volume campaigns
- One gate at end: calendar could be wrong, wasting all content generation

**Rationale:** Gate 1 prevents generating content for a misconfigured calendar (wrong platforms, wrong dates). Gate 2 allows a human review before any post is ever scheduled. Both can be approved quickly if the operator trusts the system.

---

## ADR-006: DALL-E 3 → Replicate Flux Fallback

**Decision:** Primary image generation with DALL-E 3; automatic fallback to Replicate Flux on `BadRequestError` or `RateLimitError`.

**Rationale:** DALL-E 3 has better brand style following and prompt understanding. Flux is cheaper and has no safety-filter content policy errors. Having both ensures image generation never blocks the pipeline.

---

## ADR-007: ffmpeg for All Video Operations

**Decision:** All video assembly, transcoding, and format conversion done via ffmpeg.

**Rationale:** ffmpeg handles every video format/codec combination. It's free, widely supported, and has Python subprocess wrappers. Commercial video SDKs add cost and vendor lock-in.

**Implementation:** ffmpeg installed at Docker image build time (`apt-get install ffmpeg`). Worker verifies availability at startup, not at task execution time.

---

## ADR-008: Celery with Redis Broker (not RabbitMQ)

**Decision:** Redis serves as both the OAuth state store and Celery broker.

**Rationale:** Running one broker (Redis) instead of two (Redis + RabbitMQ) reduces operational complexity. Redis Celery backend is reliable for our task volumes. For very high throughput, migrating to RabbitMQ is straightforward.

---

## ADR-009: Port Offsets for Sister Systems

**Decision:** All ports offset from defaults (5433, 6380, 8001, 5174).

**Rationale:** This system runs alongside other systems on the same VPS. Default ports would conflict. Offsets are systematic (+1 for PostgreSQL, +1 for Redis, +1 for API, +1 for Frontend) to make the pattern memorable.

---

## ADR-010: ContentCalendar Created Before ContentAssets Ordered

**Decision:** In the Alembic migration, `content_assets` table is created before `content_calendar`.

**Rationale:** `content_calendar.asset_id` references `content_assets.id`. SQLAlchemy ORM definitions can have the FK either way, but the migration must create the referenced table first. This is an implementation detail, not a schema design choice.

---

## ADR-011: Brand Consistency Severity Tiers

**Decision:** CRITICAL/HIGH failures block the pipeline; MEDIUM/LOW pass with warnings.

**Rationale:**
- CRITICAL (competitor name in content) and HIGH (forbidden word, over char limit) would embarrass the client or violate brand policy — must block.
- MEDIUM (missing CTA) and LOW (informal tone) are style suggestions — blocking on these would slow the pipeline excessively for minor issues.

Operators can see warnings in the asset review screen.

---

## ADR-012: MinIO for Media Storage (not cloud S3)

**Decision:** MinIO as object storage, not AWS S3 or GCS.

**Rationale:** Self-hosted, no per-GB egress costs, S3-compatible API (migration to S3 is a config change). For a SaaS on a VPS, MinIO is appropriate. The `minio` Python SDK is a drop-in replacement for `boto3` in most cases.

**Bucket isolation:** Path prefix `{client_id}/` enforced in all storage operations. Presigned URLs validated against `client_id_prefix` before generation.

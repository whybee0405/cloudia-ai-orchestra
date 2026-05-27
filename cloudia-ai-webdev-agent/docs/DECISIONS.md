# Architecture Decisions

## Why Celery + Redis instead of a process manager?

Celery provides: retry logic, result storage, task chaining, worker monitoring, and rate limiting built-in. The approval gate pattern (blocking a task until a human approves) maps cleanly to Celery retries with countdown. Redis is already required for the result backend, so no additional infrastructure.

## Why human gates before the first API call to WordPress/Shopify?

A bad Claude response that gets published to a real client's live site causes irreversible reputational damage. Content approval costs 5 minutes of operator time per project. The downside of not having it is enormous relative to the friction cost.

## Why SQLAlchemy JSON not PostgreSQL JSONB?

JSONB is PostgreSQL-specific. All tests run on SQLite in-memory. Using `sqlalchemy.JSON` means zero test infrastructure changes and identical column behaviour in production (PostgreSQL stores JSON efficiently regardless of type annotation).

## Why Fernet for credential encryption?

Fernet (AES-128-CBC + HMAC-SHA256) from the `cryptography` library:
- Authenticated encryption — tampering detected
- Random IV per encryption — same plaintext produces different ciphertext
- Part of the standard `cryptography` package already in requirements
- Key derivation from `ENCRYPTION_KEY` env var — zero config beyond providing the key

Alternative considered: `pgcrypto` extension — rejected because it requires PostgreSQL-specific setup and doesn't work in test SQLite.

## Why WordPress Application Passwords and not admin username/password?

Application Passwords were introduced in WordPress 5.6 and are the official REST API authentication method. They:
- Can be revoked without changing the admin password
- Scope is limited to REST API only
- Don't expire (unlike OAuth tokens)
- Are stored hashed in WordPress

## Why Shopify Admin API (REST) and not GraphQL?

The Shopify Admin GraphQL API has quota limits based on query complexity, not request count. For a batch builder creating 20 products + 5 collections + 5 pages, the REST API's per-request throttling (2 req/second) is simpler to implement correctly than calculating GraphQL query costs. Migration to GraphQL can happen when scaling beyond current use case.

## Why Unsplash and not Pexels as primary?

Both are supported. Unsplash was chosen as primary because:
- Higher quality stock photos
- Better API documentation
- Free tier: 50 req/hour (sufficient for batch builds)
- Better attribution handling

Pexels is the fallback if Unsplash API key is not configured.

## Why no authentication for the operator GUI beyond API key?

This is an **internal tool only** — no public access, runs on a VPS. The API key in the `X-API-Key` header stored in localStorage is sufficient for the use case. If the system is ever exposed to the internet, add proper JWT auth.

## Why no multi-tenancy (one operator per instance)?

CloudIA is a single-operator shop. Multi-tenancy adds complexity (row-level security, tenant isolation, billing) with zero current value. The system can be deployed per-team if needed.

## Why structlog not Python's built-in logging?

structlog outputs JSON-compatible structured logs that work with log aggregators (Grafana Loki, CloudWatch, etc.). It also provides context binding (`log.bind(project_id=X)`) that automatically adds fields to every subsequent log in that scope. The built-in logging module requires formatters and adapters to achieve the same result.

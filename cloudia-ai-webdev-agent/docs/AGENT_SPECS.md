# Agent Specifications

## BaseAgent (`agents/base.py`)

All agents inherit from BaseAgent. Provides:
- `mark_running()` — sets task.status = "running", records started_at
- `mark_completed(output_data, tokens_used, cost_usd)` — records completion
- `mark_failed(error)` — records error, increments retry_count
- `execute()` — wraps `run()` with lifecycle management
- `get_project()` / `get_task()` — DB accessors

Agents must implement `run() -> dict`. Return dict may include `_tokens_used` and `_cost_usd` keys which BaseAgent pops and records to the task row.

## Director Agent

Not a BaseAgent — runs synchronously when operator creates a project.

**Input:** `client_id: int`, `raw_brief: dict`

**Output:** `{ project_id: int, platform: str, task_count: int }`

**Pipeline tasks created (WordPress):**
1. content_agent
2. media_agent
3. wp_structure_agent
4. wp_builder_agent
5. seo_agent
6. wp_qa_agent

**Pipeline tasks created (Shopify):**
1. content_agent
2. media_agent
3. shopify_structure_agent
4. shopify_builder_agent
5. shopify_theme_agent
6. seo_agent
7. shopify_qa_agent

**Failure modes:**
- Claude returns malformed JSON → project.status = "failed"
- Brief is empty → validation error returned before Claude call
- Platform = "ambiguous" → project.status = "needs_input", no tasks created

## Content Agent

**Input:** project_id, task_id

**Claude calls:** 1 per page (batched for efficiency if possible)

**Validation (all fail → retry up to 2x, then mark content piece as failed):**
- meta_title ≤ 60 chars
- meta_description ≤ 160 chars
- body_content > 100 chars
- No "lorem ipsum", "TODO", "[PLACEHOLDER]", "[INSERT"

**Output data:**
```json
{
  "pages_generated": 4,
  "pages_failed": 0,
  "gate_id": 1,
  "content_ids": [1, 2, 3, 4]
}
```

## Media Agent

**Input:** project_id, task_id

**Unsplash API:** `GET /search/photos?query=...&per_page=3&client_id=KEY`

**Rate limit:** 48 req/hour enforced with 1.5s delay between calls

**For each page:** downloads 1 image, resizes to max 1920px, saves to `media/project_{id}/`

**Attribution:** stored for every Unsplash image (legal requirement)

**Graceful degradation:** if no API key → log warning, return empty result (pipeline continues)

## WordPress Builder Agent

**Pre-requisites:** PlatformCredential with site_url + app_password for this client

**REST API endpoints used:**
- `POST /wp-json/wp/v2/pages` — create page
- `POST /wp-json/wp/v2/media` — upload image
- `POST /wp-json/wp/v2/menus` — create menu
- `POST /wp-json/wp/v2/menu-items` — add menu item
- `POST /wp-json/wp/v2/settings` — site title/tagline
- `POST /wp-json/wc/v3/products` — WooCommerce products

**Partial failure behaviour:** records `partial_failures: [{slug, error}]` in output_data. Operator can retry the task which resumes from first failed page.

## Shopify Builder Agent

**Rate limiting:** 2 req/second (0.5s between calls) — uses leaky bucket via `_throttle()`

**CRITICAL validation:** any product with price = 0 or None → ValueError before API call

**Assets API used by Theme Agent:**
- `GET /admin/api/2024-01/themes/{id}/assets.json?asset[key]=config/settings_data.json`
- `PUT /admin/api/2024-01/themes/{id}/assets.json` — update

## SEO Agent

**Schema types generated:**
- Home/About → LocalBusiness
- Service pages → Service
- Products → Product
- Restaurant pages → Restaurant

**Sitemap:** XML generated from project.site_url + all published page slugs. Validated with `xml.etree.ElementTree`.

**Meta validation:** flags (does not auto-truncate). Operator sees warnings in QA report.

## QA Agents

Both QA agents produce `qa_report` JSON:
```json
{
  "checks": [
    { "name": "all_pages_200", "severity": "CRITICAL", "passed": true },
    { "name": "meta_titles_present", "severity": "HIGH", "passed": false, "detail": "Page /contact missing meta title" }
  ],
  "critical_failures": [],
  "high_warnings": ["meta_titles_present"],
  "medium_warnings": [],
  "passed": true
}
```

**CRITICAL failure** → project.status = "failed", site_review gate NOT created, operator notified.
**Warnings only** → site_review gate created with notes field populated.

# CloudIA Website Agent System — Architecture

## Overview

A multi-agent AI orchestration system that builds professional WordPress and Shopify websites for SME clients. Agents run as Celery tasks. Humans approve content and built sites at defined gates before anything goes live.

## Component Map

```
Operator GUI (React)
       │  HTTP + WebSocket
       ▼
FastAPI API (backend/api/)
       │  DB reads/writes
       ▼
PostgreSQL ◄──────────────────────────────────────┐
       │  task queue                               │
       ▼                                           │
Redis ◄──── Celery Worker                          │
                │                                  │
                ▼                                  │
         Director Agent ──► Creates pipeline tasks ┘
                │
                ├──► Content Agent ──► [GATE: content_review]
                │                               │ (human approves)
                ├──► Media Agent ───────────────┘
                │
                ├──► Platform-specific pipeline:
                │       WP:      Structure → Builder → SEO → QA → [GATE: site_review]
                │       Shopify: Structure → Builder → Theme → SEO → QA → [GATE: store_review]
                │
                └──► Operator notified → approves → project complete
```

## Agent Descriptions

| Agent | File | Trigger |
|---|---|---|
| Director | `agents/director.py` | New project created |
| Content | `agents/shared/content_agent.py` | Director queues it |
| Media | `agents/shared/media_agent.py` | content_review gate approved |
| SEO | `agents/shared/seo_agent.py` | Builder agent completes |
| WP Structure | `agents/wordpress/structure_agent.py` | content_review gate approved |
| WP Builder | `agents/wordpress/builder_agent.py` | WP Structure completes |
| WP QA | `agents/wordpress/qa_agent.py` | WP Builder completes |
| Shopify Structure | `agents/shopify/structure_agent.py` | content_review gate approved |
| Shopify Builder | `agents/shopify/builder_agent.py` | Shopify Structure completes |
| Shopify Theme | `agents/shopify/theme_agent.py` | Shopify Builder completes |
| Shopify QA | `agents/shopify/qa_agent.py` | Shopify Theme completes |

## Approval Gates

Two gates in every project:
1. **content_review** — Human reads and approves all generated copy before any API call to WP/Shopify
2. **site_review** / **store_review** — Human inspects the built site before marking complete

Gates block the pipeline. Agents check gate status before executing. Rejection triggers partial re-run.

## Data Flow

```
Brief (JSON from GUI)
  → Director → Project + AgentTask rows in DB
  → Content Agent → GeneratedContent rows (status: draft)
  → Operator edits/approves in GUI
  → Media Agent → ProjectMedia rows + images on disk
  → Structure Agent → structure_plan merged into Project.pipeline_plan
  → Builder Agent → site created via platform API → ApprovalGate (site_review)
  → SEO Agent → schema markup pushed to platform, sitemap generated
  → QA Agent → qa_report JSON → gate created or blocked
  → Operator approves → Project.status = completed
```

## Error Handling

- Every agent wraps `run()` in `execute()` which catches exceptions, calls `mark_failed()`, and re-raises
- Celery retries up to 3 times with exponential backoff
- Claude rate limits trigger automatic retry (2/4/8s delays)
- Partial failures (e.g., 3 of 8 pages built) are recorded in `output_data` — operator can retry
- Pipeline never silently continues past a CRITICAL QA failure

## Security Model

- All platform credentials encrypted at rest (Fernet)
- API requires `X-API-Key` header on every request
- Client data never logged — only IDs and operation names
- Claude prompts never logged in full
- Prompt injection via client data contained by `<<<` delimiters in context_builder

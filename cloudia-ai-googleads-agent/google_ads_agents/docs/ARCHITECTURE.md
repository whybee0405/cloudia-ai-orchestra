# System Architecture

## Overview

The Google Ads Agent System is a multi-agent AI backend that manages Google Ads campaigns across multiple client accounts on behalf of CloudIA. It is a managed service — not a SaaS product. CloudIA operators and account managers interact with it via the approval queue API.

```
┌──────────────────────────────────────────────────────────┐
│                        main.py                           │
│               APScheduler (BlockingScheduler)            │
│   ┌──────────┐ ┌─────────┐ ┌──────────┐ ┌────────────┐  │
│   │ Auditor  │ │ Manager │ │ Reporter │ │KwrdScout   │  │
│   │  6h cron │ │10am cron│ │Mon 8am   │ │Sun 9am     │  │
│   └────┬─────┘ └────┬────┘ └────┬─────┘ └─────┬──────┘  │
│        │            │           │              │          │
│        └────────────┴───────────┴──────────────┘         │
│                          │                               │
│                   orchestrator.py                        │
│          (loops all agents across active accounts)       │
└──────────────────────┬───────────────────────────────────┘
                       │
         ┌─────────────┼──────────────┐
         ▼             ▼              ▼
   ┌───────────┐ ┌──────────┐ ┌─────────────┐
   │ Google    │ │ Anthropic│ │ PostgreSQL  │
   │ Ads API   │ │ Claude   │ │ Database    │
   │(read+write│ │ (analyse)│ │(state+queue)│
   └───────────┘ └──────────┘ └──────┬──────┘
                                      │
                              ┌───────▼──────┐
                              │  FastAPI     │
                              │  (port 8000) │
                              │  Approval UI │
                              └──────────────┘
                                      │
                              Human Reviewer
                              (approve/reject)
```

## Core Design Principles

1. **Observe and recommend. Humans approve.** No agent writes to Google Ads without a queue row having `status='approved'` first. The Executor only fires on explicit approval.

2. **Context-aware per client.** Every Claude call receives a rich client context string (baselines, KPI targets, industry benchmarks, seasonality, hard rules). Generic advice is architecturally impossible.

3. **Cheap to run.** All agents share one DB connection pool and one Anthropic client. APScheduler runs them inside the same process. No Kubernetes, no message queues.

## Data Flow — Auditor (typical)

```
APScheduler fires every 6h
  → orchestrator.run_auditor()
    → for each active account:
      → AuditorAgent.run(account)
        → BaseAgent checks calibration (skip if < 30 days old)
        → AdsClient.run_query(CAMPAIGN_PERFORMANCE_7D)
        → save_snapshot() → campaign_snapshots table
        → get_previous_snapshot() → diff deltas
        → _detect_anomalies() → list of triggered thresholds
        → for each anomaly:
          → build_client_context()
          → ClaudeClient.complete_json(AUDITOR_SYSTEM_PROMPT, data)
          → write AuditLog row
          → if severity HIGH/CRITICAL: send_alert() via SMTP
        → AgentRun row updated with token usage + summary
```

## Data Flow — Approval Queue (Manager/Creator/KeywordScout)

```
Agent generates decisions
  → write_queue_item() → approval_queue (status='pending')
  → email sent to alert_email with queue summary

Human reviews in dashboard (FastAPI)
  → POST /queue/{id}/approve (status='approved')

Human (or automated trigger) executes
  → POST /queue/{id}/execute
    → Executor.execute_approved(item, customer_id)
      → dispatches to action handler (bid/budget/pause/keyword/create)
      → Google Ads API mutate call
      → status='executed' or 'failed'
```

## Module Responsibilities

| Module | Responsibility |
|---|---|
| `config.py` | Single source of truth for all env vars and constants |
| `orchestrator.py` | Loops all agents across all `active` accounts |
| `main.py` | APScheduler jobs + FastAPI daemon thread startup |
| `agents/base.py` | Run logging, calibration guard, error capture |
| `agents/*.py` | Agent-specific logic only |
| `google_ads/client.py` | All Google Ads API calls |
| `google_ads/executor.py` | All Google Ads write mutations |
| `google_ads/campaign_builder.py` | Full campaign structure creation |
| `ai/claude.py` | All Anthropic API calls |
| `ai/context_builder.py` | Per-client context string assembly |
| `ai/prompts/*.py` | System prompt constants |
| `db/models.py` | ORM schema |
| `db/snapshots.py` | Snapshot CRUD |
| `db/queue.py` | Approval queue CRUD |
| `notifications/email.py` | SMTP email delivery |
| `api/` | FastAPI routes + schemas |

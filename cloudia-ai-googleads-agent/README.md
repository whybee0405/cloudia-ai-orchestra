# CloudIA Google Ads Agent

An AI-powered, human-in-the-loop Google Ads management system built for CloudIA. Agents continuously monitor, optimise, and report on Google Ads accounts — but nothing is ever executed without explicit human approval.

---

## How it works

The system runs as a single Docker container. Inside it:

- **APScheduler** drives four agents on a fixed schedule (SAST timezone)
- **FastAPI** serves the REST API and the web dashboard simultaneously
- **Claude (Anthropic)** is the intelligence layer — each agent sends structured data to Claude and receives decisions or narratives back
- **PostgreSQL** stores all accounts, agent decisions, audit logs, and queue items

Every action an agent recommends lands in the `approval_queue` with `status=pending`. A human must approve → execute it before anything touches Google Ads.

---

## Agent Hierarchy

```
╔══════════════════════════════════════════════════════════════════════╗
║                         HUMAN OPERATOR                              ║
║           (approves / rejects / executes via Dashboard)             ║
╚═══════════════════╦══════════════════════════╦═══════════════════════╝
                    │                          │ POST /campaigns/create
                    │                          │ (on-demand only)
                    ▼                          ▼
       ╔════════════════════╗     ╔══════════════════════╗
       ║   DIRECTOR AGENT   ║     ║    CREATOR AGENT     ║
       ║                    ║     ║                      ║
       ║  Scheduled entry   ║     ║  Builds campaign     ║
       ║  point. Delegates  ║     ║  structures from a   ║
       ║  to 3 Divisions,   ║     ║  human brief.        ║
       ║  synthesises a     ║     ║  → 1 approval_queue  ║
       ║  holistic report   ║     ║    item (pending)    ║
       ║  via Claude.       ║     ╚══════════════════════╝
       ╚═══╦═══════╦════╦═══╝
           │       │    │
    ┌───────┘       │    └────────────┐
    ▼               ▼                ▼
╔══════════╗  ╔═══════════════╗  ╔════════════╗
║ ANALYSIS ║  ║ OPTIMIZATION  ║  ║ REPORTING  ║
║ DIVISION ║  ║   DIVISION    ║  ║  DIVISION  ║
║          ║  ║               ║  ║            ║
║ Every    ║  ║ Daily 10:00   ║  ║ Mon 08:00  ║
║ 6 hours  ║  ║ SAST          ║  ║ SAST       ║
╚════╦═════╝  ╚═══╦══════╦════╝  ╚══════╦═════╝
     │             │      │             │
     ▼             ▼      ▼             ▼
╔══════════╗ ╔═══════╗ ╔════════╗ ╔══════════╗
║ AUDITOR  ║ ║MANAGER║ ║KEYWORD ║ ║ REPORTER ║
║          ║ ║       ║ ║ SCOUT  ║ ║          ║
║ Anomaly  ║ ║ Bid / ║ ║        ║ ║ Weekly   ║
║ detection║ ║budget ║ ║Keyword ║ ║ perf     ║
║          ║ ║optimise║ ║discov- ║ ║ report   ║
║ → audit_ ║ ║       ║ ║ery     ║ ║ via email║
║   log    ║ ║ → ap- ║ ║        ║ ║          ║
║ → agent_ ║ ║ proval║ ║ → ap-  ║ ║ → agent_ ║
║   runs   ║ ║ queue ║ ║ proval ║ ║   runs   ║
╚══════════╝ ╚═══════╝ ║ queue  ║ ╚══════════╝
                       ╚════════╝
```

> Manager and KeywordScout run **in parallel** (ThreadPoolExecutor) within the Optimization Division, one account at a time.

---

## Schedule

| Trigger | What runs |
|---|---|
| Every 6 hours | Auditor (anomaly detection) |
| Daily 10:00 SAST | Manager + KeywordScout (optimisation) |
| Monday 08:00 SAST | Reporter (weekly email summary) |
| `POST /campaigns/create` | Creator (on-demand, not scheduled) |

---

## Human-in-the-loop guarantee

```
Agent recommends action
        │
        ▼
approval_queue  (status = pending)
        │
        │  Human reviews in dashboard
        ▼
POST /queue/{id}/approve       → status = approved
        │
        │  Human triggers execution
        ▼
POST /queue/{id}/execute       → status = executed
                                 Google Ads API called
```

No agent can ever call the Google Ads API autonomously. Every decision requires two deliberate human actions.

---

## Data flow

```
Google Ads API
      │
      │  AdsClient.run_query()  (GAQL)
      ▼
  Agent logic
      │
      │  ClaudeClient.complete_json()
      ▼
  Claude (Anthropic)
      │
      │  JSON decisions / narrative
      ▼
  PostgreSQL
   ├── approval_queue   (decisions awaiting human approval)
   ├── audit_log        (anomalies detected by Auditor)
   ├── agent_runs       (run history, tokens used, errors)
   └── accounts         (registered MCC sub-accounts)
```

---

## Project structure

```
google_ads_agents/
├── agents/
│   ├── base.py           # BaseAgent — shared run loop, DB writes, skip logic
│   ├── auditor.py        # Anomaly detection (CTR, spend, CVR, CPA, QS)
│   ├── manager.py        # Bid & budget recommendations
│   ├── keyword_scout.py  # Keyword opportunity mining
│   ├── reporter.py       # Weekly performance narrative + email
│   ├── creator.py        # On-demand campaign builder from a brief
│   └── director.py       # Orchestrates divisions → holistic report
│
├── ai/
│   ├── claude.py         # Anthropic API wrapper (all Claude calls go here)
│   ├── context_builder.py
│   └── prompts/          # One prompt file per agent
│
├── api/
│   ├── app.py            # FastAPI app factory, CORS, ApiKeyMiddleware
│   ├── routes.py         # All REST endpoints
│   └── schemas.py        # Pydantic request/response models
│
├── db/
│   ├── models.py         # SQLAlchemy ORM models
│   ├── session.py        # Engine + session factory
│   ├── queue.py          # approval_queue helpers
│   └── snapshots.py      # Campaign snapshot helpers
│
├── google_ads/
│   ├── client.py         # AdsClient (GAQL wrapper around google-ads-python)
│   ├── executor.py       # Executes approved queue items against the API
│   ├── queries.py        # All GAQL query strings
│   └── campaign_builder.py
│
├── notifications/
│   └── email.py          # SMTP email sender (used by Reporter)
│
├── frontend/
│   └── index.html        # Single-page dashboard (served at /app/)
│
├── tests/                # 128 tests across 16 suites
├── orchestrator.py       # Thin wrapper used by main.py scheduler jobs
├── main.py               # Entry point: uvicorn thread + APScheduler
├── config.py             # All env vars and app constants
└── requirements.txt
```

---

## API endpoints

| Method | Path | Description |
|---|---|---|
| `GET` | `/health` | Liveness check |
| `GET` | `/accounts` | List all registered accounts |
| `GET` | `/queue` | List pending approval items |
| `GET` | `/queue/{id}` | Get a single queue item |
| `POST` | `/queue/{id}/approve` | Approve a pending item |
| `POST` | `/queue/{id}/reject` | Reject a pending item |
| `POST` | `/queue/{id}/execute` | Execute an approved item against Google Ads |
| `POST` | `/campaigns/create` | Trigger Creator agent from a campaign brief |
| `GET` | `/audit` | List audit log entries |
| `POST` | `/accounts/{id}/baseline` | Manually set account baseline metrics |

Interactive docs: `http://your-host:8020/docs`

---

## Getting started

### 1. Copy and fill in the environment file

```bash
cp google_ads_agents/.env.example google_ads_agents/.env
```

Required values:

| Variable | Where to get it |
|---|---|
| `GOOGLE_ADS_DEVELOPER_TOKEN` | Google Ads API Center |
| `GOOGLE_ADS_CLIENT_ID` | Google Cloud OAuth credentials |
| `GOOGLE_ADS_CLIENT_SECRET` | Google Cloud OAuth credentials |
| `GOOGLE_ADS_REFRESH_TOKEN` | `google-auth-oauthlib` flow |
| `GOOGLE_ADS_LOGIN_CUSTOMER_ID` | Your MCC account ID (no dashes) |
| `ANTHROPIC_API_KEY` | console.anthropic.com |
| `DATABASE_URL` | `postgresql://user:pass@host:5432/google_ads_agents` |
| `API_SECRET_KEY` | Any secret string — required on all POST/PUT/DELETE |

### 2. Create the database

```sql
CREATE DATABASE google_ads_agents;
```

### 3. Deploy

```bash
# Production (joins existing cloudia-erp_default network, port 8020)
./deploy.sh

# Development (isolated network, hot-reload, local postgres on port 5433)
./deploy.sh --dev
```

The deploy script: validates `.env`, stops old containers, rebuilds, runs Alembic migrations, starts the container, and checks `/health`.

### 4. Access

| URL | What |
|---|---|
| `http://dashboard.cloudia.co.za:8020/` | Dashboard (frontend) |
| `http://dashboard.cloudia.co.za:8020/docs` | Swagger API docs |
| `http://dashboard.cloudia.co.za:8020/health` | Health check |

---

## Development

```bash
cd google_ads_agents
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt

# Run tests
pytest tests/ -v

# Run locally (no Docker)
python main.py
```

### Authentication

All state-mutating endpoints (`POST`, `PUT`, `PATCH`, `DELETE`) require the `X-API-Key` header when `API_SECRET_KEY` is set. `GET` requests and `/health` are always open.

```bash
curl -X POST http://localhost:8000/queue/1/approve \
  -H "X-API-Key: your-secret-key" \
  -H "Content-Type: application/json"
```

---

## Account lifecycle

```
calibrating  →  active  →  paused  →  churned
     │                        │
     │  30-day window to      │  agents skip this
     │  build baseline        │  account entirely
     │  metrics               │
     └────────────────────────┘
          agents skip during calibration too
```

Anomaly detection thresholds scale by the account's `budget_sensitivity`:

| Sensitivity | CTR drop | Spend spike | CPA spike |
|---|---|---|---|
| `aggressive` | 40% | 60% | 60% |
| `moderate` | 30% | 40% | 40% |
| `conservative` | 20% | 25% | 25% |

---

## Tech stack

| Layer | Technology |
|---|---|
| Language | Python 3.12 |
| API framework | FastAPI + uvicorn |
| Scheduler | APScheduler 3.x (SAST timezone) |
| AI | Anthropic Claude (Sonnet 4) |
| Google Ads | `google-ads` Python client library (GAQL) |
| Database | PostgreSQL 15 + SQLAlchemy 2.0 + Alembic |
| Container | Docker + Docker Compose |
| Tests | pytest — 128 tests, 16 suites |

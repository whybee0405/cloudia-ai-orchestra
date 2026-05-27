# Google Ads Agent System

Multi-agent AI system that creates, manages, audits, and reports on Google Ads campaigns across multiple client accounts. Built for CloudIA — a South African digital agency.

**Principle:** Agents observe and recommend. Humans approve. No agent auto-executes spend decisions.

---

## Prerequisites

- Python 3.11+
- PostgreSQL 15
- Google Ads API access (developer token + OAuth credentials)
- Anthropic API key

---

## Setup

### 1. Clone and install dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure environment

```bash
cp .env.example .env
# Edit .env and fill in all values
```

### 3. Create the database

```bash
createdb google_ads_agents
```

### 4. Run migrations

```bash
cd google_ads_agents
alembic upgrade head
```

### 5. Start the API server

```bash
uvicorn api.app:app --host 0.0.0.0 --port 8000 --reload
```

### 6. Start the scheduler

```bash
python main.py
```

---

## Agent Schedule

| Agent | Schedule | Purpose |
|---|---|---|
| Auditor | Every 6 hours | Anomaly detection |
| Manager | Daily 10:00am | Bid & budget optimisation |
| Reporter | Monday 08:00am | Weekly performance report |
| Keyword Scout | Sunday 09:00am | New keyword opportunities |
| Creator | On demand (API) | Campaign creation from brief |

---

## API Endpoints

- `GET /queue` — list pending approval items
- `POST /queue/{id}/approve` — approve a decision
- `POST /queue/{id}/reject` — reject a decision
- `POST /campaigns/create` — submit a campaign creation brief
- `GET /accounts` — list all active accounts

---

## Adding a New Client

See `docs/ONBOARDING.md` for the full onboarding checklist.

---

## Running Tests

```bash
pytest tests/ -v
```

---

## Project Structure

```
google_ads_agents/
├── main.py              # Scheduler entry point
├── config.py            # All env vars + constants
├── orchestrator.py      # Loops agents across all active accounts
├── agents/              # All AI agents
├── google_ads/          # Google Ads API layer
├── ai/                  # Claude client + context builder
├── db/                  # Models, sessions, migrations
├── api/                 # FastAPI approval queue UI
├── notifications/       # SMTP email
└── tests/               # pytest suite
```

# Google Ads Agent System — Master Project Prompt

# For use with: Claude Code / Codex / GitHub Copilot (Sonnet)

# Version: 1.0 | Owner: CloudIA

-----

## HOW TO USE THIS FILE

This is the single source of truth for building the Google Ads Agent System.
At the start of EVERY coding session, paste this entire file as your first message.
At the end of EVERY session, update `PROGRESS.md` (defined below) before closing.
The next model picks up from `PROGRESS.md` + this file. Nothing is lost.

-----

## 1. PROJECT BRIEF

**Company:** CloudIA — a digital agency (South Africa) serving SME clients.

**What we are building:**
A multi-agent AI system that creates, manages, audits, and reports on Google Ads
campaigns across multiple client accounts. It is a backend managed service — not
a SaaS product. CloudIA operates it on behalf of clients.

**Core principles:**

- Agents observe and recommend. Humans approve. No agent auto-executes spend decisions.
- Every agent call is context-aware per client — no generic advice.
- System must be cheap to run (~R200–400/month infrastructure at 15 clients).
- Code must be clean, documented, and resumable by any AI coding assistant.

-----

## 2. TECH STACK (exact — do not substitute)

|Layer         |Tool                          |Notes                     |
|--------------|------------------------------|--------------------------|
|Language      |Python 3.11+                  |Type hints everywhere     |
|Google Ads    |google-ads==24.1.0            |Official Python client    |
|AI            |anthropic==0.26.0             |Claude Sonnet only        |
|Database      |PostgreSQL 15 + SQLAlchemy 2.0|Alembic for migrations    |
|Scheduler     |APScheduler 3.10              |BlockingScheduler         |
|API           |FastAPI 0.111 + Uvicorn       |Approval queue UI         |
|Env management|python-dotenv                 |.env file                 |
|Notifications |SMTP (smtplib)                |No third-party email SDK  |
|Testing       |pytest                        |All agents must have tests|
|Linting       |ruff                          |Enforce on all files      |

-----

## 3. FOLDER STRUCTURE (complete — build exactly this)

```
google_ads_agents/
├── main.py                        # Scheduler entry point
├── config.py                      # All env vars + constants
├── orchestrator.py                # Loops agents across all active accounts
│
├── agents/
│   ├── __init__.py
│   ├── base.py                    # BaseAgent class all agents inherit
│   ├── auditor.py                 # Anomaly detection — runs every 6h
│   ├── manager.py                 # Bid/budget decisions — runs daily 10am
│   ├── reporter.py                # Performance reports — runs Monday 8am
│   ├── keyword_scout.py           # Keyword opportunities — runs Sunday 9am
│   └── creator.py                 # Campaign creation — on demand only
│
├── google_ads/
│   ├── __init__.py
│   ├── client.py                  # GoogleAdsClient wrapper
│   ├── queries.py                 # All GAQL query strings
│   └── executor.py                # Applies approved actions to Google Ads API
│
├── ai/
│   ├── __init__.py
│   ├── claude.py                  # Anthropic API wrapper
│   ├── context_builder.py         # Builds per-client context string for prompts
│   └── prompts/
│       ├── __init__.py
│       ├── auditor.py             # Auditor system prompt
│       ├── manager.py             # Manager system prompt
│       ├── reporter.py            # Reporter system prompt
│       ├── keyword_scout.py       # Keyword scout system prompt
│       └── creator.py             # Creator system prompt
│
├── db/
│   ├── __init__.py
│   ├── models.py                  # All SQLAlchemy models
│   ├── session.py                 # DB session management
│   ├── snapshots.py               # Campaign snapshot read/write logic
│   ├── queue.py                   # Approval queue read/write logic
│   └── migrations/                # Alembic migration files
│
├── api/
│   ├── __init__.py
│   ├── app.py                     # FastAPI app instance
│   ├── routes.py                  # All API routes
│   └── schemas.py                 # Pydantic request/response schemas
│
├── notifications/
│   ├── __init__.py
│   └── email.py                   # SMTP email delivery
│
├── tests/
│   ├── conftest.py
│   ├── test_auditor.py
│   ├── test_manager.py
│   ├── test_context_builder.py
│   └── test_executor.py
│
├── docs/
│   ├── ARCHITECTURE.md            # Full system architecture diagram + explanation
│   ├── AGENT_SPECS.md             # Each agent: purpose, inputs, outputs, schedule
│   ├── DATABASE.md                # Full schema with field explanations
│   ├── ONBOARDING.md              # How to add a new client account
│   └── DECISIONS.md               # Architectural decisions log
│
├── PROGRESS.md                    # SESSION HANDOFF FILE — updated every session
├── .env.example                   # All required env vars, no values
├── requirements.txt
├── alembic.ini
└── README.md
```

-----

## 4. DATABASE SCHEMA (exact — implement in db/models.py)

### accounts

The master client registry. Every other table references this.

```sql
id                      SERIAL PRIMARY KEY
client_name             VARCHAR(255) NOT NULL
customer_id             VARCHAR(50) NOT NULL UNIQUE   -- Google Ads customer ID
mcc_id                  VARCHAR(50) NOT NULL           -- Your MCC account ID
status                  VARCHAR(20) DEFAULT 'calibrating'
                        -- calibrating | active | paused | churned

-- Business context (used in every prompt)
industry                VARCHAR(100)   -- 'automotive_parts' | 'dental' | 'legal' | etc
business_type           VARCHAR(50)    -- 'local_service' | 'ecommerce' | 'lead_gen'
geo_focus               VARCHAR(20)    -- 'local' | 'regional' | 'national'
avg_transaction_value   NUMERIC(10,2)  -- ZAR
sales_cycle_days        INTEGER

-- Goal hierarchy
primary_kpi             VARCHAR(20)    -- 'CPL' | 'ROAS' | 'CPA' | 'CTR'
primary_kpi_target      NUMERIC(10,2)
secondary_kpi           VARCHAR(20)
secondary_kpi_target    NUMERIC(10,2)

-- Budget context
monthly_ad_spend        NUMERIC(10,2)  -- client's actual ad budget (ZAR)
budget_sensitivity      VARCHAR(20)    -- 'aggressive' | 'moderate' | 'conservative'
min_daily_budget        NUMERIC(10,2)  -- hard floor — never go below

-- Baselines (set after 30-day calibration)
baseline_ctr            NUMERIC(6,4)
baseline_cvr            NUMERIC(6,4)
baseline_cpc            NUMERIC(10,2)
baseline_cpa            NUMERIC(10,2)
baseline_roas           NUMERIC(8,2)
baseline_set_at         TIMESTAMP

-- Seasonality
peak_months             JSONB          -- [1, 3, 11]
slow_months             JSONB          -- [6, 7]

-- Rules engine
custom_rules            JSONB
/*
  Example custom_rules:
  {
    "never_pause_brand_campaign": true,
    "max_cpc_increase_pct": 20,
    "blackout_dates": ["2025-12-25"],
    "always_include_keywords": ["brand term xyz"],
    "competitor_bidding_allowed": false,
    "max_daily_spend_increase_pct": 15
  }
*/

-- Admin
alert_email             VARCHAR(255)
report_email            VARCHAR(255)
onboarded_at            TIMESTAMP DEFAULT NOW()
notes                   TEXT
```

### campaign_snapshots

Point-in-time campaign metrics. Auditor diffs these.

```sql
id                  SERIAL PRIMARY KEY
account_id          INTEGER REFERENCES accounts(id)
campaign_id         VARCHAR(50) NOT NULL
campaign_name       VARCHAR(255)
snapshot_time       TIMESTAMP NOT NULL
impressions         BIGINT
clicks              BIGINT
cost_micros         BIGINT          -- divide by 1,000,000 for ZAR
conversions         NUMERIC(10,2)
ctr                 NUMERIC(6,4)
avg_cpc_micros      BIGINT
conversion_rate     NUMERIC(6,4)
cost_per_conversion NUMERIC(10,2)
roas                NUMERIC(8,2)
budget_micros       BIGINT
status              VARCHAR(50)
raw_json            JSONB           -- full API response stored for reference
```

### audit_log

Every anomaly detected. Persisted even if no action taken.

```sql
id                  SERIAL PRIMARY KEY
account_id          INTEGER REFERENCES accounts(id)
run_time            TIMESTAMP NOT NULL
campaign_id         VARCHAR(50)
anomaly_type        VARCHAR(100)    -- 'ctr_drop' | 'spend_spike' | 'cvr_collapse' | etc
severity            VARCHAR(20)     -- 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL'
diagnosis           TEXT            -- Claude's plain English explanation
recommended_action  TEXT            -- Claude's recommendation
delta_value         NUMERIC(10,4)   -- the actual change that triggered this
threshold_used      NUMERIC(10,4)   -- what threshold was set
acknowledged        BOOLEAN DEFAULT FALSE
acknowledged_at     TIMESTAMP
acknowledged_by     VARCHAR(100)
```

### approval_queue

All agent decisions waiting for human review. NOTHING executes without a row here
being set to ‘approved’.

```sql
id                  SERIAL PRIMARY KEY
account_id          INTEGER REFERENCES accounts(id)
agent_name          VARCHAR(50)     -- 'manager' | 'keyword_scout' | 'creator'
created_at          TIMESTAMP DEFAULT NOW()
action_type         VARCHAR(100)    -- 'increase_bid' | 'pause_adgroup' | 'add_negative' | etc
action_payload      JSONB           -- exact parameters passed to executor
reasoning           TEXT            -- Claude's explanation of why
status              VARCHAR(20) DEFAULT 'pending'
                    -- pending | approved | rejected | executed | failed
reviewed_at         TIMESTAMP
reviewed_by         VARCHAR(100)
executed_at         TIMESTAMP
execution_result    JSONB
failure_reason      TEXT
```

### industry_benchmarks

Reference data injected into every prompt alongside client baseline.

```sql
id                  SERIAL PRIMARY KEY
industry            VARCHAR(100) NOT NULL
avg_ctr             NUMERIC(6,4)
avg_cvr             NUMERIC(6,4)
avg_cpc_zar         NUMERIC(10,2)
avg_cpa_zar         NUMERIC(10,2)
good_quality_score  INTEGER DEFAULT 7
source              VARCHAR(100)    -- 'wordstream_2024' | 'internal'
updated_at          TIMESTAMP
notes               TEXT
```

### agent_runs

Every agent execution logged for debugging and cost tracking.

```sql
id                  SERIAL PRIMARY KEY
agent_name          VARCHAR(50)
account_id          INTEGER REFERENCES accounts(id)
started_at          TIMESTAMP
completed_at        TIMESTAMP
status              VARCHAR(20)     -- 'running' | 'success' | 'failed' | 'skipped'
tokens_used         INTEGER
cost_usd            NUMERIC(8,6)
decisions_generated INTEGER
anomalies_found     INTEGER
summary             TEXT
error               TEXT
```

-----

## 5. AGENT SPECIFICATIONS

### BaseAgent (agents/base.py)

All agents inherit this. Handles run logging, error catching, calibration check.

```python
class BaseAgent:
    name: str  # override in subclass

    def __init__(self, ads_client, claude_client, db_session):
        self.ads = ads_client
        self.claude = claude_client
        self.db = db_session

    def run(self, account: Account) -> AgentRunResult:
        # 1. Log start to agent_runs
        # 2. Check if account is still in calibration — if so, skip + log 'skipped'
        # 3. Call self.execute(account)
        # 4. Log completion + token usage
        # 5. On exception: log failure, re-raise

    def execute(self, account: Account) -> AgentRunResult:
        raise NotImplementedError

    def is_calibrating(self, account: Account) -> bool:
        if account.baseline_set_at is None:
            return True
        return (datetime.utcnow() - account.baseline_set_at).days < 30
```

### Auditor (agents/auditor.py)

**Schedule:** every 6 hours
**Purpose:** detect anomalies by diffing current metrics against last snapshot

Flow:

1. Pull campaign metrics via GAQL (CAMPAIGN_PERFORMANCE_7D query)
1. Store new snapshot to campaign_snapshots
1. Load previous snapshot from DB
1. Calculate deltas per metric
1. Load dynamic thresholds from account profile (conservative/moderate/aggressive)
1. For each metric exceeding threshold: send context to Claude
1. Claude returns: { anomaly_type, severity, diagnosis, recommended_action }
1. Write to audit_log
1. If severity = CRITICAL or HIGH: trigger email notification immediately

Anomaly types to detect:

- ctr_drop (> threshold % decline vs previous snapshot)
- spend_spike (> threshold % above daily average)
- cvr_collapse (conversion rate drops sharply)
- cpa_spike (cost per acquisition exceeds target by > threshold)
- zero_conversions (spend occurring, no conversions, over N days)
- ad_disapproval (disapproved ads detected)
- budget_exhaustion (campaign hitting budget cap before noon)
- quality_score_drop (avg quality score drops below good_quality_score)

### Manager (agents/manager.py)

**Schedule:** daily at 10:00am
**Purpose:** recommend bid and budget optimisations

Flow:

1. Pull 7-day rolling campaign + ad group metrics (CAMPAIGN_PERFORMANCE_7D)
1. Pull current bids per ad group (ADGROUP_BIDS query)
1. Pull current budgets per campaign
1. Build full client context via context_builder.py
1. Send to Claude: metrics + current settings + client context
1. Claude returns structured JSON array of decisions:
   [{ action_type, target_id, current_value, recommended_value, reasoning }]
1. Validate decisions against custom_rules (reject any violating hard rules)
1. Write valid decisions to approval_queue (status: pending)
1. Send email notification to alert_email with queue summary

Action types the manager can recommend:

- increase_bid / decrease_bid (ad group level)
- increase_budget / decrease_budget (campaign level)
- pause_adgroup (with mandatory reasoning)
- pause_campaign (CRITICAL: always flags for immediate human review)
- enable_adgroup
- adjust_bidding_strategy

### Reporter (agents/reporter.py)

**Schedule:** every Monday at 08:00am
**Purpose:** generate plain English performance report per client

Flow:

1. Pull date range metrics (last 7 days and last 30 days) via GAQL
1. Pull conversion data and ROAS
1. Compare against client baseline and KPI targets
1. Send raw data to Claude with client context
1. Claude returns structured report:
   { executive_summary, key_wins, areas_of_concern, top_campaigns, recommendations }
1. Format into HTML email
1. Send to report_email

### Keyword Scout (agents/keyword_scout.py)

**Schedule:** every Sunday at 09:00am
**Purpose:** identify new keywords and negatives from search terms data

Flow:

1. Pull Search Terms report (last 30 days, impressions > 10) via GAQL
1. Pull existing keyword list with match types
1. Send both to Claude with client context
1. Claude returns:
   { new_keyword_opportunities, negatives_to_add, match_type_adjustments }
1. Write each recommendation as a row in approval_queue
1. Human reviews and approves per recommendation

### Creator (agents/creator.py)

**Schedule:** on demand only — triggered via API endpoint POST /campaigns/create
**Purpose:** generate full campaign structure from a brief

Input (via API):

```json
{
  "account_id": 1,
  "brief": {
    "goal": "generate leads for brake pad replacement service",
    "product_service": "brake pad replacement",
    "audience_description": "car owners in Johannesburg needing brake service",
    "budget_daily_zar": 150,
    "geo_targets": ["Johannesburg", "Sandton", "Randburg"],
    "languages": ["English"],
    "landing_page_url": "https://example.co.za/brakes"
  }
}
```

Flow:

1. Receive brief + account_id
1. Load full account profile + benchmarks
1. Build context + brief
1. Send to Claude
1. Claude returns full campaign structure JSON:
   { campaign_name, campaign_settings, ad_groups: [{ name, keywords, ads }] }
1. Write to approval_queue (status: pending) — do NOT create in Google Ads yet
1. Return structure to caller for review
1. On approval: executor.create_campaign(structure, customer_id)

-----

## 6. GAQL QUERIES (google_ads/queries.py)

All queries stored as constants. Use named constants only — no inline GAQL.

```python
CAMPAIGN_PERFORMANCE_7D = """
SELECT
  campaign.id, campaign.name, campaign.status,
  campaign_budget.amount_micros,
  metrics.impressions, metrics.clicks,
  metrics.cost_micros, metrics.conversions,
  metrics.ctr, metrics.average_cpc,
  metrics.cost_per_conversion, metrics.conversions_from_interactions_rate,
  metrics.search_impression_share
FROM campaign
WHERE segments.date DURING LAST_7_DAYS
  AND campaign.status != 'REMOVED'
ORDER BY metrics.cost_micros DESC
"""

CAMPAIGN_PERFORMANCE_30D = """
SELECT
  campaign.id, campaign.name,
  metrics.impressions, metrics.clicks,
  metrics.cost_micros, metrics.conversions,
  metrics.ctr, metrics.average_cpc,
  metrics.cost_per_conversion, metrics.roas
FROM campaign
WHERE segments.date DURING LAST_30_DAYS
  AND campaign.status != 'REMOVED'
"""

ADGROUP_BIDS = """
SELECT
  ad_group.id, ad_group.name, ad_group.status,
  ad_group.cpc_bid_micros,
  campaign.id, campaign.name,
  metrics.impressions, metrics.clicks,
  metrics.ctr, metrics.conversions,
  metrics.average_cpc
FROM ad_group
WHERE segments.date DURING LAST_7_DAYS
  AND ad_group.status != 'REMOVED'
"""

SEARCH_TERMS_30D = """
SELECT
  search_term_view.search_term,
  search_term_view.status,
  campaign.name, ad_group.name,
  metrics.impressions, metrics.clicks,
  metrics.conversions, metrics.cost_micros,
  metrics.ctr, metrics.average_cpc
FROM search_term_view
WHERE segments.date DURING LAST_30_DAYS
  AND metrics.impressions > 10
ORDER BY metrics.clicks DESC
"""

KEYWORD_PERFORMANCE_30D = """
SELECT
  ad_group_criterion.keyword.text,
  ad_group_criterion.keyword.match_type,
  ad_group_criterion.quality_info.quality_score,
  ad_group_criterion.status,
  campaign.name, ad_group.name,
  metrics.impressions, metrics.clicks,
  metrics.ctr, metrics.average_cpc,
  metrics.conversions, metrics.cost_per_conversion
FROM keyword_view
WHERE segments.date DURING LAST_30_DAYS
  AND ad_group_criterion.status != 'REMOVED'
ORDER BY metrics.cost_micros DESC
"""
```

-----

## 7. CONTEXT BUILDER (ai/context_builder.py)

This is the most important file in the system.
Every Claude call passes through this. It injects client-specific intelligence.

```python
def build_client_context(account: Account, benchmarks: IndustryBenchmark) -> str:
    current_month = datetime.utcnow().month
    is_peak = current_month in (account.peak_months or [])
    is_slow = current_month in (account.slow_months or [])
    season_label = "PEAK SEASON" if is_peak else ("SLOW SEASON" if is_slow else "NORMAL PERIOD")

    return f"""
=== CLIENT CONTEXT ===
Client: {account.client_name}
Industry: {account.industry}
Business type: {account.business_type}
Geographic focus: {account.geo_focus}
Average transaction value: R{account.avg_transaction_value}
Sales cycle: {account.sales_cycle_days} days

=== GOALS ===
Primary KPI: {account.primary_kpi} — target: {account.primary_kpi_target}
Secondary KPI: {account.secondary_kpi} — target: {account.secondary_kpi_target}
Monthly ad spend budget: R{account.monthly_ad_spend}
Budget sensitivity: {account.budget_sensitivity}
Minimum daily budget floor: R{account.min_daily_budget}

=== CLIENT BASELINE (established over first 30 days) ===
CTR: {account.baseline_ctr}
CVR: {account.baseline_cvr}
CPC: R{account.baseline_cpc}
CPA: R{account.baseline_cpa}
ROAS: {account.baseline_roas}

=== INDUSTRY BENCHMARKS ({account.industry}) ===
Average CTR: {benchmarks.avg_ctr}
Average CVR: {benchmarks.avg_cvr}
Average CPC: R{benchmarks.avg_cpc_zar}
Average CPA: R{benchmarks.avg_cpa_zar}
Good quality score threshold: {benchmarks.good_quality_score}
Source: {benchmarks.source}

=== SEASONALITY ===
Current period: {season_label} (Month {current_month})
Peak months: {account.peak_months}
Slow months: {account.slow_months}

=== HARD RULES — YOU MUST FOLLOW THESE WITHOUT EXCEPTION ===
{json.dumps(account.custom_rules or {}, indent=2)}

=== YOUR ROLE ===
You are a senior Google Ads strategist operating as part of an automated
management system for CloudIA, a South African digital agency.
All your recommendations must be:
1. Specific to THIS client's industry, goals, and baseline — not generic
2. Proportional to their budget sensitivity level
3. Compliant with every hard rule listed above
4. Expressed in South African Rand (ZAR)
5. Structured as JSON where action output is required
Do not hallucinate metrics. If data is missing, say so.
"""
```

-----

## 8. ENVIRONMENT VARIABLES (.env.example)

```env
# Google Ads
GOOGLE_ADS_DEVELOPER_TOKEN=
GOOGLE_ADS_CLIENT_ID=
GOOGLE_ADS_CLIENT_SECRET=
GOOGLE_ADS_REFRESH_TOKEN=
GOOGLE_ADS_LOGIN_CUSTOMER_ID=     # Your MCC account ID

# Anthropic
ANTHROPIC_API_KEY=
ANTHROPIC_MODEL=claude-sonnet-4-20250514
ANTHROPIC_MAX_TOKENS=1500

# Database
DATABASE_URL=postgresql://user:password@host:5432/google_ads_agents

# API
API_HOST=0.0.0.0
API_PORT=8000
API_SECRET_KEY=                   # For route protection

# Notifications
SMTP_HOST=
SMTP_PORT=587
SMTP_USER=
SMTP_PASSWORD=
NOTIFICATION_FROM_EMAIL=
CLOUDIA_ALERT_EMAIL=              # Your internal alert address

# App
ENVIRONMENT=development           # development | production
LOG_LEVEL=INFO
```

-----

## 9. CODING STANDARDS

- Type hints on every function signature
- Docstring on every class and public method
- No hardcoded strings — use config.py constants
- All DB operations go through SQLAlchemy ORM — no raw SQL except migrations
- All Google Ads API calls go through google_ads/client.py — never call API directly from agents
- All Claude calls go through ai/claude.py — never call Anthropic directly from agents
- Every agent must have at least one pytest test in tests/
- Log every significant action with Python logging (not print statements)
- Costs in ZAR displayed as human readable — micros converted immediately on ingestion

-----

## 10. BUILD ORDER (strict — do not deviate)

Complete each phase fully before starting the next.
Mark each item in PROGRESS.md as you complete it.

### Phase 1 — Foundation

- [ ] Project folder structure created
- [ ] requirements.txt populated
- [ ] .env.example created
- [ ] config.py with all constants
- [ ] db/models.py — all models defined
- [ ] db/session.py — session factory
- [ ] Alembic configured + initial migration runs clean
- [ ] README.md — setup instructions

### Phase 2 — Google Ads Layer

- [ ] google_ads/client.py — AdsClient wrapper
- [ ] google_ads/queries.py — all GAQL constants
- [ ] google_ads/executor.py — stub (no live execution yet)
- [ ] Test: raw GAQL query returns data from a test account

### Phase 3 — AI Layer

- [ ] ai/claude.py — ClaudeClient wrapper
- [ ] ai/context_builder.py — build_client_context()
- [ ] ai/prompts/ — all 5 prompt files stubbed

### Phase 4 — Auditor (first agent)

- [ ] agents/base.py — BaseAgent
- [ ] agents/auditor.py — full implementation
- [ ] db/snapshots.py — snapshot read/write
- [ ] tests/test_auditor.py — passing
- [ ] notifications/email.py — SMTP send

### Phase 5 — Reporter

- [ ] agents/reporter.py — full implementation
- [ ] tests/test_reporter.py — passing

### Phase 6 — Manager + Approval Queue

- [ ] agents/manager.py — full implementation
- [ ] db/queue.py — queue read/write
- [ ] google_ads/executor.py — real execution logic
- [ ] api/app.py + api/routes.py + api/schemas.py
- [ ] tests/test_manager.py — passing

### Phase 7 — Keyword Scout

- [ ] agents/keyword_scout.py — full implementation
- [ ] tests/test_keyword_scout.py — passing

### Phase 8 — Creator

- [ ] agents/creator.py — full implementation
- [ ] API endpoint: POST /campaigns/create
- [ ] tests/test_creator.py — passing

### Phase 9 — Orchestrator + Scheduler

- [ ] orchestrator.py — loops all agents across all accounts
- [ ] main.py — APScheduler with all jobs
- [ ] End-to-end dry run against test account

### Phase 10 — Documentation

- [ ] docs/ARCHITECTURE.md
- [ ] docs/AGENT_SPECS.md
- [ ] docs/DATABASE.md
- [ ] docs/ONBOARDING.md
- [ ] docs/DECISIONS.md

-----

## 11. SESSION HANDOFF PROTOCOL

At the END of every coding session, the active model MUST update PROGRESS.md
with the following format. This is mandatory — it is how the next model
picks up without losing context.

```markdown
# PROGRESS.md

## Last Updated
[ISO timestamp] by [model name e.g. claude-sonnet / codex / copilot]

## Current Phase
Phase X — [Phase Name]

## Completed Items (tick from build order above)
- [x] item one
- [x] item two

## In Progress
- [ ] item currently being worked on
  - Sub-task done: ...
  - Sub-task remaining: ...

## Decisions Made This Session
- Why we chose X over Y: [reason]
- Deviation from spec (if any): [what changed and why]

## Blockers / Open Questions
- [any unresolved issues]

## Files Modified This Session
- path/to/file.py — [what changed]
- path/to/other.py — [what changed]

## Next Session Should Start With
[Exact instruction for the next model — be specific]
```

-----

## 12. CONTEXT FOR NEXT MODEL

When starting a new session, the next model should:

1. Read this entire MASTER_PROMPT.md first
1. Read PROGRESS.md for current state
1. Run `git status` or list modified files to verify state
1. Read any files listed under “Files Modified This Session”
1. Continue from “Next Session Should Start With”

Do not re-architect. Do not rename things. Follow the spec.
If you identify a genuine problem with the spec, document it in
PROGRESS.md under “Decisions Made” before deviating.

-----

*End of MASTER_PROMPT.md*
*This file does not change between sessions. Only PROGRESS.md changes.*
# Agent Specifications

Each agent inherits from `BaseAgent` which handles run logging, calibration checks, and error capture.

---

## BaseAgent (`agents/base.py`)

**Purpose:** Shared scaffolding for all agents.

**Key behaviour:**
- Logs every run to `agent_runs` table (start, end, tokens, cost, status)
- Checks `is_calibrating()` — skips account if `baseline_set_at` is None or < 30 days ago
- Catches all exceptions, marks run as `failed`, re-raises

---

## Auditor (`agents/auditor.py`)

**Schedule:** Every 6 hours  
**Purpose:** Detect campaign anomalies by diffing current metrics against previous snapshots.

**Inputs:**
- `CAMPAIGN_PERFORMANCE_7D` GAQL query
- Previous `campaign_snapshots` rows from DB

**Outputs:**
- New `campaign_snapshots` rows
- `audit_log` rows for every anomaly detected
- SMTP alert email for HIGH/CRITICAL severities

**Anomaly types detected:**

| Type | Trigger |
|---|---|
| `ctr_drop` | CTR declines > threshold % vs previous snapshot |
| `spend_spike` | Cost > threshold % above previous snapshot |
| `cvr_collapse` | Conversion rate drops > threshold % |
| `cpa_spike` | CPA exceeds previous by > threshold % |
| `zero_conversions` | Clicks > 20, spend > 0, conversions = 0 |

**Thresholds** (from `config.ANOMALY_THRESHOLDS` by `budget_sensitivity`):

| Sensitivity | CTR drop | Spend spike | CVR collapse | CPA spike |
|---|---|---|---|---|
| aggressive | 40% | 60% | 40% | 60% |
| moderate | 30% | 40% | 30% | 40% |
| conservative | 20% | 25% | 20% | 25% |

---

## Manager (`agents/manager.py`)

**Schedule:** Daily at 10:00am  
**Purpose:** Recommend bid and budget optimisations.

**Inputs:**
- `CAMPAIGN_PERFORMANCE_7D` (campaign metrics)
- `ADGROUP_BIDS` (current bids per ad group)
- Client context from `build_client_context()`

**Outputs:**
- `approval_queue` rows (status: `pending`) for each valid decision
- SMTP summary email to `alert_email`

**Action types:**

| Action | Description |
|---|---|
| `increase_bid` | Raise ad group CPC bid |
| `decrease_bid` | Lower ad group CPC bid |
| `increase_budget` | Raise campaign daily budget |
| `decrease_budget` | Lower campaign daily budget |
| `pause_adgroup` | Pause underperforming ad group |
| `enable_adgroup` | Re-enable a paused ad group |
| `pause_campaign` | CRITICAL — flags for immediate human review |

**Custom rules enforcement:**
- `never_pause_brand_campaign: true` → blocks all `pause_campaign` decisions
- `max_cpc_increase_pct` → blocks `increase_bid` if increase exceeds the cap
- `max_daily_spend_increase_pct` → blocks `increase_budget` if increase exceeds the cap

---

## Reporter (`agents/reporter.py`)

**Schedule:** Every Monday at 08:00am  
**Purpose:** Generate plain-English weekly performance reports.

**Inputs:**
- `CAMPAIGN_PERFORMANCE_7D` (last 7 days)
- `CAMPAIGN_PERFORMANCE_30D` (last 30 days)
- Client context

**Outputs:**
- HTML email to `report_email` containing:
  - Executive summary
  - Key wins
  - Areas of concern
  - Top campaigns table
  - Recommendations

---

## Keyword Scout (`agents/keyword_scout.py`)

**Schedule:** Every Sunday at 09:00am  
**Purpose:** Identify new keyword opportunities and negative keywords from search terms data.

**Inputs:**
- `SEARCH_TERMS_30D` (search terms with > 10 impressions)
- `KEYWORD_PERFORMANCE_30D` (existing keywords)
- Client context

**Outputs:**
- `approval_queue` rows for each recommendation:
  - `add_keyword` — new keyword to add
  - `add_negative_keyword` — wasteful search term to block
  - `adjust_match_type` — match type change recommendation

---

## Creator (`agents/creator.py`)

**Schedule:** On demand only — triggered via `POST /campaigns/create`  
**Purpose:** Generate a complete campaign structure from a brief.

**Inputs (via API):**
```json
{
  "account_id": 1,
  "brief": {
    "goal": "generate leads for brake pad replacement",
    "product_service": "brake pad replacement",
    "audience_description": "car owners in Johannesburg",
    "budget_daily_zar": 150,
    "geo_targets": ["Johannesburg", "Sandton"],
    "languages": ["English"],
    "landing_page_url": "https://example.co.za/brakes"
  }
}
```

**Outputs:**
- One `approval_queue` row with `action_type='create_campaign'`
- `action_payload` contains the full campaign structure JSON
- On approval + execution: `campaign_builder.py` creates the campaign in Google Ads (starts PAUSED)

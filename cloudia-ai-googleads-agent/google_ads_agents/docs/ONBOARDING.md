# Client Onboarding Guide

How to add a new client account to the Google Ads Agent System.

---

## Prerequisites

- Google Ads customer ID for the client account
- Client has granted MCC access to CloudIA's MCC account
- You have the client's business context (industry, KPIs, budget)

---

## Step 1 — Confirm API access

Verify the client's account is accessible via your MCC:

```python
# Quick test — run from the project root
from google_ads.client import AdsClient
from google_ads.queries import CAMPAIGN_PERFORMANCE_7D

client = AdsClient()
rows = client.run_query(customer_id="CUSTOMER_ID_NO_DASHES", query=CAMPAIGN_PERFORMANCE_7D)
print(f"Found {len(rows)} campaigns")
```

If this raises a `GoogleAdsException`, fix the permission issue before proceeding.

---

## Step 2 — Insert the account record

Via psql or your preferred DB client:

```sql
INSERT INTO accounts (
  client_name,
  customer_id,
  mcc_id,
  status,
  industry,
  business_type,
  geo_focus,
  avg_transaction_value,
  sales_cycle_days,
  primary_kpi,
  primary_kpi_target,
  secondary_kpi,
  secondary_kpi_target,
  monthly_ad_spend,
  budget_sensitivity,
  min_daily_budget,
  peak_months,
  slow_months,
  custom_rules,
  alert_email,
  report_email,
  notes
) VALUES (
  'Client Name Pty Ltd',
  '1234567890',               -- no dashes
  '0987654321',               -- your MCC ID
  'calibrating',              -- always start here
  'automotive_parts',
  'local_service',
  'local',
  2500.00,                    -- ZAR avg transaction value
  1,                          -- sales cycle in days
  'CPL',
  450.00,                     -- target cost per lead (ZAR)
  'CTR',
  0.045,
  15000.00,                   -- monthly ad budget (ZAR)
  'moderate',
  200.00,                     -- minimum daily budget (ZAR)
  '[10, 11, 12]',             -- peak months as JSON array
  '[6, 7]',                   -- slow months
  '{
    "never_pause_brand_campaign": true,
    "max_cpc_increase_pct": 15,
    "max_daily_spend_increase_pct": 10,
    "competitor_bidding_allowed": false
  }',
  'alerts@clientdomain.co.za',
  'reports@clientdomain.co.za',
  'Automotive parts retailer, JHB North.'
);
```

---

## Step 3 — Calibration period (30 days)

While `status = 'calibrating'`:

- All agents **skip** this account automatically
- The Auditor still pulls and saves campaign snapshots every 6 hours
- This builds up a baseline of data without making any recommendations

**Nothing to do** during calibration — the system handles it.

---

## Step 4 — Set baselines after 30 days

After 30 days of data collection, calculate baselines from the `campaign_snapshots` table and set them via the API:

```bash
curl -X POST http://localhost:8000/accounts/{account_id}/baseline \
  -H "Content-Type: application/json" \
  -d '{
    "ctr": 0.0450,
    "cvr": 0.0320,
    "cpc": 18.50,
    "cpa": 420.00,
    "roas": 3.20
  }'
```

This sets `baseline_set_at = now()`. The account becomes eligible for all agents.

---

## Step 5 — Activate the account

```sql
UPDATE accounts SET status = 'active' WHERE customer_id = '1234567890';
```

From the next scheduler cycle, all agents will include this account.

---

## Step 6 — Verify first runs

Check `agent_runs` after the next Auditor cycle:

```sql
SELECT agent_name, status, summary, tokens_used, cost_usd
FROM agent_runs
WHERE account_id = (SELECT id FROM accounts WHERE customer_id = '1234567890')
ORDER BY started_at DESC
LIMIT 10;
```

If status is `skipped`, confirm `baseline_set_at` is set and `status = 'active'`.

---

## Common custom_rules fields

| Rule | Type | Description |
|---|---|---|
| `never_pause_brand_campaign` | bool | Blocks all pause_campaign decisions |
| `max_cpc_increase_pct` | int | Max % bid increase per Manager cycle |
| `max_daily_spend_increase_pct` | int | Max % budget increase per cycle |
| `blackout_dates` | string[] | Dates when no changes should be made (YYYY-MM-DD) |
| `always_include_keywords` | string[] | Keywords the KeywordScout must never suggest removing |
| `competitor_bidding_allowed` | bool | Whether to recommend competitor brand keywords |

---

## Offboarding a client

```sql
UPDATE accounts SET status = 'churned' WHERE customer_id = '1234567890';
```

All agents skip churned accounts. Historical data is retained.

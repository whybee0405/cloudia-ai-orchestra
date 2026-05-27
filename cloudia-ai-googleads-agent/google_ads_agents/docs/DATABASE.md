# Database Schema

PostgreSQL 15. All migrations managed by Alembic. ORM via SQLAlchemy 2.0.

Run migrations: `alembic upgrade head`

---

## accounts

Master client registry. Every other table references this via `account_id`.

| Column | Type | Notes |
|---|---|---|
| id | SERIAL PK | |
| client_name | VARCHAR(255) | Display name |
| customer_id | VARCHAR(50) UNIQUE | Google Ads customer ID (no dashes) |
| mcc_id | VARCHAR(50) | Your MCC account ID |
| status | VARCHAR(20) | `calibrating` \| `active` \| `paused` \| `churned` |
| industry | VARCHAR(100) | e.g. `automotive_parts`, `dental`, `legal` |
| business_type | VARCHAR(50) | `local_service` \| `ecommerce` \| `lead_gen` |
| geo_focus | VARCHAR(20) | `local` \| `regional` \| `national` |
| avg_transaction_value | NUMERIC(10,2) | ZAR |
| sales_cycle_days | INTEGER | |
| primary_kpi | VARCHAR(20) | `CPL` \| `ROAS` \| `CPA` \| `CTR` |
| primary_kpi_target | NUMERIC(10,2) | |
| secondary_kpi | VARCHAR(20) | |
| secondary_kpi_target | NUMERIC(10,2) | |
| monthly_ad_spend | NUMERIC(10,2) | Client's ad budget in ZAR |
| budget_sensitivity | VARCHAR(20) | `aggressive` \| `moderate` \| `conservative` |
| min_daily_budget | NUMERIC(10,2) | Hard floor — agents never go below this |
| baseline_ctr | NUMERIC(6,4) | Set after 30-day calibration |
| baseline_cvr | NUMERIC(6,4) | |
| baseline_cpc | NUMERIC(10,2) | ZAR |
| baseline_cpa | NUMERIC(10,2) | ZAR |
| baseline_roas | NUMERIC(8,2) | |
| baseline_set_at | TIMESTAMP | When baselines were locked in |
| peak_months | JSONB | e.g. `[10, 11, 12]` |
| slow_months | JSONB | e.g. `[6, 7]` |
| custom_rules | JSONB | See rules engine below |
| alert_email | VARCHAR(255) | Receives anomaly alerts + queue summaries |
| report_email | VARCHAR(255) | Receives weekly reports |
| onboarded_at | TIMESTAMP | |
| notes | TEXT | Free text |

**custom_rules JSON schema:**
```json
{
  "never_pause_brand_campaign": true,
  "max_cpc_increase_pct": 20,
  "max_daily_spend_increase_pct": 15,
  "blackout_dates": ["2025-12-25"],
  "always_include_keywords": ["brand term xyz"],
  "competitor_bidding_allowed": false
}
```

**Account lifecycle:**
1. `calibrating` — first 30 days. Agents skip, only data is collected.
2. `active` — baselines set. All agents run.
3. `paused` — temporarily suspended. Agents skip.
4. `churned` — client offboarded. Agents skip.

---

## campaign_snapshots

Point-in-time campaign metrics stored every 6 hours by the Auditor.

| Column | Type | Notes |
|---|---|---|
| id | SERIAL PK | |
| account_id | INTEGER FK | → accounts.id |
| campaign_id | VARCHAR(50) | Google Ads campaign ID |
| campaign_name | VARCHAR(255) | |
| snapshot_time | TIMESTAMP | UTC |
| impressions | BIGINT | |
| clicks | BIGINT | |
| cost_micros | BIGINT | Divide by 1,000,000 for ZAR |
| conversions | NUMERIC(10,2) | |
| ctr | NUMERIC(6,4) | |
| avg_cpc_micros | BIGINT | |
| conversion_rate | NUMERIC(6,4) | |
| cost_per_conversion | NUMERIC(10,2) | ZAR |
| roas | NUMERIC(8,2) | |
| budget_micros | BIGINT | Daily budget |
| status | VARCHAR(50) | `ENABLED` \| `PAUSED` \| `REMOVED` |
| raw_json | JSONB | Full API response for debugging |

**Indexes:** `(account_id, campaign_id)`, `(snapshot_time)`

---

## audit_log

Every anomaly detected by the Auditor. Persisted even if no action is taken.

| Column | Type | Notes |
|---|---|---|
| id | SERIAL PK | |
| account_id | INTEGER FK | |
| run_time | TIMESTAMP | When the Auditor ran |
| campaign_id | VARCHAR(50) | |
| anomaly_type | VARCHAR(100) | `ctr_drop` \| `spend_spike` \| `cvr_collapse` \| `cpa_spike` \| `zero_conversions` |
| severity | VARCHAR(20) | `LOW` \| `MEDIUM` \| `HIGH` \| `CRITICAL` |
| diagnosis | TEXT | Claude's plain-English explanation |
| recommended_action | TEXT | Claude's recommendation |
| delta_value | NUMERIC(10,4) | The actual change that triggered this |
| threshold_used | NUMERIC(10,4) | The threshold that was set |
| acknowledged | BOOLEAN | Has a human reviewed this? |
| acknowledged_at | TIMESTAMP | |
| acknowledged_by | VARCHAR(100) | |

**Indexes:** `(account_id, severity)`

---

## approval_queue

All agent decisions awaiting human review. Nothing executes without approval.

| Column | Type | Notes |
|---|---|---|
| id | SERIAL PK | |
| account_id | INTEGER FK | |
| agent_name | VARCHAR(50) | `manager` \| `keyword_scout` \| `creator` |
| created_at | TIMESTAMP | |
| action_type | VARCHAR(100) | See action types per agent |
| action_payload | JSONB | Exact parameters passed to executor |
| reasoning | TEXT | Claude's explanation |
| status | VARCHAR(20) | `pending` → `approved`/`rejected` → `executed`/`failed` |
| reviewed_at | TIMESTAMP | |
| reviewed_by | VARCHAR(100) | |
| executed_at | TIMESTAMP | |
| execution_result | JSONB | Google Ads API response |
| failure_reason | TEXT | On `failed` status |

**Status flow:** `pending` → `approved` or `rejected`. Only `approved` items can be `executed`. Execution sets status to `executed` or `failed`.

**Index:** `(status)`

---

## industry_benchmarks

Reference data injected into every Claude prompt.

| Column | Type | Notes |
|---|---|---|
| id | SERIAL PK | |
| industry | VARCHAR(100) | Matches `accounts.industry` |
| avg_ctr | NUMERIC(6,4) | |
| avg_cvr | NUMERIC(6,4) | |
| avg_cpc_zar | NUMERIC(10,2) | |
| avg_cpa_zar | NUMERIC(10,2) | |
| good_quality_score | INTEGER | Default 7 |
| source | VARCHAR(100) | e.g. `wordstream_2024` |
| updated_at | TIMESTAMP | |
| notes | TEXT | |

---

## agent_runs

Every agent execution logged for debugging and cost tracking.

| Column | Type | Notes |
|---|---|---|
| id | SERIAL PK | |
| agent_name | VARCHAR(50) | |
| account_id | INTEGER FK | NULL for orchestrator-level runs |
| started_at | TIMESTAMP | |
| completed_at | TIMESTAMP | |
| status | VARCHAR(20) | `running` \| `success` \| `failed` \| `skipped` |
| tokens_used | INTEGER | Input + output tokens |
| cost_usd | NUMERIC(8,6) | Estimated Claude API cost |
| decisions_generated | INTEGER | Queue items created |
| anomalies_found | INTEGER | Audit log entries created |
| summary | TEXT | One-line run summary |
| error | TEXT | Exception message on failure |

**Index:** `(account_id)`

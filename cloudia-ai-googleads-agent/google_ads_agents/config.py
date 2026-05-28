"""Central configuration — all env vars and app-wide constants."""

import os
from dotenv import load_dotenv

load_dotenv()


# ── Google Ads ──────────────────────────────────────────────────────────────
GOOGLE_ADS_DEVELOPER_TOKEN: str = os.environ["GOOGLE_ADS_DEVELOPER_TOKEN"]
GOOGLE_ADS_CLIENT_ID: str = os.environ["GOOGLE_ADS_CLIENT_ID"]
GOOGLE_ADS_CLIENT_SECRET: str = os.environ["GOOGLE_ADS_CLIENT_SECRET"]
GOOGLE_ADS_REFRESH_TOKEN: str = os.environ["GOOGLE_ADS_REFRESH_TOKEN"]
GOOGLE_ADS_LOGIN_CUSTOMER_ID: str = os.environ["GOOGLE_ADS_LOGIN_CUSTOMER_ID"]

# ── Anthropic ───────────────────────────────────────────────────────────────
ANTHROPIC_API_KEY: str = os.environ["ANTHROPIC_API_KEY"]
ANTHROPIC_MODEL: str = os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-20250514")
ANTHROPIC_MAX_TOKENS: int = int(os.getenv("ANTHROPIC_MAX_TOKENS", "1500"))

# ── Database ─────────────────────────────────────────────────────────────────
DATABASE_URL: str = os.environ["DATABASE_URL"]

# ── API ──────────────────────────────────────────────────────────────────────
API_HOST: str = os.getenv("API_HOST", "0.0.0.0")
API_PORT: int = int(os.getenv("API_PORT", "8000"))
API_SECRET_KEY: str = os.getenv("API_SECRET_KEY", "")

# ── Notifications ─────────────────────────────────────────────────────────────
SMTP_HOST: str = os.getenv("SMTP_HOST", "")
SMTP_PORT: int = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER: str = os.getenv("SMTP_USER", "")
SMTP_PASSWORD: str = os.getenv("SMTP_PASSWORD", "")
NOTIFICATION_FROM_EMAIL: str = os.getenv("NOTIFICATION_FROM_EMAIL", "")
CLOUDIA_ALERT_EMAIL: str = os.getenv("CLOUDIA_ALERT_EMAIL", "")

# ── Brand DNA Service ─────────────────────────────────────────────────────────
BRAND_DNA_SERVICE_URL: str = os.getenv("BRAND_DNA_SERVICE_URL", "http://localhost:8000")
INTERNAL_API_SECRET: str = os.getenv("INTERNAL_API_SECRET", "")

# ── App ───────────────────────────────────────────────────────────────────────
ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development")
LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")

# ── Agent schedule constants ──────────────────────────────────────────────────
AUDITOR_INTERVAL_HOURS: int = 6
MANAGER_HOUR: int = 10          # daily 10:00 am
REPORTER_DAY_OF_WEEK: str = "mon"
REPORTER_HOUR: int = 8
KEYWORD_SCOUT_DAY_OF_WEEK: str = "sun"
KEYWORD_SCOUT_HOUR: int = 9

# ── Anomaly detection thresholds by budget_sensitivity ───────────────────────
ANOMALY_THRESHOLDS: dict[str, dict[str, float]] = {
    "aggressive": {
        "ctr_drop_pct": 40.0,
        "spend_spike_pct": 60.0,
        "cvr_collapse_pct": 40.0,
        "cpa_spike_pct": 60.0,
        "zero_conversion_days": 5,
        "quality_score_drop": 2,
    },
    "moderate": {
        "ctr_drop_pct": 30.0,
        "spend_spike_pct": 40.0,
        "cvr_collapse_pct": 30.0,
        "cpa_spike_pct": 40.0,
        "zero_conversion_days": 4,
        "quality_score_drop": 2,
    },
    "conservative": {
        "ctr_drop_pct": 20.0,
        "spend_spike_pct": 25.0,
        "cvr_collapse_pct": 20.0,
        "cpa_spike_pct": 25.0,
        "zero_conversion_days": 3,
        "quality_score_drop": 1,
    },
}

# ── Micros conversion ─────────────────────────────────────────────────────────
MICROS_DIVISOR: int = 1_000_000

# ── Account status values ─────────────────────────────────────────────────────
ACCOUNT_STATUS_CALIBRATING: str = "calibrating"
ACCOUNT_STATUS_ACTIVE: str = "active"
ACCOUNT_STATUS_PAUSED: str = "paused"
ACCOUNT_STATUS_CHURNED: str = "churned"

# ── Approval queue status values ──────────────────────────────────────────────
QUEUE_STATUS_PENDING: str = "pending"
QUEUE_STATUS_APPROVED: str = "approved"
QUEUE_STATUS_REJECTED: str = "rejected"
QUEUE_STATUS_EXECUTED: str = "executed"
QUEUE_STATUS_FAILED: str = "failed"

# ── Severity levels ───────────────────────────────────────────────────────────
SEVERITY_LOW: str = "LOW"
SEVERITY_MEDIUM: str = "MEDIUM"
SEVERITY_HIGH: str = "HIGH"
SEVERITY_CRITICAL: str = "CRITICAL"

IMMEDIATE_ALERT_SEVERITIES: set[str] = {SEVERITY_HIGH, SEVERITY_CRITICAL}

# ── Calibration window ────────────────────────────────────────────────────────
CALIBRATION_DAYS: int = 30

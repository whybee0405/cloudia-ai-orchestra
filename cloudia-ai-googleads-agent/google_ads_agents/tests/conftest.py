"""
Shared pytest fixtures and test configuration.

IMPORTANT: env vars are set at module level so they are available before
config.py is imported by any test file. The SQLite JSONB patch must also
run before any model import.
"""

import os

# ── Set all required env vars before any project import ───────────────────────
os.environ.setdefault("GOOGLE_ADS_DEVELOPER_TOKEN", "test-developer-token")
os.environ.setdefault("GOOGLE_ADS_CLIENT_ID", "test-client-id")
os.environ.setdefault("GOOGLE_ADS_CLIENT_SECRET", "test-client-secret")
os.environ.setdefault("GOOGLE_ADS_REFRESH_TOKEN", "test-refresh-token")
os.environ.setdefault("GOOGLE_ADS_LOGIN_CUSTOMER_ID", "1234567890")
os.environ.setdefault("ANTHROPIC_API_KEY", "test-anthropic-key")
os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
os.environ.setdefault("API_SECRET_KEY", "test-secret-key")
os.environ.setdefault("ENVIRONMENT", "testing")
os.environ.setdefault("LOG_LEVEL", "WARNING")

# ── Patch SQLite to understand JSONB (must run before model imports) ──────────
from sqlalchemy.dialects.sqlite.base import SQLiteTypeCompiler  # noqa: E402

SQLiteTypeCompiler.visit_JSONB = lambda self, type_, **kw: "JSON"

# ── Now it is safe to import project modules ───────────────────────────────────
from datetime import datetime, timedelta, timezone
from typing import Any
from unittest.mock import MagicMock

import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session, sessionmaker

from ai.claude import ClaudeClient
from db.models import Account, Base, IndustryBenchmark
from google_ads.client import AdsClient


# ── SQLite in-memory engine fixture ───────────────────────────────────────────

@pytest.fixture(scope="session")
def engine():
    """Create a single SQLite in-memory engine for the whole test session."""
    eng = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})

    @event.listens_for(eng, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    Base.metadata.create_all(eng)
    return eng


@pytest.fixture()
def db_session(engine):
    """Yield a transactional SQLAlchemy session that rolls back after each test."""
    connection = engine.connect()
    transaction = connection.begin()
    Session_ = sessionmaker(bind=connection)
    session = Session_()

    yield session

    session.close()
    transaction.rollback()
    connection.close()


# ── Client mocks ───────────────────────────────────────────────────────────────

@pytest.fixture()
def mock_ads_client() -> MagicMock:
    """A MagicMock of AdsClient whose run_query always returns an empty list."""
    client = MagicMock(spec=AdsClient)
    client.run_query.return_value = []
    return client


@pytest.fixture()
def mock_claude_client() -> MagicMock:
    """A MagicMock of ClaudeClient with sensible default return values."""
    client = MagicMock(spec=ClaudeClient)
    client.complete.return_value = ("", 0)
    client.complete_json.return_value = ({}, 0)
    client.estimate_cost_usd.return_value = 0.0
    return client


@pytest.fixture()
def mock_db_session() -> MagicMock:
    """A MagicMock of a SQLAlchemy Session for unit tests that don't need a DB."""
    return MagicMock(spec=Session)


# ── Domain objects ─────────────────────────────────────────────────────────────

@pytest.fixture()
def sample_account() -> Account:
    """Fully populated Account (not persisted). Calibration complete (baseline > 30d)."""
    return Account(
        id=1,
        client_name="Test Auto Parts",
        customer_id="1234567890",
        mcc_id="0987654321",
        status="active",
        industry="automotive_parts",
        business_type="local_service",
        geo_focus="local",
        avg_transaction_value=2500.00,
        sales_cycle_days=1,
        primary_kpi="CPL",
        primary_kpi_target=450.00,
        secondary_kpi="ROAS",
        secondary_kpi_target=3.0,
        monthly_ad_spend=15000.00,
        budget_sensitivity="moderate",
        min_daily_budget=200.00,
        baseline_ctr=0.0450,
        baseline_cvr=0.0320,
        baseline_cpc=18.50,
        baseline_cpa=420.00,
        baseline_roas=3.20,
        baseline_set_at=datetime(2025, 1, 1),  # >30 days ago
        peak_months=[10, 11, 12],
        slow_months=[6, 7],
        custom_rules={
            "never_pause_brand_campaign": True,
            "max_cpc_increase_pct": 15,
        },
        alert_email="alerts@testclient.co.za",
        report_email="reports@testclient.co.za",
    )


@pytest.fixture()
def sample_benchmark() -> IndustryBenchmark:
    """IndustryBenchmark for 'automotive_parts'."""
    return IndustryBenchmark(
        industry="automotive_parts",
        avg_ctr=0.035,
        avg_cvr=0.025,
        avg_cpc_zar=22.00,
        avg_cpa_zar=550.00,
        good_quality_score=7,
        source="wordstream_2024",
    )


@pytest.fixture()
def persisted_account(db_session: Session) -> Account:
    """Account persisted to the SQLite test DB, available for integration tests."""
    account = Account(
        client_name="Persisted Dental Practice",
        customer_id="9999888877",
        mcc_id="1111222233",
        status="active",
        industry="dental",
        business_type="local_service",
        budget_sensitivity="conservative",
        monthly_ad_spend=5000.00,
        primary_kpi="CPL",
        primary_kpi_target=200.00,
        baseline_ctr=0.045,
        baseline_cvr=0.032,
        baseline_cpc=12.50,
        baseline_cpa=390.00,
        baseline_roas=None,
        baseline_set_at=datetime.now(timezone.utc) - timedelta(days=45),
        peak_months=[1, 6],
        slow_months=[7, 8],
        custom_rules={
            "never_pause_brand_campaign": True,
            "max_cpc_increase_pct": 15,
            "competitor_bidding_allowed": False,
        },
        alert_email="test@example.com",
        report_email="report@example.com",
    )
    db_session.add(account)
    db_session.commit()
    db_session.refresh(account)
    return account

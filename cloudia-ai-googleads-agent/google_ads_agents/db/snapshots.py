"""Campaign snapshot read/write logic."""

import logging
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

import config
from db.models import CampaignSnapshot

logger = logging.getLogger(__name__)


def save_snapshot(
    db: Session,
    account_id: int,
    campaign_data: list[dict[str, Any]],
) -> list[CampaignSnapshot]:
    """Persist a list of campaign metric dicts as snapshot rows.

    Args:
        db: Active SQLAlchemy session.
        account_id: The account these campaigns belong to.
        campaign_data: List of dicts parsed from GAQL rows.

    Returns:
        List of newly created CampaignSnapshot ORM objects.
    """
    now = datetime.now(timezone.utc)
    snapshots: list[CampaignSnapshot] = []

    for row in campaign_data:
        snapshot = CampaignSnapshot(
            account_id=account_id,
            campaign_id=str(row["campaign_id"]),
            campaign_name=row.get("campaign_name"),
            snapshot_time=now,
            impressions=row.get("impressions"),
            clicks=row.get("clicks"),
            cost_micros=row.get("cost_micros"),
            conversions=row.get("conversions"),
            ctr=row.get("ctr"),
            avg_cpc_micros=row.get("avg_cpc_micros"),
            conversion_rate=row.get("conversion_rate"),
            cost_per_conversion=row.get("cost_per_conversion"),
            roas=row.get("roas"),
            budget_micros=row.get("budget_micros"),
            status=row.get("status"),
            raw_json=row,
        )
        db.add(snapshot)
        snapshots.append(snapshot)

    db.commit()
    logger.debug("Saved %d snapshots for account %d", len(snapshots), account_id)
    return snapshots


def get_previous_snapshot(
    db: Session,
    account_id: int,
    campaign_id: str,
    before_snapshot_time: datetime,
) -> CampaignSnapshot | None:
    """Return the most recent snapshot for a campaign before a given timestamp.

    Args:
        db: Active SQLAlchemy session.
        account_id: Filter to this account.
        campaign_id: The Google Ads campaign ID.
        before_snapshot_time: Return only snapshots older than this.

    Returns:
        The most recent matching CampaignSnapshot, or None.
    """
    stmt = (
        select(CampaignSnapshot)
        .where(
            CampaignSnapshot.account_id == account_id,
            CampaignSnapshot.campaign_id == campaign_id,
            CampaignSnapshot.snapshot_time < before_snapshot_time,
        )
        .order_by(CampaignSnapshot.snapshot_time.desc())
        .limit(1)
    )
    return db.scalars(stmt).first()


def parse_gaql_row(row: Any) -> dict[str, Any]:
    """Convert a proto-plus GAQL row into a plain dict for snapshotting.

    Args:
        row: A GoogleAdsRow proto-plus object from AdsClient.run_query().

    Returns:
        A flat dict ready for CampaignSnapshot fields.
    """
    return {
        "campaign_id": str(row.campaign.id),
        "campaign_name": row.campaign.name,
        "status": row.campaign.status.name,
        "impressions": row.metrics.impressions,
        "clicks": row.metrics.clicks,
        "cost_micros": row.metrics.cost_micros,
        "conversions": float(row.metrics.conversions),
        "ctr": float(row.metrics.ctr),
        "avg_cpc_micros": row.metrics.average_cpc,
        "conversion_rate": float(row.metrics.conversions_from_interactions_rate),
        "cost_per_conversion": float(row.metrics.cost_per_conversion) if row.metrics.cost_per_conversion else None,
        "budget_micros": row.campaign_budget.amount_micros if row.campaign_budget.amount_micros else None,
    }

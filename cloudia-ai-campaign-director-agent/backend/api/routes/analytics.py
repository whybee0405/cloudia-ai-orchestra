from datetime import datetime
from decimal import Decimal
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from backend.api.schemas import CampaignAnalyticsSummary, TopPost
from backend.db.models import (
    ContentCalendar,
    PostAnalytics,
    PublishedPost,
    ScheduledPost,
)
from backend.db.session import get_db

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("", response_model=CampaignAnalyticsSummary)
def get_analytics(
    client_id: Optional[int] = Query(None),
    campaign_id: Optional[int] = Query(None),
    platform: Optional[str] = Query(None),
    date_from: Optional[datetime] = Query(None),
    date_to: Optional[datetime] = Query(None),
    top_posts_limit: int = Query(10, ge=1, le=100),
    db: Session = Depends(get_db),
):
    q = (
        db.query(PostAnalytics)
        .join(PublishedPost, PostAnalytics.published_post_id == PublishedPost.id)
        .join(ScheduledPost, PublishedPost.scheduled_post_id == ScheduledPost.id)
        .join(ContentCalendar, ScheduledPost.calendar_id == ContentCalendar.id)
    )

    if client_id is not None:
        q = q.filter(ContentCalendar.client_id == client_id)
    if campaign_id is not None:
        q = q.filter(ContentCalendar.campaign_id == campaign_id)
    if platform is not None:
        q = q.filter(PublishedPost.platform == platform)
    if date_from is not None:
        q = q.filter(PublishedPost.published_at >= date_from)
    if date_to is not None:
        q = q.filter(PublishedPost.published_at <= date_to)

    agg = q.with_entities(
        func.coalesce(func.sum(PostAnalytics.reach), 0).label("total_reach"),
        func.coalesce(func.sum(PostAnalytics.impressions), 0).label("total_impressions"),
        func.coalesce(
            func.sum(
                func.coalesce(PostAnalytics.likes, 0)
                + func.coalesce(PostAnalytics.comments, 0)
                + func.coalesce(PostAnalytics.shares, 0)
                + func.coalesce(PostAnalytics.saves, 0)
            ),
            0,
        ).label("total_engagement"),
        func.avg(PostAnalytics.engagement_rate).label("avg_engagement_rate"),
    ).one()

    top_q = (
        db.query(
            PostAnalytics.published_post_id,
            PublishedPost.post_url,
            PublishedPost.platform,
            func.coalesce(PostAnalytics.impressions, 0).label("impressions"),
            func.coalesce(PostAnalytics.reach, 0).label("reach"),
            PostAnalytics.engagement_rate,
        )
        .join(PublishedPost, PostAnalytics.published_post_id == PublishedPost.id)
        .join(ScheduledPost, PublishedPost.scheduled_post_id == ScheduledPost.id)
        .join(ContentCalendar, ScheduledPost.calendar_id == ContentCalendar.id)
    )

    if client_id is not None:
        top_q = top_q.filter(ContentCalendar.client_id == client_id)
    if campaign_id is not None:
        top_q = top_q.filter(ContentCalendar.campaign_id == campaign_id)
    if platform is not None:
        top_q = top_q.filter(PublishedPost.platform == platform)
    if date_from is not None:
        top_q = top_q.filter(PublishedPost.published_at >= date_from)
    if date_to is not None:
        top_q = top_q.filter(PublishedPost.published_at <= date_to)

    top_rows = (
        top_q.order_by(PostAnalytics.impressions.desc().nullslast())
        .limit(top_posts_limit)
        .all()
    )

    top_posts = [
        TopPost(
            published_post_id=row.published_post_id,
            post_url=row.post_url,
            platform=row.platform,
            impressions=row.impressions or 0,
            reach=row.reach or 0,
            engagement_rate=row.engagement_rate,
        )
        for row in top_rows
    ]

    avg_rate = agg.avg_engagement_rate
    if avg_rate is not None:
        avg_rate = Decimal(str(avg_rate)).quantize(Decimal("0.0001"))

    return CampaignAnalyticsSummary(
        total_reach=int(agg.total_reach),
        total_impressions=int(agg.total_impressions),
        total_engagement=int(agg.total_engagement),
        avg_engagement_rate=avg_rate,
        top_posts=top_posts,
    )

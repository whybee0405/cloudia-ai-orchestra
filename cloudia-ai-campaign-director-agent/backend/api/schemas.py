from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict


class ClientCreate(BaseModel):
    name: str
    industry: Optional[str] = None
    business_type: Optional[str] = None
    target_audience: Optional[str] = None
    usp: Optional[str] = None
    tone_of_voice: Optional[str] = None
    brand_colours: Optional[Any] = None
    city: Optional[str] = None
    country: str = "South Africa"
    brand_dna_client_id: Optional[str] = None


class ClientRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    industry: Optional[str] = None
    business_type: Optional[str] = None
    target_audience: Optional[str] = None
    usp: Optional[str] = None
    tone_of_voice: Optional[str] = None
    brand_colours: Optional[Any] = None
    city: Optional[str] = None
    country: Optional[str] = None
    is_active: bool
    created_at: Optional[datetime] = None
    brand_dna_client_id: Optional[str] = None


class CampaignCreate(BaseModel):
    client_id: int
    name: str
    goal: Optional[str] = None
    brief: Any
    platforms: Any
    duration_days: Optional[int] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    posts_per_week: Optional[int] = None
    content_mix: Optional[Any] = None
    target_audience: Optional[str] = None
    campaign_hashtags: Optional[Any] = None
    operator_notes: Optional[str] = None


class CampaignRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    client_id: int
    name: str
    goal: Optional[str] = None
    status: Optional[str] = None
    brief: Any
    platforms: Any
    duration_days: Optional[int] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    posts_per_week: Optional[int] = None
    content_mix: Optional[Any] = None
    target_audience: Optional[str] = None
    campaign_hashtags: Optional[Any] = None
    operator_notes: Optional[str] = None
    created_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    calendar_items: list[CalendarItemRead] = []
    content_assets: list[AssetListItem] = []
    approval_gates: list[ApprovalGateRead] = []


class CampaignListItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    client_id: int
    name: str
    goal: Optional[str] = None
    status: Optional[str] = None
    platforms: Any
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    created_at: Optional[datetime] = None


class CampaignUpdate(BaseModel):
    operator_notes: Optional[str] = None
    status: Optional[str] = None


class CalendarItemRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    campaign_id: int
    client_id: int
    platform: str
    content_type: str
    scheduled_for: datetime
    status: Optional[str] = None
    asset_id: Optional[int] = None
    topic: Optional[str] = None
    notes: Optional[str] = None
    created_at: Optional[datetime] = None


class CalendarItemUpdate(BaseModel):
    scheduled_for: Optional[datetime] = None
    status: Optional[str] = None
    notes: Optional[str] = None


class AssetRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    campaign_id: int
    client_id: int
    asset_type: str
    content_type: Optional[str] = None
    title: Optional[str] = None
    text_content: Optional[str] = None
    storage_path: Optional[str] = None
    storage_bucket: Optional[str] = None
    file_size_bytes: Optional[int] = None
    duration_seconds: Optional[int] = None
    width: Optional[int] = None
    height: Optional[int] = None
    format: Optional[str] = None
    platform_versions: Optional[Any] = None
    status: Optional[str] = None
    brand_check_passed: Optional[bool] = None
    brand_check_notes: Optional[str] = None
    generation_prompt: Optional[str] = None
    generation_model: Optional[str] = None
    tokens_used: Optional[int] = None
    cost_usd: Optional[Decimal] = None
    created_by_agent: Optional[str] = None
    created_at: Optional[datetime] = None


class AssetListItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    campaign_id: int
    client_id: int
    asset_type: str
    content_type: Optional[str] = None
    title: Optional[str] = None
    status: Optional[str] = None
    storage_path: Optional[str] = None
    created_at: Optional[datetime] = None


class AssetUpdate(BaseModel):
    status: Optional[str] = None
    text_content: Optional[str] = None


class ApprovalGateRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    campaign_id: int
    gate_name: Optional[str] = None
    pipeline_order: Optional[int] = None
    status: Optional[str] = None
    notes: Optional[str] = None
    created_at: Optional[datetime] = None
    reviewed_at: Optional[datetime] = None
    reviewed_by: Optional[str] = None


class ApprovalAction(BaseModel):
    notes: Optional[str] = None
    reviewed_by: Optional[str] = None


class ScheduledPostRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    calendar_id: int
    asset_id: int
    platform_account_id: int
    scheduled_for: datetime
    caption: Optional[str] = None
    hashtags: Optional[Any] = None
    first_comment: Optional[str] = None
    status: Optional[str] = None
    celery_task_id: Optional[str] = None
    created_at: Optional[datetime] = None


class AnalyticsRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    published_post_id: int
    snapshot_type: Optional[str] = None
    pulled_at: Optional[datetime] = None
    impressions: Optional[int] = None
    reach: Optional[int] = None
    likes: Optional[int] = None
    comments: Optional[int] = None
    shares: Optional[int] = None
    saves: Optional[int] = None
    clicks: Optional[int] = None
    video_views: Optional[int] = None
    video_watch_time_sec: Optional[int] = None
    engagement_rate: Optional[Decimal] = None


class TopPost(BaseModel):
    published_post_id: int
    post_url: Optional[str]
    platform: Optional[str]
    impressions: int
    reach: int
    engagement_rate: Optional[Decimal]


class CampaignAnalyticsSummary(BaseModel):
    total_reach: int
    total_impressions: int
    total_engagement: int
    avg_engagement_rate: Optional[Decimal]
    top_posts: list[TopPost]


class PlatformAccountRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    client_id: int
    platform: str
    account_name: Optional[str] = None
    account_id: Optional[str] = None
    page_id: Optional[str] = None
    scopes: Optional[Any] = None
    is_active: bool
    last_verified_at: Optional[datetime] = None
    connected_at: Optional[datetime] = None
    token_expires_at: Optional[datetime] = None


class BrandGuidelinesCreate(BaseModel):
    primary_colour: Optional[str] = None
    secondary_colour: Optional[str] = None
    accent_colour: Optional[str] = None
    background_colour: Optional[str] = None
    logo_path: Optional[str] = None
    logo_dark_path: Optional[str] = None
    heading_font: Optional[str] = None
    body_font: Optional[str] = None
    tone_keywords: Optional[Any] = None
    forbidden_words: Optional[Any] = None
    competitor_names: Optional[Any] = None
    required_elements: Optional[Any] = None
    image_style_notes: Optional[str] = None
    copy_style_notes: Optional[str] = None
    voice_id: Optional[str] = None


class BrandGuidelinesRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    client_id: int
    primary_colour: Optional[str] = None
    secondary_colour: Optional[str] = None
    accent_colour: Optional[str] = None
    background_colour: Optional[str] = None
    logo_path: Optional[str] = None
    logo_dark_path: Optional[str] = None
    heading_font: Optional[str] = None
    body_font: Optional[str] = None
    tone_keywords: Optional[Any] = None
    forbidden_words: Optional[Any] = None
    competitor_names: Optional[Any] = None
    required_elements: Optional[Any] = None
    image_style_notes: Optional[str] = None
    copy_style_notes: Optional[str] = None
    voice_id: Optional[str] = None
    updated_at: Optional[datetime] = None


CampaignRead.model_rebuild()

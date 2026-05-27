from datetime import datetime
from sqlalchemy import (
    Column, Integer, String, Text, Boolean, BigInteger, Numeric,
    DateTime, Date, ForeignKey, UniqueConstraint, JSON, func
)
from sqlalchemy.orm import DeclarativeBase, relationship


class Base(DeclarativeBase):
    pass


class Client(Base):
    __tablename__ = "clients"

    id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=False)
    industry = Column(String(100))
    business_type = Column(String(100))
    target_audience = Column(Text)
    usp = Column(Text)
    tone_of_voice = Column(String(100))
    brand_colours = Column(JSON)
    city = Column(String(100))
    country = Column(String(100), default="South Africa")
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=func.now())

    campaigns = relationship("Campaign", back_populates="client", cascade="all, delete-orphan")
    brand_guidelines = relationship("BrandGuidelines", back_populates="client", uselist=False)
    platform_accounts = relationship("PlatformAccount", back_populates="client")


class Campaign(Base):
    __tablename__ = "campaigns"

    id = Column(Integer, primary_key=True)
    client_id = Column(Integer, ForeignKey("clients.id", ondelete="RESTRICT"), nullable=False)
    name = Column(String(255), nullable=False)
    goal = Column(Text)
    status = Column(String(30), default="planned")
    brief = Column(JSON, nullable=False)
    platforms = Column(JSON, nullable=False)
    duration_days = Column(Integer)
    start_date = Column(Date)
    end_date = Column(Date)
    posts_per_week = Column(Integer)
    content_mix = Column(JSON)
    target_audience = Column(Text)
    campaign_hashtags = Column(JSON)
    created_at = Column(DateTime, default=func.now())
    completed_at = Column(DateTime)
    operator_notes = Column(Text)

    client = relationship("Client", back_populates="campaigns")
    calendar_items = relationship("ContentCalendar", back_populates="campaign", cascade="all, delete-orphan")
    content_assets = relationship("ContentAsset", back_populates="campaign", cascade="all, delete-orphan")
    agent_tasks = relationship("AgentTask", back_populates="campaign", cascade="all, delete-orphan")
    approval_gates = relationship("ApprovalGate", back_populates="campaign", cascade="all, delete-orphan")


class ContentCalendar(Base):
    __tablename__ = "content_calendar"

    id = Column(Integer, primary_key=True)
    campaign_id = Column(Integer, ForeignKey("campaigns.id", ondelete="CASCADE"), nullable=False)
    client_id = Column(Integer, ForeignKey("clients.id", ondelete="RESTRICT"), nullable=False)
    platform = Column(String(50), nullable=False)
    content_type = Column(String(50), nullable=False)
    scheduled_for = Column(DateTime, nullable=False)
    status = Column(String(30), default="planned")
    asset_id = Column(Integer, ForeignKey("content_assets.id", ondelete="SET NULL"))
    topic = Column(Text)
    notes = Column(Text)
    created_at = Column(DateTime, default=func.now())

    campaign = relationship("Campaign", back_populates="calendar_items")
    client = relationship("Client")
    asset = relationship("ContentAsset", foreign_keys=[asset_id])
    scheduled_posts = relationship("ScheduledPost", back_populates="calendar_item", cascade="all, delete-orphan")
    agent_tasks = relationship("AgentTask", back_populates="calendar_item")


class ContentAsset(Base):
    __tablename__ = "content_assets"

    id = Column(Integer, primary_key=True)
    campaign_id = Column(Integer, ForeignKey("campaigns.id", ondelete="CASCADE"), nullable=False)
    client_id = Column(Integer, ForeignKey("clients.id", ondelete="RESTRICT"), nullable=False)
    asset_type = Column(String(20), nullable=False)
    content_type = Column(String(50))
    title = Column(String(255))
    text_content = Column(Text)
    storage_path = Column(Text)
    storage_bucket = Column(String(100))
    file_size_bytes = Column(BigInteger)
    duration_seconds = Column(Integer)
    width = Column(Integer)
    height = Column(Integer)
    format = Column(String(20))
    platform_versions = Column(JSON)
    status = Column(String(30), default="draft")
    brand_check_passed = Column(Boolean)
    brand_check_notes = Column(Text)
    generation_prompt = Column(Text)
    generation_model = Column(String(100))
    tokens_used = Column(Integer)
    cost_usd = Column(Numeric(8, 6))
    created_by_agent = Column(String(100))
    created_at = Column(DateTime, default=func.now())

    campaign = relationship("Campaign", back_populates="content_assets")
    client = relationship("Client")
    versions = relationship("AssetVersion", back_populates="asset", cascade="all, delete-orphan")


class AssetVersion(Base):
    __tablename__ = "asset_versions"

    id = Column(Integer, primary_key=True)
    asset_id = Column(Integer, ForeignKey("content_assets.id", ondelete="CASCADE"), nullable=False)
    version_number = Column(Integer, nullable=False)
    storage_path = Column(Text)
    change_description = Column(Text)
    changed_by_agent = Column(String(100))
    created_at = Column(DateTime, default=func.now())

    asset = relationship("ContentAsset", back_populates="versions")


class BrandGuidelines(Base):
    __tablename__ = "brand_guidelines"

    id = Column(Integer, primary_key=True)
    client_id = Column(Integer, ForeignKey("clients.id", ondelete="CASCADE"), nullable=False, unique=True)
    primary_colour = Column(String(7))
    secondary_colour = Column(String(7))
    accent_colour = Column(String(7))
    background_colour = Column(String(7))
    logo_path = Column(Text)
    logo_dark_path = Column(Text)
    heading_font = Column(String(100))
    body_font = Column(String(100))
    tone_keywords = Column(JSON)
    forbidden_words = Column(JSON)
    competitor_names = Column(JSON)
    required_elements = Column(JSON)
    image_style_notes = Column(Text)
    copy_style_notes = Column(Text)
    voice_id = Column(String(100))
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    client = relationship("Client", back_populates="brand_guidelines")


class PlatformAccount(Base):
    __tablename__ = "platform_accounts"

    id = Column(Integer, primary_key=True)
    client_id = Column(Integer, ForeignKey("clients.id", ondelete="RESTRICT"), nullable=False)
    platform = Column(String(50), nullable=False)
    account_name = Column(String(255))
    account_id = Column(String(255))
    page_id = Column(String(255))
    access_token = Column(Text)
    refresh_token = Column(Text)
    token_expires_at = Column(DateTime)
    scopes = Column(JSON)
    is_active = Column(Boolean, default=True)
    last_verified_at = Column(DateTime)
    connected_at = Column(DateTime, default=func.now())

    __table_args__ = (
        UniqueConstraint("client_id", "platform", "account_id", name="uq_client_platform_account"),
    )

    client = relationship("Client", back_populates="platform_accounts")
    scheduled_posts = relationship("ScheduledPost", back_populates="platform_account")


class ScheduledPost(Base):
    __tablename__ = "scheduled_posts"

    id = Column(Integer, primary_key=True)
    calendar_id = Column(Integer, ForeignKey("content_calendar.id", ondelete="RESTRICT"), nullable=False)
    asset_id = Column(Integer, ForeignKey("content_assets.id", ondelete="RESTRICT"), nullable=False)
    platform_account_id = Column(Integer, ForeignKey("platform_accounts.id", ondelete="RESTRICT"), nullable=False)
    scheduled_for = Column(DateTime, nullable=False)
    caption = Column(Text)
    hashtags = Column(JSON)
    first_comment = Column(Text)
    status = Column(String(20), default="queued")
    celery_task_id = Column(String(255))
    created_at = Column(DateTime, default=func.now())

    calendar_item = relationship("ContentCalendar", back_populates="scheduled_posts")
    asset = relationship("ContentAsset")
    platform_account = relationship("PlatformAccount", back_populates="scheduled_posts")
    published_post = relationship("PublishedPost", back_populates="scheduled_post", uselist=False)


class PublishedPost(Base):
    __tablename__ = "published_posts"

    id = Column(Integer, primary_key=True)
    scheduled_post_id = Column(Integer, ForeignKey("scheduled_posts.id", ondelete="RESTRICT"), nullable=False)
    platform = Column(String(50))
    platform_post_id = Column(String(255))
    post_url = Column(Text)
    published_at = Column(DateTime)
    raw_response = Column(JSON)

    scheduled_post = relationship("ScheduledPost", back_populates="published_post")
    analytics = relationship("PostAnalytics", back_populates="published_post", cascade="all, delete-orphan")


class PostAnalytics(Base):
    __tablename__ = "post_analytics"

    id = Column(Integer, primary_key=True)
    published_post_id = Column(Integer, ForeignKey("published_posts.id", ondelete="CASCADE"), nullable=False)
    snapshot_type = Column(String(20))
    pulled_at = Column(DateTime)
    impressions = Column(BigInteger)
    reach = Column(BigInteger)
    likes = Column(Integer)
    comments = Column(Integer)
    shares = Column(Integer)
    saves = Column(Integer)
    clicks = Column(Integer)
    video_views = Column(BigInteger)
    video_watch_time_sec = Column(BigInteger)
    engagement_rate = Column(Numeric(6, 4))
    platform_raw = Column(JSON)

    published_post = relationship("PublishedPost", back_populates="analytics")


class AgentTask(Base):
    __tablename__ = "agent_tasks"

    id = Column(Integer, primary_key=True)
    campaign_id = Column(Integer, ForeignKey("campaigns.id", ondelete="CASCADE"), nullable=False)
    calendar_id = Column(Integer, ForeignKey("content_calendar.id", ondelete="CASCADE"))
    agent_name = Column(String(100))
    pipeline_order = Column(Integer)
    status = Column(String(20), default="pending")
    input_data = Column(JSON)
    output_data = Column(JSON)
    tokens_used = Column(Integer)
    cost_usd = Column(Numeric(8, 6))
    started_at = Column(DateTime)
    completed_at = Column(DateTime)
    error = Column(Text)
    retry_count = Column(Integer, default=0)
    celery_task_id = Column(String(255))

    campaign = relationship("Campaign", back_populates="agent_tasks")
    calendar_item = relationship("ContentCalendar", back_populates="agent_tasks")


class ApprovalGate(Base):
    __tablename__ = "approval_gates"

    id = Column(Integer, primary_key=True)
    campaign_id = Column(Integer, ForeignKey("campaigns.id", ondelete="CASCADE"), nullable=False)
    gate_name = Column(String(100))
    pipeline_order = Column(Integer)
    status = Column(String(20), default="pending")
    notes = Column(Text)
    created_at = Column(DateTime, default=func.now())
    reviewed_at = Column(DateTime)
    reviewed_by = Column(String(100))

    campaign = relationship("Campaign", back_populates="approval_gates")

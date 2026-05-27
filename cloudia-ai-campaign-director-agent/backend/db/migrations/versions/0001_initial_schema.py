"""Initial schema — all tables

Revision ID: 0001
Revises:
Create Date: 2026-05-25
"""
from typing import Union
from alembic import op
import sqlalchemy as sa

revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "clients",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("industry", sa.String(100)),
        sa.Column("business_type", sa.String(100)),
        sa.Column("target_audience", sa.Text),
        sa.Column("usp", sa.Text),
        sa.Column("tone_of_voice", sa.String(100)),
        sa.Column("brand_colours", sa.JSON),
        sa.Column("city", sa.String(100)),
        sa.Column("country", sa.String(100), server_default="South Africa"),
        sa.Column("is_active", sa.Boolean, server_default="true"),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
    )

    op.create_table(
        "campaigns",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("client_id", sa.Integer, sa.ForeignKey("clients.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("goal", sa.Text),
        sa.Column("status", sa.String(30), server_default="planned"),
        sa.Column("brief", sa.JSON, nullable=False),
        sa.Column("platforms", sa.JSON, nullable=False),
        sa.Column("duration_days", sa.Integer),
        sa.Column("start_date", sa.Date),
        sa.Column("end_date", sa.Date),
        sa.Column("posts_per_week", sa.Integer),
        sa.Column("content_mix", sa.JSON),
        sa.Column("target_audience", sa.Text),
        sa.Column("campaign_hashtags", sa.JSON),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
        sa.Column("completed_at", sa.DateTime),
        sa.Column("operator_notes", sa.Text),
    )

    op.create_table(
        "content_assets",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("campaign_id", sa.Integer, sa.ForeignKey("campaigns.id", ondelete="CASCADE"), nullable=False),
        sa.Column("client_id", sa.Integer, sa.ForeignKey("clients.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("asset_type", sa.String(20), nullable=False),
        sa.Column("content_type", sa.String(50)),
        sa.Column("title", sa.String(255)),
        sa.Column("text_content", sa.Text),
        sa.Column("storage_path", sa.Text),
        sa.Column("storage_bucket", sa.String(100)),
        sa.Column("file_size_bytes", sa.BigInteger),
        sa.Column("duration_seconds", sa.Integer),
        sa.Column("width", sa.Integer),
        sa.Column("height", sa.Integer),
        sa.Column("format", sa.String(20)),
        sa.Column("platform_versions", sa.JSON),
        sa.Column("status", sa.String(30), server_default="draft"),
        sa.Column("brand_check_passed", sa.Boolean),
        sa.Column("brand_check_notes", sa.Text),
        sa.Column("generation_prompt", sa.Text),
        sa.Column("generation_model", sa.String(100)),
        sa.Column("tokens_used", sa.Integer),
        sa.Column("cost_usd", sa.Numeric(8, 6)),
        sa.Column("created_by_agent", sa.String(100)),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
    )

    op.create_table(
        "content_calendar",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("campaign_id", sa.Integer, sa.ForeignKey("campaigns.id", ondelete="CASCADE"), nullable=False),
        sa.Column("client_id", sa.Integer, sa.ForeignKey("clients.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("platform", sa.String(50), nullable=False),
        sa.Column("content_type", sa.String(50), nullable=False),
        sa.Column("scheduled_for", sa.DateTime, nullable=False),
        sa.Column("status", sa.String(30), server_default="planned"),
        sa.Column("asset_id", sa.Integer, sa.ForeignKey("content_assets.id", ondelete="SET NULL")),
        sa.Column("topic", sa.Text),
        sa.Column("notes", sa.Text),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
    )

    op.create_table(
        "asset_versions",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("asset_id", sa.Integer, sa.ForeignKey("content_assets.id", ondelete="CASCADE"), nullable=False),
        sa.Column("version_number", sa.Integer, nullable=False),
        sa.Column("storage_path", sa.Text),
        sa.Column("change_description", sa.Text),
        sa.Column("changed_by_agent", sa.String(100)),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
    )

    op.create_table(
        "brand_guidelines",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("client_id", sa.Integer, sa.ForeignKey("clients.id", ondelete="CASCADE"), nullable=False, unique=True),
        sa.Column("primary_colour", sa.String(7)),
        sa.Column("secondary_colour", sa.String(7)),
        sa.Column("accent_colour", sa.String(7)),
        sa.Column("background_colour", sa.String(7)),
        sa.Column("logo_path", sa.Text),
        sa.Column("logo_dark_path", sa.Text),
        sa.Column("heading_font", sa.String(100)),
        sa.Column("body_font", sa.String(100)),
        sa.Column("tone_keywords", sa.JSON),
        sa.Column("forbidden_words", sa.JSON),
        sa.Column("competitor_names", sa.JSON),
        sa.Column("required_elements", sa.JSON),
        sa.Column("image_style_notes", sa.Text),
        sa.Column("copy_style_notes", sa.Text),
        sa.Column("voice_id", sa.String(100)),
        sa.Column("updated_at", sa.DateTime, server_default=sa.func.now()),
    )

    op.create_table(
        "platform_accounts",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("client_id", sa.Integer, sa.ForeignKey("clients.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("platform", sa.String(50), nullable=False),
        sa.Column("account_name", sa.String(255)),
        sa.Column("account_id", sa.String(255)),
        sa.Column("page_id", sa.String(255)),
        sa.Column("access_token", sa.Text),
        sa.Column("refresh_token", sa.Text),
        sa.Column("token_expires_at", sa.DateTime),
        sa.Column("scopes", sa.JSON),
        sa.Column("is_active", sa.Boolean, server_default="true"),
        sa.Column("last_verified_at", sa.DateTime),
        sa.Column("connected_at", sa.DateTime, server_default=sa.func.now()),
        sa.UniqueConstraint("client_id", "platform", "account_id", name="uq_client_platform_account"),
    )

    op.create_table(
        "scheduled_posts",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("calendar_id", sa.Integer, sa.ForeignKey("content_calendar.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("asset_id", sa.Integer, sa.ForeignKey("content_assets.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("platform_account_id", sa.Integer, sa.ForeignKey("platform_accounts.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("scheduled_for", sa.DateTime, nullable=False),
        sa.Column("caption", sa.Text),
        sa.Column("hashtags", sa.JSON),
        sa.Column("first_comment", sa.Text),
        sa.Column("status", sa.String(20), server_default="queued"),
        sa.Column("celery_task_id", sa.String(255)),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
    )

    op.create_table(
        "published_posts",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("scheduled_post_id", sa.Integer, sa.ForeignKey("scheduled_posts.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("platform", sa.String(50)),
        sa.Column("platform_post_id", sa.String(255)),
        sa.Column("post_url", sa.Text),
        sa.Column("published_at", sa.DateTime),
        sa.Column("raw_response", sa.JSON),
    )

    op.create_table(
        "post_analytics",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("published_post_id", sa.Integer, sa.ForeignKey("published_posts.id", ondelete="CASCADE"), nullable=False),
        sa.Column("snapshot_type", sa.String(20)),
        sa.Column("pulled_at", sa.DateTime),
        sa.Column("impressions", sa.BigInteger),
        sa.Column("reach", sa.BigInteger),
        sa.Column("likes", sa.Integer),
        sa.Column("comments", sa.Integer),
        sa.Column("shares", sa.Integer),
        sa.Column("saves", sa.Integer),
        sa.Column("clicks", sa.Integer),
        sa.Column("video_views", sa.BigInteger),
        sa.Column("video_watch_time_sec", sa.BigInteger),
        sa.Column("engagement_rate", sa.Numeric(6, 4)),
        sa.Column("platform_raw", sa.JSON),
    )

    op.create_table(
        "agent_tasks",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("campaign_id", sa.Integer, sa.ForeignKey("campaigns.id", ondelete="CASCADE"), nullable=False),
        sa.Column("calendar_id", sa.Integer, sa.ForeignKey("content_calendar.id", ondelete="CASCADE")),
        sa.Column("agent_name", sa.String(100)),
        sa.Column("pipeline_order", sa.Integer),
        sa.Column("status", sa.String(20), server_default="pending"),
        sa.Column("input_data", sa.JSON),
        sa.Column("output_data", sa.JSON),
        sa.Column("tokens_used", sa.Integer),
        sa.Column("cost_usd", sa.Numeric(8, 6)),
        sa.Column("started_at", sa.DateTime),
        sa.Column("completed_at", sa.DateTime),
        sa.Column("error", sa.Text),
        sa.Column("retry_count", sa.Integer, server_default="0"),
        sa.Column("celery_task_id", sa.String(255)),
    )

    op.create_table(
        "approval_gates",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("campaign_id", sa.Integer, sa.ForeignKey("campaigns.id", ondelete="CASCADE"), nullable=False),
        sa.Column("gate_name", sa.String(100)),
        sa.Column("pipeline_order", sa.Integer),
        sa.Column("status", sa.String(20), server_default="pending"),
        sa.Column("notes", sa.Text),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
        sa.Column("reviewed_at", sa.DateTime),
        sa.Column("reviewed_by", sa.String(100)),
    )


def downgrade() -> None:
    for table in [
        "approval_gates", "agent_tasks", "post_analytics", "published_posts",
        "scheduled_posts", "platform_accounts", "brand_guidelines",
        "asset_versions", "content_calendar", "content_assets",
        "campaigns", "clients",
    ]:
        op.drop_table(table)

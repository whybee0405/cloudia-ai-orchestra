"""Initial schema — create all base tables

Revision ID: 0000
Revises:
Create Date: 2026-05-31
"""
from typing import Union
from alembic import op
import sqlalchemy as sa

revision: str = "0000"
down_revision: Union[str, None] = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "clients",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("industry", sa.String(100), nullable=True),
        sa.Column("business_type", sa.String(50), nullable=True),
        sa.Column("target_audience", sa.Text(), nullable=True),
        sa.Column("usp", sa.Text(), nullable=True),
        sa.Column("tone_of_voice", sa.String(50), nullable=True),
        sa.Column("brand_colours", sa.JSON(), nullable=True),
        sa.Column("brand_fonts", sa.JSON(), nullable=True),
        sa.Column("logo_url", sa.Text(), nullable=True),
        sa.Column("contact_email", sa.String(255), nullable=True),
        sa.Column("contact_phone", sa.String(50), nullable=True),
        sa.Column("address", sa.Text(), nullable=True),
        sa.Column("city", sa.String(100), nullable=True),
        sa.Column("country", sa.String(100), nullable=False, server_default="South Africa"),
        sa.Column("website_url", sa.Text(), nullable=True),
        sa.Column("social_links", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "projects",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("client_id", sa.Integer(), nullable=False),
        sa.Column("platform", sa.String(20), nullable=True),
        sa.Column("status", sa.String(30), nullable=False, server_default="planned"),
        sa.Column("brief", sa.JSON(), nullable=True),
        sa.Column("pipeline_plan", sa.JSON(), nullable=True),
        sa.Column("site_url", sa.Text(), nullable=True),
        sa.Column("admin_url", sa.Text(), nullable=True),
        sa.Column("credentials", sa.JSON(), nullable=True),
        sa.Column("estimated_pages", sa.Integer(), nullable=True),
        sa.Column("actual_pages", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
        sa.Column("operator_notes", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["client_id"], ["clients.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_projects_client_id", "projects", ["client_id"])
    op.create_index("ix_projects_status", "projects", ["status"])

    op.create_table(
        "agent_tasks",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("project_id", sa.Integer(), nullable=False),
        sa.Column("agent_name", sa.String(100), nullable=False),
        sa.Column("pipeline_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("input_data", sa.JSON(), nullable=True),
        sa.Column("output_data", sa.JSON(), nullable=True),
        sa.Column("tokens_used", sa.Integer(), nullable=True),
        sa.Column("cost_usd", sa.Numeric(8, 6), nullable=True),
        sa.Column("started_at", sa.DateTime(), nullable=True),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("retry_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("celery_task_id", sa.String(255), nullable=True),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_agent_tasks_project_id", "agent_tasks", ["project_id"])
    op.create_index("ix_agent_tasks_status", "agent_tasks", ["status"])
    op.create_index("ix_agent_tasks_celery_task_id", "agent_tasks", ["celery_task_id"])

    op.create_table(
        "approval_gates",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("project_id", sa.Integer(), nullable=False),
        sa.Column("gate_name", sa.String(100), nullable=False),
        sa.Column("pipeline_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("reviewed_at", sa.DateTime(), nullable=True),
        sa.Column("reviewed_by", sa.String(100), nullable=True),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_approval_gates_project_id", "approval_gates", ["project_id"])
    op.create_index("ix_approval_gates_status", "approval_gates", ["status"])

    op.create_table(
        "generated_content",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("project_id", sa.Integer(), nullable=False),
        sa.Column("page_slug", sa.String(255), nullable=True),
        sa.Column("content_type", sa.String(50), nullable=True),
        sa.Column("title", sa.String(255), nullable=True),
        sa.Column("h1", sa.String(255), nullable=True),
        sa.Column("body_content", sa.Text(), nullable=True),
        sa.Column("cta_text", sa.String(100), nullable=True),
        sa.Column("meta_title", sa.String(60), nullable=True),
        sa.Column("meta_description", sa.String(160), nullable=True),
        sa.Column("schema_markup", sa.JSON(), nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="draft"),
        sa.Column("revision_notes", sa.Text(), nullable=True),
        sa.Column("platform_id", sa.String(100), nullable=True),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_generated_content_project_id", "generated_content", ["project_id"])

    op.create_table(
        "project_media",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("project_id", sa.Integer(), nullable=False),
        sa.Column("page_slug", sa.String(255), nullable=True),
        sa.Column("image_purpose", sa.String(100), nullable=True),
        sa.Column("source", sa.String(50), nullable=True),
        sa.Column("source_id", sa.String(255), nullable=True),
        sa.Column("source_url", sa.Text(), nullable=True),
        sa.Column("local_path", sa.Text(), nullable=True),
        sa.Column("optimised_path", sa.Text(), nullable=True),
        sa.Column("alt_text", sa.Text(), nullable=True),
        sa.Column("attribution", sa.Text(), nullable=True),
        sa.Column("platform_media_id", sa.String(100), nullable=True),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_project_media_project_id", "project_media", ["project_id"])

    op.create_table(
        "platform_credentials",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("client_id", sa.Integer(), nullable=False),
        sa.Column("platform", sa.String(20), nullable=False),
        sa.Column("site_url", sa.Text(), nullable=True),
        sa.Column("api_url", sa.Text(), nullable=True),
        sa.Column("shop_name", sa.String(255), nullable=True),
        sa.Column("api_version", sa.String(20), nullable=True, server_default="2024-01"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("last_verified_at", sa.DateTime(), nullable=True),
        sa.Column("access_token_encrypted", sa.String(2048), nullable=True),
        sa.Column("app_password_encrypted", sa.String(2048), nullable=True),
        sa.ForeignKeyConstraint(["client_id"], ["clients.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_platform_credentials_client_id", "platform_credentials", ["client_id"])


def downgrade() -> None:
    op.drop_table("platform_credentials")
    op.drop_table("project_media")
    op.drop_table("generated_content")
    op.drop_table("approval_gates")
    op.drop_table("agent_tasks")
    op.drop_table("projects")
    op.drop_table("clients")

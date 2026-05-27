"""Initial schema — clients, brand_dna, icp_personas

Revision ID: 001
Revises:
Create Date: 2026-05-27
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "clients",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("website_url", sa.String(500)),
        sa.Column("industry", sa.String(100)),
        sa.Column("sub_industry", sa.String(100)),
        sa.Column("location", sa.String(200)),
        sa.Column("timezone", sa.String(50), server_default="Africa/Johannesburg"),
        sa.Column("founded_year", sa.Integer()),
        sa.Column("is_active", sa.Boolean(), server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "brand_dna",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("client_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("clients.id", ondelete="CASCADE"), nullable=False, unique=True),
        sa.Column("tagline", sa.String(500)),
        sa.Column("tone", sa.String(50)),
        sa.Column("language_style", sa.Text()),
        sa.Column("personality_traits", postgresql.JSON()),
        sa.Column("primary_color", sa.String(7)),
        sa.Column("secondary_colors", postgresql.JSON()),
        sa.Column("accent_color", sa.String(7)),
        sa.Column("heading_font", sa.String(100)),
        sa.Column("body_font", sa.String(100)),
        sa.Column("logo_url", sa.String(500)),
        sa.Column("visual_style", sa.String(100)),
        sa.Column("usps", postgresql.JSON()),
        sa.Column("pain_points_addressed", postgresql.JSON()),
        sa.Column("key_messages", postgresql.JSON()),
        sa.Column("competitors", postgresql.JSON()),
        sa.Column("differentiators", postgresql.JSON()),
        sa.Column("enriched_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "icp_personas",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("client_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("clients.id", ondelete="CASCADE"), nullable=False),
        sa.Column("persona_name", sa.String(200), nullable=False),
        sa.Column("age_min", sa.Integer()),
        sa.Column("age_max", sa.Integer()),
        sa.Column("gender_skew", sa.String(50)),
        sa.Column("income_bracket", sa.String(50)),
        sa.Column("location_type", sa.String(50)),
        sa.Column("interests", postgresql.JSON()),
        sa.Column("values", postgresql.JSON()),
        sa.Column("pain_points", postgresql.JSON()),
        sa.Column("goals", postgresql.JSON()),
        sa.Column("preferred_channels", postgresql.JSON()),
        sa.Column("seo_keywords", postgresql.JSON()),
        sa.Column("vocabulary", postgresql.JSON()),
        sa.Column("order", sa.Integer(), server_default="1"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_index("ix_icp_personas_client_id", "icp_personas", ["client_id"])


def downgrade() -> None:
    op.drop_table("icp_personas")
    op.drop_table("brand_dna")
    op.drop_table("clients")

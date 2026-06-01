"""Add brand_dna_access_log table for usage auditing

Revision ID: 002
Revises: 001
Create Date: 2026-06-01
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "002"
down_revision: Union[str, None] = "001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "brand_dna_access_log",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "client_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("clients.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "accessed_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("accessed_by_service", sa.String(50), nullable=True),
        sa.Column("accessed_by_agent", sa.String(100), nullable=True),
        sa.Column("persona_ids_used", sa.JSON(), nullable=True),
        sa.Column("brand_dna_version_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index(
        "ix_brand_dna_access_log_client_id",
        "brand_dna_access_log",
        ["client_id"],
    )
    op.create_index(
        "ix_brand_dna_access_log_accessed_at",
        "brand_dna_access_log",
        ["accessed_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_brand_dna_access_log_accessed_at", "brand_dna_access_log")
    op.drop_index("ix_brand_dna_access_log_client_id", "brand_dna_access_log")
    op.drop_table("brand_dna_access_log")

"""Add brand_dna_client_id to accounts

Revision ID: 0002
Revises: 0001
Create Date: 2026-05-27
"""
from typing import Union
from alembic import op
import sqlalchemy as sa

revision: str = "0002"
down_revision: Union[str, None] = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("accounts", sa.Column("brand_dna_client_id", sa.String(36), nullable=True))


def downgrade() -> None:
    op.drop_column("accounts", "brand_dna_client_id")

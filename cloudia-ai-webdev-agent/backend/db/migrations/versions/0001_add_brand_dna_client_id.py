"""Add brand_dna_client_id to clients

Revision ID: 0001
Revises:
Create Date: 2026-05-27
"""
from typing import Union
from alembic import op
import sqlalchemy as sa

revision: str = "0001"
down_revision: Union[str, None] = "0000"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("clients", sa.Column("brand_dna_client_id", sa.String(36), nullable=True))


def downgrade() -> None:
    op.drop_column("clients", "brand_dna_client_id")

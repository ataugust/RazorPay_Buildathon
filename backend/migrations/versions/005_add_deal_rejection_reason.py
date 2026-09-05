"""Persist optional buyer rejection feedback.

Revision ID: 005_add_deal_rejection_reason
Revises: 004_create_deals_table
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "005_add_deal_rejection_reason"
down_revision: Union[str, None] = "004_create_deals_table"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("deals", sa.Column("rejection_reason", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("deals", "rejection_reason")

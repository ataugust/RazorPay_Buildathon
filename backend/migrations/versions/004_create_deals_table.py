"""Create persistent deal state for synchronized buyer and merchant views.

Revision ID: 004_create_deals_table
Revises: 003_create_audit_events_table
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "004_create_deals_table"
down_revision: Union[str, None] = "003_create_audit_events_table"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "deals",
        sa.Column("transaction_id", sa.String(length=100), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("prompt", sa.Text(), nullable=False),
        sa.Column("product_query", sa.String(length=255), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.Column("max_budget_paise", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=50), nullable=False),
        sa.Column("outcome_type", sa.String(length=50), nullable=True),
        sa.Column("recovered", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("intelligence_json", sa.JSON(), nullable=False),
        sa.Column("initial_offer_json", sa.JSON(), nullable=True),
        sa.Column("current_offer_json", sa.JSON(), nullable=True),
        sa.Column("candidates_json", sa.JSON(), nullable=False),
        sa.Column("gate_results_json", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("transaction_id"),
    )
    op.create_index(op.f("ix_deals_status"), "deals", ["status"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_deals_status"), table_name="deals")
    op.drop_table("deals")


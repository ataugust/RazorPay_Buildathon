"""Persist agent-to-agent messages and explicit merchant responses.

Revision ID: 006_add_agent_messages
Revises: 005_add_deal_rejection_reason
"""

from alembic import op
import sqlalchemy as sa


revision = "006_add_agent_messages"
down_revision = "005_add_deal_rejection_reason"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("deals", sa.Column("merchant_response_json", sa.JSON(), nullable=True))
    op.create_table(
        "agent_messages",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("transaction_id", sa.String(length=100), nullable=False),
        sa.Column("sender", sa.String(length=50), nullable=False),
        sa.Column("recipient", sa.String(length=50), nullable=False),
        sa.Column("message_type", sa.String(length=50), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("reason_code", sa.String(length=50), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["transaction_id"], ["deals.transaction_id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_agent_messages_transaction_id", "agent_messages", ["transaction_id"])


def downgrade() -> None:
    op.drop_index("ix_agent_messages_transaction_id", table_name="agent_messages")
    op.drop_table("agent_messages")
    op.drop_column("deals", "merchant_response_json")

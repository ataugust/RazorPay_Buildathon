"""Persist buyer drafts, ownership, and communication events."""
from alembic import op
import sqlalchemy as sa
revision = "007_buyer_drafts"
down_revision = "006_add_agent_messages"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("deals") as batch:
        batch.alter_column("max_budget_paise", existing_type=sa.Integer(), nullable=True)
    op.create_table("buyer_drafts",
        sa.Column("id", sa.String(80), primary_key=True),
        sa.Column("owner", sa.String(80), nullable=False),
        sa.Column("prompt", sa.Text(), nullable=False),
        sa.Column("state", sa.String(40), nullable=False),
        sa.Column("data", sa.JSON(), nullable=False),
        sa.Column("events", sa.JSON(), nullable=False),
        sa.Column("transaction_id", sa.String(100), nullable=True))
    op.create_index("ix_buyer_drafts_owner", "buyer_drafts", ["owner"])


def downgrade():
    op.drop_table("buyer_drafts")

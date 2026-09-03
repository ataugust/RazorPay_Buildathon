"""Create audit_events table

Revision ID: 003_create_audit_events_table
Revises: 002_create_merchant_policies_table
Create Date: 2026-09-03 12:30:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = '003_create_audit_events_table'
down_revision: Union[str, None] = '002_create_merchant_policies_table'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    op.create_table(
        'audit_events',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('transaction_id', sa.String(length=100), nullable=False),
        sa.Column('timestamp', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.Column('component', sa.String(length=100), nullable=False),
        sa.Column('event_type', sa.String(length=100), nullable=False),
        sa.Column('status', sa.String(length=20), nullable=False),
        sa.Column('message', sa.Text(), nullable=False),
        sa.Column('metadata_json', sa.JSON(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_audit_events_transaction_id'), 'audit_events', ['transaction_id'], unique=False)

def downgrade() -> None:
    op.drop_index(op.f('ix_audit_events_transaction_id'), table_name='audit_events')
    op.drop_table('audit_events')

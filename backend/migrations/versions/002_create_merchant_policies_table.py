"""Create merchant_policies table

Revision ID: 002_create_merchant_policies_table
Revises: 001_create_products_table
Create Date: 2026-09-03 12:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = '002_create_merchant_policies_table'
down_revision: Union[str, None] = '001_create_products_table'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    op.create_table(
        'merchant_policies',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('policy_name', sa.String(length=100), nullable=False),
        sa.Column('min_margin_percent', sa.Float(), nullable=False, server_default=sa.text('15.0')),
        sa.Column('max_discount_percent', sa.Float(), nullable=False, server_default=sa.text('20.0')),
        sa.Column('allow_bundles', sa.Boolean(), nullable=False, server_default=sa.text('1')),
        sa.Column('allow_substitutions', sa.Boolean(), nullable=False, server_default=sa.text('1')),
        sa.Column('weight_margin', sa.Float(), nullable=False, server_default=sa.text('0.4')),
        sa.Column('weight_revenue', sa.Float(), nullable=False, server_default=sa.text('0.3')),
        sa.Column('weight_overstock', sa.Float(), nullable=False, server_default=sa.text('0.2')),
        sa.Column('weight_discount_penalty', sa.Float(), nullable=False, server_default=sa.text('0.1')),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.text('1')),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_merchant_policies_policy_name'), 'merchant_policies', ['policy_name'], unique=True)

def downgrade() -> None:
    op.drop_index(op.f('ix_merchant_policies_policy_name'), table_name='merchant_policies')
    op.drop_table('merchant_policies')

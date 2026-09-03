"""Create products table

Revision ID: 001_create_products_table
Revises: 
Create Date: 2026-09-01 12:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = '001_create_products_table'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    op.create_table(
        'products',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('sku', sa.String(length=100), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('brand', sa.String(length=100), nullable=True),
        sa.Column('model', sa.String(length=100), nullable=True),
        sa.Column('category', sa.String(length=100), nullable=False),
        sa.Column('selling_price_rupees', sa.Integer(), nullable=False),
        sa.Column('cost_price_rupees', sa.Integer(), nullable=False),
        sa.Column('stock_quantity', sa.Integer(), nullable=False),
        sa.Column('cpu_brand', sa.String(length=50), nullable=True),
        sa.Column('cpu_tier', sa.String(length=50), nullable=True),
        sa.Column('cpu_generation', sa.String(length=50), nullable=True),
        sa.Column('ram_gb', sa.Integer(), nullable=True),
        sa.Column('storage_gb', sa.Integer(), nullable=True),
        sa.Column('storage_type', sa.String(length=50), nullable=True),
        sa.Column('display_inches', sa.Float(), nullable=True),
        sa.Column('resolution', sa.String(length=50), nullable=True),
        sa.Column('operating_system', sa.String(length=100), nullable=True),
        sa.Column('is_overstock', sa.Boolean(), server_default=sa.text('0'), nullable=False),
        sa.Column('is_active', sa.Boolean(), server_default=sa.text('1'), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_products_sku'), 'products', ['sku'], unique=True)

def downgrade() -> None:
    op.drop_index(op.f('ix_products_sku'), table_name='products')
    op.drop_table('products')

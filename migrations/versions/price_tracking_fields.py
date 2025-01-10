"""add price tracking fields

Revision ID: price_tracking_fields
Revises: 311758c1dbcc
Create Date: 2025-01-10 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'price_tracking_fields'
down_revision = '311758c1dbcc'  # Updated to the actual last migration ID
branch_labels = None
depends_on = None

def upgrade():
    # Add new columns to Product table
    op.add_column('product', sa.Column('last_purchase_price', sa.Float(), nullable=True))
    op.add_column('product', sa.Column('price_trend', sa.String(20), nullable=True))
    op.add_column('product', sa.Column('price_alert_threshold', sa.Float(), nullable=True))
    op.add_column('product', sa.Column('last_price_update', sa.DateTime(), nullable=True))
    op.add_column('product', sa.Column('price_update_notes', sa.Text(), nullable=True))

    # Add new columns to InvoiceItem table
    op.add_column('invoice_item', sa.Column('previous_cost_price', sa.Float(), nullable=True))
    op.add_column('invoice_item', sa.Column('price_difference', sa.Float(), nullable=True))
    op.add_column('invoice_item', sa.Column('price_difference_percentage', sa.Float(), nullable=True))
    op.add_column('invoice_item', sa.Column('price_status', sa.String(50), nullable=True))
    op.add_column('invoice_item', sa.Column('requires_approval', sa.Boolean(), nullable=True))
    op.add_column('invoice_item', sa.Column('approval_notes', sa.Text(), nullable=True))

def downgrade():
    # Remove columns from Product table
    op.drop_column('product', 'last_purchase_price')
    op.drop_column('product', 'price_trend')
    op.drop_column('product', 'price_alert_threshold')
    op.drop_column('product', 'last_price_update')
    op.drop_column('product', 'price_update_notes')

    # Remove columns from InvoiceItem table
    op.drop_column('invoice_item', 'previous_cost_price')
    op.drop_column('invoice_item', 'price_difference')
    op.drop_column('invoice_item', 'price_difference_percentage')
    op.drop_column('invoice_item', 'price_status')
    op.drop_column('invoice_item', 'requires_approval')
    op.drop_column('invoice_item', 'approval_notes') 
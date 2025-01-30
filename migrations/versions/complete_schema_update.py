"""Complete schema update for enhanced invoice processing

Revision ID: complete_schema_update
Revises: dc51250f37fe
Create Date: 2025-01-26 12:00:00.000000
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from sqlalchemy.engine.reflection import Inspector

# revision identifiers
revision = 'complete_schema_update'
down_revision = 'dc51250f37fe'
branch_labels = None
depends_on = None

def has_column(table, column):
    conn = op.get_bind()
    insp = Inspector.from_engine(conn)
    columns = [c['name'] for c in insp.get_columns(table)]
    return column in columns

def upgrade():
    # Add new fields to Invoice table if they don't exist
    if not has_column('invoice', 'supplier_id'):
        op.add_column('invoice', sa.Column('supplier_id', sa.Integer(), nullable=True))
    if not has_column('invoice', 'location'):
        op.add_column('invoice', sa.Column('location', sa.String(100)))
    if not has_column('invoice', 'area_type'):
        op.add_column('invoice', sa.Column('area_type', sa.String(50)))
    
    # Create foreign key if it doesn't exist
    # Note: This might fail if the constraint already exists
    try:
        op.create_foreign_key('fk_invoice_supplier', 'invoice', 'wholesaler',
                             ['supplier_id'], ['id'])
    except Exception:
        pass
    
    # Enhance ProcessingProgress table
    if not has_column('processing_progress', 'stage_details'):
        op.add_column('processing_progress', 
                     sa.Column('stage_details', postgresql.JSONB(astext_type=sa.Text())))
    if not has_column('processing_progress', 'ui_message'):
        op.add_column('processing_progress', 
                     sa.Column('ui_message', sa.Text()))
    
    # Create MarginSuggestion table if it doesn't exist
    conn = op.get_bind()
    insp = Inspector.from_engine(conn)
    if 'margin_suggestion' not in insp.get_table_names():
        op.create_table('margin_suggestion',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('invoice_id', sa.Integer(), nullable=False),
            sa.Column('category_name', sa.String(100), nullable=False),
            sa.Column('suggested_margin', sa.Float(), nullable=False),
            sa.Column('location', sa.String(100)),
            sa.Column('area_type', sa.String(50)),
            sa.Column('insights', postgresql.JSONB(astext_type=sa.Text())),
            sa.Column('created_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP')),
            sa.PrimaryKeyConstraint('id')
        )
        
        # Add indices for better performance
        op.create_index('ix_margin_suggestion_invoice_id', 'margin_suggestion', ['invoice_id'])
        op.create_index('ix_margin_suggestion_category', 'margin_suggestion', ['category_name'])
        
        # Create foreign key constraints
        op.create_foreign_key(
            'fk_margin_suggestion_invoice',
            'margin_suggestion', 'invoice',
            ['invoice_id'], ['id']
        )
    
    # Add fields to TempProduct table if they don't exist
    if not has_column('temp_product', 'margin'):
        op.add_column('temp_product', sa.Column('margin', sa.Float(), nullable=True))
    if not has_column('temp_product', 'selling_price'):
        op.add_column('temp_product', sa.Column('selling_price', sa.Float(), nullable=True))
    if not has_column('temp_product', 'status'):
        op.add_column('temp_product', sa.Column('status', sa.String(20), 
                                              server_default='pending'))
    
    # Add tracking fields to StaffPriceTask if they don't exist
    if not has_column('staff_price_task', 'label_printed'):
        op.add_column('staff_price_task', sa.Column('label_printed', sa.Boolean(), 
                                                   server_default='false'))
    if not has_column('staff_price_task', 'completion_notes'):
        op.add_column('staff_price_task', sa.Column('completion_notes', sa.Text()))
    
    # Create indices for performance if they don't exist
    try:
        op.create_index('ix_invoice_status', 'invoice', ['status'])
    except Exception:
        pass
    try:
        op.create_index('ix_invoice_processed_date', 'invoice', ['processed_date'])
    except Exception:
        pass
    try:
        op.create_index('ix_temp_product_status', 'temp_product', ['status'])
    except Exception:
        pass
    try:
        op.create_index('ix_staff_price_task_status', 'staff_price_task', ['status'])
    except Exception:
        pass

def downgrade():
    # Remove indices
    try:
        op.drop_index('ix_staff_price_task_status')
    except Exception:
        pass
    try:
        op.drop_index('ix_temp_product_status')
    except Exception:
        pass
    try:
        op.drop_index('ix_invoice_processed_date')
    except Exception:
        pass
    try:
        op.drop_index('ix_invoice_status')
    except Exception:
        pass
    
    # Remove StaffPriceTask columns if they exist
    if has_column('staff_price_task', 'completion_notes'):
        op.drop_column('staff_price_task', 'completion_notes')
    if has_column('staff_price_task', 'label_printed'):
        op.drop_column('staff_price_task', 'label_printed')
    
    # Remove TempProduct columns if they exist
    if has_column('temp_product', 'status'):
        op.drop_column('temp_product', 'status')
    if has_column('temp_product', 'selling_price'):
        op.drop_column('temp_product', 'selling_price')
    if has_column('temp_product', 'margin'):
        op.drop_column('temp_product', 'margin')
    
    # Drop MarginSuggestion table and related objects if they exist
    conn = op.get_bind()
    insp = Inspector.from_engine(conn)
    if 'margin_suggestion' in insp.get_table_names():
        op.drop_constraint('fk_margin_suggestion_invoice', 'margin_suggestion', type_='foreignkey')
        op.drop_index('ix_margin_suggestion_category')
        op.drop_index('ix_margin_suggestion_invoice_id')
        op.drop_table('margin_suggestion')
    
    # Remove ProcessingProgress columns if they exist
    if has_column('processing_progress', 'ui_message'):
        op.drop_column('processing_progress', 'ui_message')
    if has_column('processing_progress', 'stage_details'):
        op.drop_column('processing_progress', 'stage_details')
    
    # Remove Invoice columns and constraints if they exist
    try:
        op.drop_constraint('fk_invoice_supplier', 'invoice', type_='foreignkey')
    except Exception:
        pass
    if has_column('invoice', 'area_type'):
        op.drop_column('invoice', 'area_type')
    if has_column('invoice', 'location'):
        op.drop_column('invoice', 'location')
    if has_column('invoice', 'supplier_id'):
        op.drop_column('invoice', 'supplier_id')

"""Fix user password hash and add cloudinary fields

Revision ID: fix_user_and_invoice
Revises: 7715708f827c
Create Date: 2025-01-27 12:45:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import text


# revision identifiers, used by Alembic.
revision = 'fix_user_and_invoice'
down_revision = '7715708f827c'
branch_labels = None
depends_on = None


def upgrade():
    # Create a temporary column for password_hash
    op.add_column('user', sa.Column('temp_password_hash', sa.String(255), nullable=True))
    
    # Copy data from old column to new column
    op.execute('UPDATE "user" SET temp_password_hash = password_hash')
    
    # Drop old column
    with op.batch_alter_table('user', schema=None) as batch_op:
        batch_op.drop_column('password_hash')
    
    # Create new column with desired length
    op.add_column('user', sa.Column('password_hash', sa.String(255), nullable=True))
    
    # Copy data back
    op.execute('UPDATE "user" SET password_hash = temp_password_hash')
    
    # Drop temporary column
    with op.batch_alter_table('user', schema=None) as batch_op:
        batch_op.drop_column('temp_password_hash')


def downgrade():
    # Create a temporary column for password_hash
    op.add_column('user', sa.Column('temp_password_hash', sa.String(128), nullable=True))
    
    # Copy data from current column to temp (truncating if necessary)
    op.execute('UPDATE "user" SET temp_password_hash = substring(password_hash from 1 for 128)')
    
    # Drop current column
    with op.batch_alter_table('user', schema=None) as batch_op:
        batch_op.drop_column('password_hash')
    
    # Create new column with original length
    op.add_column('user', sa.Column('password_hash', sa.String(128), nullable=True))
    
    # Copy data back
    op.execute('UPDATE "user" SET password_hash = temp_password_hash')
    
    # Drop temporary column
    with op.batch_alter_table('user', schema=None) as batch_op:
        batch_op.drop_column('temp_password_hash')
    
    # Drop cloudinary columns from invoice table
    with op.batch_alter_table('invoice', schema=None) as batch_op:
        batch_op.drop_column('cloudinary_url')
        batch_op.drop_column('cloudinary_public_id')

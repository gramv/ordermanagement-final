"""Update TempProduct model with category_name

Revision ID: b1585e69cc0e
Revises: 719eb6ffd4f3
Create Date: 2025-01-26 12:14:49.986334

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'b1585e69cc0e'
down_revision = '719eb6ffd4f3'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('temp_product', schema=None) as batch_op:
        batch_op.add_column(sa.Column('category_name', sa.String(length=100), nullable=True))
        batch_op.drop_column('category')

    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('temp_product', schema=None) as batch_op:
        batch_op.add_column(sa.Column('category', sa.VARCHAR(length=100), autoincrement=False, nullable=True))
        batch_op.drop_column('category_name')

    # ### end Alembic commands ###

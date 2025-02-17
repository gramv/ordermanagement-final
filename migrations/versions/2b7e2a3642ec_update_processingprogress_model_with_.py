"""Update ProcessingProgress model with detailed tracking

Revision ID: 2b7e2a3642ec
Revises: b1585e69cc0e
Create Date: 2025-01-26 12:47:57.609020

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '2b7e2a3642ec'
down_revision = 'b1585e69cc0e'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('processing_progress', schema=None) as batch_op:
        batch_op.add_column(sa.Column('step_number', sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column('total_steps', sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column('detailed_status', sa.Text(), nullable=True))
        batch_op.add_column(sa.Column('estimated_time_remaining', sa.Integer(), nullable=True))

    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('processing_progress', schema=None) as batch_op:
        batch_op.drop_column('estimated_time_remaining')
        batch_op.drop_column('detailed_status')
        batch_op.drop_column('total_steps')
        batch_op.drop_column('step_number')

    # ### end Alembic commands ###

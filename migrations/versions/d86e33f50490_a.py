"""a

Revision ID: d86e33f50490
Revises: 16bd181c2ae8
Create Date: 2023-10-26 10:42:37.387238

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'd86e33f50490'
down_revision = '16bd181c2ae8'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('resource_allocation', schema=None) as batch_op:
        batch_op.add_column(sa.Column('sub_org_id', sa.Integer(), nullable=True))

    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('resource_allocation', schema=None) as batch_op:
        batch_op.drop_column('sub_org_id')

    # ### end Alembic commands ###

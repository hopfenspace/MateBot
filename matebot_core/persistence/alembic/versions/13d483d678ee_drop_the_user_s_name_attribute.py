"""drop the user's name attribute

Revision ID: 13d483d678ee
Revises: 88911f193d4c
Create Date: 2022-06-18 17:46:06.434846

"""
from alembic import op
import sqlalchemy as sa


revision = '13d483d678ee'
down_revision = '88911f193d4c'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('users') as batch_op:
        batch_op.drop_column('name')


def downgrade():
    with op.batch_alter_table('users') as batch_op:
        batch_op.add_column(sa.Column('name', sa.VARCHAR(length=255), nullable=True))

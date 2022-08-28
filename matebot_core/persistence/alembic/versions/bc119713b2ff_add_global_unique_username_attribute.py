"""add global unique username attribute

Revision ID: bc119713b2ff
Revises: 13d483d678ee
Create Date: 2022-08-28 03:18:40.297187

"""
from alembic import op
import sqlalchemy as sa


revision = 'bc119713b2ff'
down_revision = '13d483d678ee'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('users') as batch_op:
        batch_op.add_column(sa.Column('name', sa.String(length=255), nullable=False))
        batch_op.create_unique_constraint('users_name_unique_constraint', ['name'])


def downgrade():
    with op.batch_alter_table('users') as batch_op:
        batch_op.drop_constraint('users_name_unique_constraint', type_='unique')
        batch_op.drop_column('name')

"""add user to poll

Revision ID: 88911f193d4c
Revises: affe444aad73
Create Date: 2022-06-18 02:09:13.184785

"""
from alembic import op
import sqlalchemy as sa


revision = '88911f193d4c'
down_revision = 'affe444aad73'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("polls") as batch_op:
        batch_op.add_column(sa.Column('variant', sa.Enum('GET_INTERNAL', 'LOOSE_INTERNAL', 'GET_PERMISSION', 'LOOSE_PERMISSION', name='pollvariant'), nullable=False))
        batch_op.add_column(sa.Column('user_id', sa.Integer(), nullable=False))
        batch_op.create_foreign_key('fk_polls_user_id_users_id', 'users', ['user_id'], ['id'])


def downgrade():
    with op.batch_alter_table("polls") as batch_op:
        batch_op.drop_constraint('fk_polls_user_id_users_id', type_='foreignkey')
        batch_op.drop_column('user_id')
        batch_op.drop_column('variant')

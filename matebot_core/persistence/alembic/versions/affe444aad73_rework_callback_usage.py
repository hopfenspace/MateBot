"""rework callback usage

Revision ID: affe444aad73
Revises: 807733b6fb80
Create Date: 2022-05-06 16:19:54.003056

"""
from alembic import op
import sqlalchemy as sa


revision = 'affe444aad73'
down_revision = '807733b6fb80'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("callbacks") as batch_op:
        batch_op.add_column(sa.Column('url', sa.String(length=255), nullable=False))
        batch_op.add_column(sa.Column('shared_secret', sa.String(length=2047), nullable=True))
        batch_op.drop_column('password')
        batch_op.drop_column('username')
        batch_op.drop_column('base')


def downgrade():
    with op.batch_alter_table("callbacks") as batch_op:
        batch_op.add_column(sa.Column('base', sa.VARCHAR(length=255), nullable=False))
        batch_op.add_column(sa.Column('username', sa.VARCHAR(length=255), nullable=True))
        batch_op.add_column(sa.Column('password', sa.VARCHAR(length=255), nullable=True))
        batch_op.drop_column('shared_secret')
        batch_op.drop_column('url')

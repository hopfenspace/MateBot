"""switch from password & salt to argon2-hashed password

Revision ID: 1ae7ae3dfe83
Revises: bc119713b2ff
Create Date: 2022-12-23 22:09:51.099599

"""
from alembic import op
import sqlalchemy as sa


revision = '1ae7ae3dfe83'
down_revision = 'bc119713b2ff'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("applications") as batch_op:
        batch_op.drop_column('salt')
        batch_op.drop_column('password')
        batch_op.add_column(sa.Column('hashed_password', sa.VARCHAR(length=255), nullable=False))


def downgrade():
    with op.batch_alter_table("applications") as batch_op:
        batch_op.drop_column('hashed_password')
        batch_op.add_column(sa.Column('password', sa.VARCHAR(length=255), nullable=False))
        batch_op.add_column(sa.Column('salt', sa.VARCHAR(length=255), nullable=False))

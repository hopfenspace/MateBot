"""initial setup

Revision ID: 807733b6fb80
Revises:
Create Date: 2022-03-01 04:13:49.107043

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '807733b6fb80'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.create_table('applications',
                    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
                    sa.Column('name', sa.String(length=255), nullable=False),
                    sa.Column('password', sa.String(length=255), nullable=False),
                    sa.Column('salt', sa.String(length=255), nullable=False),
                    sa.Column('created', sa.DateTime(), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=True),
                    sa.PrimaryKeyConstraint('id'),
                    sa.UniqueConstraint('id'),
                    sa.UniqueConstraint('name')
                    )
    op.create_table('ballots',
                    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
                    sa.Column('modified', sa.DateTime(), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
                    sa.PrimaryKeyConstraint('id'),
                    sa.UniqueConstraint('id')
                    )
    op.create_table('multi_transactions',
                    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
                    sa.Column('base_amount', sa.Integer(), nullable=False),
                    sa.Column('registered', sa.DateTime(), server_default=sa.text('(CURRENT_TIMESTAMP)'),
                              nullable=False),
                    sa.PrimaryKeyConstraint('id'),
                    sa.UniqueConstraint('id')
                    )
    op.create_table('users',
                    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
                    sa.Column('name', sa.String(length=255), nullable=True),
                    sa.Column('balance', sa.Integer(), nullable=False),
                    sa.Column('permission', sa.Boolean(), nullable=False),
                    sa.Column('active', sa.Boolean(), nullable=False),
                    sa.Column('special', sa.Boolean(), nullable=True),
                    sa.Column('external', sa.Boolean(), nullable=False),
                    sa.Column('voucher_id', sa.Integer(), nullable=True),
                    sa.Column('created', sa.DateTime(), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=True),
                    sa.Column('modified', sa.DateTime(), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=True),
                    sa.CheckConstraint('special != false'),
                    sa.ForeignKeyConstraint(['voucher_id'], ['users.id'], ),
                    sa.PrimaryKeyConstraint('id'),
                    sa.UniqueConstraint('id'),
                    sa.UniqueConstraint('special')
                    )
    op.create_table('aliases',
                    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
                    sa.Column('user_id', sa.Integer(), nullable=False),
                    sa.Column('application_id', sa.Integer(), nullable=False),
                    sa.Column('username', sa.String(length=255), nullable=False),
                    sa.Column('confirmed', sa.Boolean(), nullable=False),
                    sa.ForeignKeyConstraint(['application_id'], ['applications.id'], ondelete='CASCADE'),
                    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
                    sa.PrimaryKeyConstraint('id'),
                    sa.UniqueConstraint('application_id', 'username', name='single_username_per_app'),
                    sa.UniqueConstraint('id')
                    )
    op.create_table('callbacks',
                    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
                    sa.Column('base', sa.String(length=255), nullable=False),
                    sa.Column('application_id', sa.Integer(), nullable=True),
                    sa.Column('username', sa.String(length=255), nullable=True),
                    sa.Column('password', sa.String(length=255), nullable=True),
                    sa.ForeignKeyConstraint(['application_id'], ['applications.id'], ondelete='CASCADE'),
                    sa.PrimaryKeyConstraint('id'),
                    sa.UniqueConstraint('application_id'),
                    sa.UniqueConstraint('id')
                    )
    op.create_table('communisms',
                    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
                    sa.Column('active', sa.Boolean(), nullable=False),
                    sa.Column('amount', sa.Integer(), nullable=False),
                    sa.Column('description', sa.String(length=255), nullable=False),
                    sa.Column('created', sa.DateTime(), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
                    sa.Column('modified', sa.DateTime(), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
                    sa.Column('creator_id', sa.Integer(), nullable=False),
                    sa.Column('multi_transaction_id', sa.Integer(), nullable=True),
                    sa.CheckConstraint('amount >= 1'),
                    sa.ForeignKeyConstraint(['creator_id'], ['users.id'], ),
                    sa.ForeignKeyConstraint(['multi_transaction_id'], ['multi_transactions.id'], ),
                    sa.PrimaryKeyConstraint('id'),
                    sa.UniqueConstraint('id')
                    )
    op.create_table('polls',
                    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
                    sa.Column('active', sa.Boolean(), nullable=False),
                    sa.Column('accepted', sa.Boolean(), nullable=True),
                    sa.Column('creator_id', sa.Integer(), nullable=False),
                    sa.Column('ballot_id', sa.Integer(), nullable=False),
                    sa.Column('created', sa.DateTime(), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
                    sa.Column('modified', sa.DateTime(), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
                    sa.ForeignKeyConstraint(['ballot_id'], ['ballots.id'], ),
                    sa.ForeignKeyConstraint(['creator_id'], ['users.id'], ),
                    sa.PrimaryKeyConstraint('id'),
                    sa.UniqueConstraint('id')
                    )
    op.create_table('transactions',
                    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
                    sa.Column('sender_id', sa.Integer(), nullable=False),
                    sa.Column('receiver_id', sa.Integer(), nullable=False),
                    sa.Column('amount', sa.Integer(), nullable=False),
                    sa.Column('reason', sa.String(length=255), nullable=True),
                    sa.Column('timestamp', sa.DateTime(), server_default=sa.text('(CURRENT_TIMESTAMP)'),
                              nullable=False),
                    sa.Column('multi_transaction_id', sa.Integer(), nullable=True),
                    sa.CheckConstraint('amount > 0'),
                    sa.CheckConstraint('sender_id != receiver_id'),
                    sa.ForeignKeyConstraint(['multi_transaction_id'], ['multi_transactions.id'], ),
                    sa.ForeignKeyConstraint(['receiver_id'], ['users.id'], ),
                    sa.ForeignKeyConstraint(['sender_id'], ['users.id'], ),
                    sa.PrimaryKeyConstraint('id'),
                    sa.UniqueConstraint('id')
                    )
    op.create_table('votes',
                    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
                    sa.Column('vote', sa.Boolean(), nullable=False),
                    sa.Column('ballot_id', sa.Integer(), nullable=False),
                    sa.Column('user_id', sa.Integer(), nullable=False),
                    sa.Column('modified', sa.DateTime(), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
                    sa.ForeignKeyConstraint(['ballot_id'], ['ballots.id'], ondelete='CASCADE'),
                    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
                    sa.PrimaryKeyConstraint('id'),
                    sa.UniqueConstraint('id'),
                    sa.UniqueConstraint('user_id', 'ballot_id', name='single_vote_per_user')
                    )
    op.create_table('communisms_users',
                    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
                    sa.Column('communism_id', sa.Integer(), nullable=False),
                    sa.Column('user_id', sa.Integer(), nullable=False),
                    sa.Column('quantity', sa.Integer(), nullable=False),
                    sa.ForeignKeyConstraint(['communism_id'], ['communisms.id'], ondelete='CASCADE'),
                    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
                    sa.PrimaryKeyConstraint('id'),
                    sa.UniqueConstraint('id')
                    )
    op.create_table('refunds',
                    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
                    sa.Column('amount', sa.Integer(), nullable=False),
                    sa.Column('description', sa.String(length=255), nullable=False),
                    sa.Column('active', sa.Boolean(), nullable=False),
                    sa.Column('created', sa.DateTime(), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
                    sa.Column('modified', sa.DateTime(), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
                    sa.Column('creator_id', sa.Integer(), nullable=False),
                    sa.Column('ballot_id', sa.Integer(), nullable=False),
                    sa.Column('transaction_id', sa.Integer(), nullable=True),
                    sa.CheckConstraint('amount > 0'),
                    sa.ForeignKeyConstraint(['ballot_id'], ['ballots.id'], ),
                    sa.ForeignKeyConstraint(['creator_id'], ['users.id'], ),
                    sa.ForeignKeyConstraint(['transaction_id'], ['transactions.id'], ),
                    sa.PrimaryKeyConstraint('id'),
                    sa.UniqueConstraint('id')
                    )


def downgrade():
    op.drop_table('refunds')
    op.drop_table('communisms_users')
    op.drop_table('votes')
    op.drop_table('transactions')
    op.drop_table('polls')
    op.drop_table('communisms')
    op.drop_table('callbacks')
    op.drop_table('aliases')
    op.drop_table('users')
    op.drop_table('multi_transactions')
    op.drop_table('ballots')
    op.drop_table('applications')

"""auth and rbac schema

Revision ID: 10a3e3b0da62
Revises: 7d364c4b6967
Create Date: 2026-09-05 00:35:08.100127

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '10a3e3b0da62'
down_revision: Union[str, None] = '7d364c4b6967'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table('auth_sessions',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.Column('token_hash', sa.String(length=128), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.Column('expires_at', sa.DateTime(), nullable=False),
    sa.Column('revoked_at', sa.DateTime(), nullable=True),
    sa.Column('user_agent', sa.String(length=400), nullable=True),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('token_hash')
    )
    op.create_table('password_reset_tokens',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.Column('token_hash', sa.String(length=128), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.Column('expires_at', sa.DateTime(), nullable=False),
    sa.Column('used_at', sa.DateTime(), nullable=True),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('token_hash')
    )
    op.create_table('invitations',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('email', sa.String(length=320), nullable=False),
    sa.Column('name', sa.String(length=200), nullable=False),
    sa.Column('team_id', sa.Integer(), nullable=True),
    sa.Column('target_global_role', sa.Enum('USER', 'ADMIN', name='globalrole'), nullable=False),
    sa.Column('target_team_role', sa.Enum('MEMBER', 'LEAD', name='teamrole'), nullable=True),
    sa.Column('invited_by_user_id', sa.Integer(), nullable=False),
    sa.Column('token_hash', sa.String(length=128), nullable=False),
    sa.Column('status', sa.Enum('PENDING', 'ACCEPTED', 'REVOKED', 'EXPIRED', name='invitationstatus'), nullable=False),
    sa.Column('expires_at', sa.DateTime(), nullable=False),
    sa.Column('accepted_at', sa.DateTime(), nullable=True),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.Column('updated_at', sa.DateTime(), nullable=False),
    sa.ForeignKeyConstraint(['invited_by_user_id'], ['users.id'], ),
    sa.ForeignKeyConstraint(['team_id'], ['teams.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('token_hash')
    )
    with op.batch_alter_table('team_memberships', schema=None) as batch_op:
        batch_op.add_column(sa.Column('team_role', sa.Enum('MEMBER', 'LEAD', name='teamrole'), nullable=False, server_default='MEMBER'))
        batch_op.create_unique_constraint('uq_team_membership', ['team_id', 'user_id'])

    # users: add the new columns nullable first, backfill from the old
    # role/active columns with a plain UPDATE, THEN tighten to NOT NULL
    # and drop the old columns — SQLite (via batch mode) recreates the
    # table on each ALTER, so the old and new columns must briefly
    # coexist for the backfill to have anything to read.
    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.add_column(sa.Column('password_hash', sa.String(length=300), nullable=True))
        batch_op.add_column(sa.Column('global_role', sa.Enum('USER', 'ADMIN', name='globalrole'), nullable=True))
        batch_op.add_column(sa.Column('status', sa.Enum('PENDING', 'ACTIVE', 'INACTIVE', 'ARCHIVED', name='userstatus'), nullable=True))
        batch_op.add_column(sa.Column('last_login_at', sa.DateTime(), nullable=True))

    op.execute("UPDATE users SET global_role = CASE WHEN role = 'ADMIN' THEN 'ADMIN' ELSE 'USER' END")
    op.execute("UPDATE users SET status = CASE WHEN active = 1 THEN 'ACTIVE' ELSE 'INACTIVE' END")

    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.alter_column('global_role', nullable=False)
        batch_op.alter_column('status', nullable=False)
        batch_op.drop_column('active')
        batch_op.drop_column('role')


def downgrade() -> None:
    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.add_column(sa.Column('role', sa.VARCHAR(length=6), nullable=False, server_default='viewer'))
        batch_op.add_column(sa.Column('active', sa.BOOLEAN(), nullable=False, server_default='1'))
        batch_op.drop_column('last_login_at')
        batch_op.drop_column('status')
        batch_op.drop_column('global_role')
        batch_op.drop_column('password_hash')

    with op.batch_alter_table('team_memberships', schema=None) as batch_op:
        batch_op.drop_constraint('uq_team_membership', type_='unique')
        batch_op.drop_column('team_role')

    op.drop_table('invitations')
    op.drop_table('password_reset_tokens')
    op.drop_table('auth_sessions')

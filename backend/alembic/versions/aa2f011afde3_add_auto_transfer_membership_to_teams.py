"""add auto_transfer_membership to teams

Revision ID: aa2f011afde3
Revises: eb312d0c1162
Create Date: 2026-09-10 09:09:17.968662

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'aa2f011afde3'
down_revision: Union[str, None] = 'eb312d0c1162'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table('teams', schema=None) as batch_op:
        batch_op.add_column(
            sa.Column(
                'auto_transfer_membership',
                sa.Boolean(),
                nullable=False,
                server_default=sa.false(),
            )
        )

    # One-time backfill: every deployment's existing "Board"/"Admin" teams
    # hold shared, role-based accounts today, so flag them as such rather
    # than starting everyone from an all-False slate an Admin has to
    # rediscover by hand. New teams default to False either way.
    bind = op.get_bind()
    bind.execute(
        sa.text(
            "UPDATE teams SET auto_transfer_membership = 1 "
            "WHERE lower(name) IN ('board', 'admin')"
        )
    )


def downgrade() -> None:
    with op.batch_alter_table('teams', schema=None) as batch_op:
        batch_op.drop_column('auto_transfer_membership')

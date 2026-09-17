"""add default view settings to projects

Revision ID: 2f737ea67a07
Revises: aa2f011afde3
Create Date: 2026-09-17 08:51:17.522896

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '2f737ea67a07'
down_revision: Union[str, None] = 'aa2f011afde3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table('projects', schema=None) as batch_op:
        batch_op.add_column(sa.Column('default_gantt_team_id', sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column('default_gantt_tag_id', sa.Integer(), nullable=True))
        batch_op.add_column(
            sa.Column(
                'default_calendar_all_teams',
                sa.Boolean(),
                nullable=False,
                server_default=sa.true(),
            )
        )
        batch_op.add_column(sa.Column('default_calendar_team_id', sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column('default_calendar_tag_id', sa.Integer(), nullable=True))
        batch_op.create_foreign_key(
            'fk_projects_default_gantt_team_id_teams', 'teams', ['default_gantt_team_id'], ['id']
        )
        batch_op.create_foreign_key(
            'fk_projects_default_gantt_tag_id_tags', 'tags', ['default_gantt_tag_id'], ['id']
        )
        batch_op.create_foreign_key(
            'fk_projects_default_calendar_team_id_teams',
            'teams',
            ['default_calendar_team_id'],
            ['id'],
        )
        batch_op.create_foreign_key(
            'fk_projects_default_calendar_tag_id_tags', 'tags', ['default_calendar_tag_id'], ['id']
        )


def downgrade() -> None:
    with op.batch_alter_table('projects', schema=None) as batch_op:
        batch_op.drop_column('default_calendar_tag_id')
        batch_op.drop_column('default_calendar_team_id')
        batch_op.drop_column('default_calendar_all_teams')
        batch_op.drop_column('default_gantt_tag_id')
        batch_op.drop_column('default_gantt_team_id')

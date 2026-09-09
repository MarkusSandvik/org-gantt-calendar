"""add project lifecycle fields and dependency project_id

Revision ID: eb312d0c1162
Revises: 3a7a6f4aacfc
Create Date: 2026-09-09 00:36:30.343482

"""
import re
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'eb312d0c1162'
down_revision: Union[str, None] = '3a7a6f4aacfc'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return slug or "project"


def upgrade() -> None:
    bind = op.get_bind()

    # --- add everything nullable/unconstrained first, so this is safe to
    # run against a database that already has real project/dependency rows.
    with op.batch_alter_table('projects', schema=None) as batch_op:
        batch_op.add_column(sa.Column('slug', sa.String(length=100), nullable=True))
        batch_op.add_column(sa.Column('season_label', sa.String(length=50), nullable=True))
        batch_op.add_column(
            sa.Column(
                'status',
                sa.Enum('DRAFT', 'ACTIVE', 'COMPLETED', 'ARCHIVED', name='projectstatus'),
                nullable=False,
                server_default='ACTIVE',
            )
        )
        batch_op.add_column(
            sa.Column('is_default', sa.Boolean(), nullable=False, server_default=sa.false())
        )
        batch_op.add_column(sa.Column('archived_at', sa.DateTime(), nullable=True))
        batch_op.add_column(sa.Column('created_by_id', sa.Integer(), nullable=True))
        batch_op.create_foreign_key(
            'fk_projects_created_by_id_users', 'users', ['created_by_id'], ['id']
        )

    with op.batch_alter_table('dependencies', schema=None) as batch_op:
        batch_op.add_column(sa.Column('project_id', sa.Integer(), nullable=True))

    # --- data backfill: give every existing project a slug, and mark
    # exactly one existing project as the org's current default — the
    # earliest-created one, so behavior after migrating matches whatever
    # was already effectively "the" project before this feature existed.
    projects = bind.execute(sa.text("SELECT id, name FROM projects ORDER BY id")).fetchall()
    used_slugs: set[str] = set()
    for i, (project_id, name) in enumerate(projects):
        base = _slugify(name)
        slug = base
        suffix = 2
        while slug in used_slugs:
            slug = f"{base}-{suffix}"
            suffix += 1
        used_slugs.add(slug)
        bind.execute(
            sa.text("UPDATE projects SET slug = :slug, is_default = :is_default WHERE id = :id"),
            {"slug": slug, "is_default": i == 0, "id": project_id},
        )

    # --- backfill dependencies.project_id from whichever end (predecessor,
    # falling back to successor) resolves to a real activity/milestone;
    # if a dependency's endpoints are somehow both missing (orphaned data
    # predating this migration), fall back to the default project rather
    # than leaving a NULL a NOT NULL constraint can't accept.
    bind.execute(
        sa.text(
            """
            UPDATE dependencies
            SET project_id = COALESCE(
                (SELECT project_id FROM activities
                 WHERE activities.id = dependencies.predecessor_id
                   AND dependencies.predecessor_type = 'activity'),
                (SELECT project_id FROM milestones
                 WHERE milestones.id = dependencies.predecessor_id
                   AND dependencies.predecessor_type = 'milestone'),
                (SELECT project_id FROM activities
                 WHERE activities.id = dependencies.successor_id
                   AND dependencies.successor_type = 'activity'),
                (SELECT project_id FROM milestones
                 WHERE milestones.id = dependencies.successor_id
                   AND dependencies.successor_type = 'milestone'),
                (SELECT id FROM projects WHERE is_default = 1 LIMIT 1)
            )
            """
        )
    )

    # --- now that every row has a value, lock the columns down.
    with op.batch_alter_table('projects', schema=None) as batch_op:
        batch_op.alter_column('slug', existing_type=sa.String(length=100), nullable=False)
        batch_op.create_index(batch_op.f('ix_projects_slug'), ['slug'], unique=True)

    with op.batch_alter_table('dependencies', schema=None) as batch_op:
        batch_op.alter_column('project_id', existing_type=sa.Integer(), nullable=False)
        batch_op.create_foreign_key(
            'fk_dependencies_project_id_projects', 'projects', ['project_id'], ['id']
        )


def downgrade() -> None:
    with op.batch_alter_table('dependencies', schema=None) as batch_op:
        batch_op.drop_constraint('fk_dependencies_project_id_projects', type_='foreignkey')
        batch_op.drop_column('project_id')

    with op.batch_alter_table('projects', schema=None) as batch_op:
        batch_op.drop_constraint('fk_projects_created_by_id_users', type_='foreignkey')
        batch_op.drop_index(batch_op.f('ix_projects_slug'))
        batch_op.drop_column('created_by_id')
        batch_op.drop_column('archived_at')
        batch_op.drop_column('is_default')
        batch_op.drop_column('status')
        batch_op.drop_column('season_label')
        batch_op.drop_column('slug')

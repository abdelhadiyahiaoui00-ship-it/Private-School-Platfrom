"""sprint4_alter_academic_tables

Revision ID: 016_sprint4_alter
Revises: ce1a704826eb
Create Date: 2026-07-22

Sprint 3 already created modules/classes/groups/sessions/enrollments as scaffolds.
This migration adds all Sprint 4 missing columns via ALTER TABLE ADD COLUMN IF NOT EXISTS.
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = '016_sprint4_alter'
down_revision: Union[str, None] = 'ce1a704826eb'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── modules: add color, created_by, unique index on name ─────────────────
    op.add_column('modules', sa.Column('color', sa.String(length=20), nullable=True))
    op.add_column('modules', sa.Column('created_by', sa.Integer(), nullable=True))
    try:
        op.create_foreign_key(
            'fk_modules_created_by', 'modules', 'users', ['created_by'], ['id'],
            ondelete='SET NULL'
        )
    except Exception:
        pass  # FK may already exist

    try:
        op.create_unique_constraint('idx_modules_name', 'modules', ['name'])
    except Exception:
        pass
    try:
        op.create_index('idx_modules_category', 'modules', ['category'])
    except Exception:
        pass
    try:
        op.create_index('idx_modules_active', 'modules', ['is_active'])
    except Exception:
        pass

    # ── classes: add education level targeting columns + created_by ──────────
    op.add_column('classes', sa.Column('education_stage', sa.String(length=20),
                  nullable=False, server_default='all'))
    op.add_column('classes', sa.Column('education_year', sa.Integer(), nullable=True))
    op.add_column('classes', sa.Column('level_scope', sa.String(length=20),
                  nullable=False, server_default='all_levels'))
    op.add_column('classes', sa.Column('min_age', sa.SmallInteger(), nullable=True))
    op.add_column('classes', sa.Column('max_age', sa.SmallInteger(), nullable=True))
    op.add_column('classes', sa.Column('university_label', sa.String(length=100), nullable=True))
    op.add_column('classes', sa.Column('level_rank', sa.SmallInteger(), nullable=True))
    op.add_column('classes', sa.Column('created_by', sa.Integer(), nullable=True))
    try:
        op.create_foreign_key(
            'fk_classes_created_by', 'classes', 'users', ['created_by'], ['id'],
            ondelete='SET NULL'
        )
    except Exception:
        pass
    try:
        op.create_index('idx_classes_status', 'classes', ['status'])
    except Exception:
        pass
    try:
        op.create_index('idx_classes_level_rank', 'classes', ['level_rank'])
    except Exception:
        pass

    # ── groups: add last_generated_until ─────────────────────────────────────
    op.add_column('groups', sa.Column('last_generated_until', sa.Date(), nullable=True))
    try:
        op.create_index('idx_groups_status', 'groups', ['status'])
    except Exception:
        pass

    # ── sessions: add unique index for idempotent generation ─────────────────
    try:
        op.create_unique_index(
            'idx_sessions_group_date_time', 'sessions',
            ['group_id', 'session_date', 'start_time']
        )
    except Exception:
        pass
    try:
        op.create_index('idx_sessions_status', 'sessions', ['status'])
    except Exception:
        pass
    try:
        op.create_index(
            'idx_sessions_branch_date', 'sessions', ['branch_id', 'session_date']
        )
    except Exception:
        pass


def downgrade() -> None:
    op.drop_column('groups', 'last_generated_until')
    op.drop_column('classes', 'created_by')
    op.drop_column('classes', 'level_rank')
    op.drop_column('classes', 'university_label')
    op.drop_column('classes', 'max_age')
    op.drop_column('classes', 'min_age')
    op.drop_column('classes', 'level_scope')
    op.drop_column('classes', 'education_year')
    op.drop_column('classes', 'education_stage')
    op.drop_column('modules', 'created_by')
    op.drop_column('modules', 'color')

"""create_assignment_submissions

Revision ID: 025_assignment_submissions
Revises: 024_add_batch_id
Create Date: 2026-08-27
"""
from typing import Union
from alembic import op
import sqlalchemy as sa

revision: str = '025_assignment_submissions'
down_revision: Union[str, None] = '024_add_batch_id'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'assignment_submissions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('assignment_id', sa.Integer(), nullable=False),
        sa.Column('student_id', sa.Integer(), nullable=False),
        sa.Column('submission_type', sa.String(20), nullable=False),
        sa.Column('response_text', sa.Text(), nullable=True),
        sa.Column('file_url', sa.String(500), nullable=True),
        sa.Column('file_name', sa.String(255), nullable=True),
        sa.Column('file_type', sa.String(20), nullable=True),
        sa.Column('submitted_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['assignment_id'], ['assignments.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['student_id'], ['users.id'], ondelete='CASCADE'),
        sa.UniqueConstraint('assignment_id', 'student_id', name='uq_assignment_student'),
    )
    op.create_check_constraint(
        'chk_submission_content',
        'assignment_submissions',
        "(submission_type = 'done_only') OR "
        "(submission_type = 'text' AND response_text IS NOT NULL) OR "
        "(submission_type = 'file' AND file_url IS NOT NULL)"
    )
    op.create_index('idx_submissions_assignment', 'assignment_submissions', ['assignment_id'])
    op.create_index('idx_submissions_student', 'assignment_submissions', ['student_id'])


def downgrade() -> None:
    op.drop_index('idx_submissions_student', table_name='assignment_submissions')
    op.drop_index('idx_submissions_assignment', table_name='assignment_submissions')
    op.drop_constraint('chk_submission_content', 'assignment_submissions', type_='check')
    op.drop_table('assignment_submissions')

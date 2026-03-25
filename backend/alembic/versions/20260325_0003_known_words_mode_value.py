"""add known words mode and value

Revision ID: 20260325_0003
Revises: 20260321_0002
Create Date: 2026-03-25 18:00:00.000000
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "20260325_0003"
down_revision = "20260321_0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("analysis_jobs") as batch_op:
        batch_op.add_column(sa.Column("known_words_mode", sa.String(length=20), nullable=True))
        batch_op.add_column(sa.Column("known_words_value", sa.String(length=20), nullable=True))

    op.execute(
        """
        UPDATE analysis_jobs
        SET known_words_mode = 'coca_rank',
            known_words_value = CAST(known_words_level AS VARCHAR)
        WHERE known_words_level IS NOT NULL
        """
    )
    op.execute(
        """
        UPDATE analysis_jobs
        SET known_words_mode = COALESCE(known_words_mode, 'coca_rank'),
            known_words_value = COALESCE(known_words_value, '3000')
        """
    )

    with op.batch_alter_table("analysis_jobs") as batch_op:
        batch_op.alter_column("known_words_mode", nullable=False)
        batch_op.alter_column("known_words_value", nullable=False)
        batch_op.alter_column("known_words_level", nullable=True)
        batch_op.create_index(batch_op.f("ix_analysis_jobs_known_words_mode"), ["known_words_mode"], unique=False)


def downgrade() -> None:
    raise NotImplementedError("Downgrade is not supported for known_words_mode/known_words_value migration.")

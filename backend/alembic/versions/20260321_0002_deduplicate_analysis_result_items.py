"""deduplicate analysis result items

Revision ID: 20260321_0002
Revises: 149ef2fe4559
Create Date: 2026-03-21 10:30:00.000000
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "20260321_0002"
down_revision = "149ef2fe4559"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("analysis_result_items") as batch_op:
        batch_op.add_column(sa.Column("is_to_memorize", sa.Boolean(), nullable=False, server_default=sa.false()))
        batch_op.add_column(sa.Column("is_coverage_95", sa.Boolean(), nullable=False, server_default=sa.false()))

    op.execute(
        """
        UPDATE analysis_result_items AS base
        SET is_to_memorize = EXISTS (
            SELECT 1
            FROM analysis_result_items AS derived
            WHERE derived.result_id = base.result_id
              AND derived.word = base.word
              AND derived.list_type = 'to_memorize'
        )
        WHERE base.list_type = 'all_words'
        """
    )
    op.execute(
        """
        UPDATE analysis_result_items AS base
        SET is_coverage_95 = EXISTS (
            SELECT 1
            FROM analysis_result_items AS derived
            WHERE derived.result_id = base.result_id
              AND derived.word = base.word
              AND derived.list_type = 'coverage_95'
        )
        WHERE base.list_type = 'all_words'
        """
    )
    op.execute("DELETE FROM analysis_result_items WHERE list_type != 'all_words'")

    with op.batch_alter_table("analysis_result_items") as batch_op:
        batch_op.alter_column("is_to_memorize", server_default=None)
        batch_op.alter_column("is_coverage_95", server_default=None)


def downgrade() -> None:
    raise NotImplementedError("Downgrade is not supported because duplicate derived rows were removed.")

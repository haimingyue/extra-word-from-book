"""add analysis result chapters

Revision ID: 20260422_0005
Revises: 20260421_0004
Create Date: 2026-04-22 10:00:00
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260422_0005"
down_revision = "20260421_0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "analysis_result_chapters",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("result_id", sa.Integer(), nullable=False),
        sa.Column("chapter_index", sa.Integer(), nullable=False),
        sa.Column("chapter_title", sa.String(length=255), nullable=False),
        sa.Column("total_word_count", sa.Integer(), nullable=False),
        sa.Column("unique_word_count", sa.Integer(), nullable=False),
        sa.Column("to_memorize_word_count", sa.Integer(), nullable=False),
        sa.Column("coverage_95_word_count", sa.Integer(), nullable=False),
        sa.Column("reading_level", sa.String(length=20), nullable=False),
        sa.Column("reading_message", sa.String(length=255), nullable=False),
        sa.Column("all_words_file_key", sa.String(length=500), nullable=True),
        sa.Column("to_memorize_file_key", sa.String(length=500), nullable=True),
        sa.Column("coverage_95_file_key", sa.String(length=500), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=False),
        sa.ForeignKeyConstraint(["result_id"], ["analysis_results.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("result_id", "chapter_index", name="uq_result_chapter_index"),
    )
    op.create_index(
        op.f("ix_analysis_result_chapters_result_id"),
        "analysis_result_chapters",
        ["result_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_analysis_result_chapters_result_id"), table_name="analysis_result_chapters")
    op.drop_table("analysis_result_chapters")

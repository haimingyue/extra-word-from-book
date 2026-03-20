"""initial schema

Revision ID: 20260320_0001
Revises: None
Create Date: 2026-03-20 12:00:00
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260320_0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("display_name", sa.String(length=100), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=False),
        sa.Column("last_login_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_users_email"), "users", ["email"], unique=True)

    op.create_table(
        "books",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("file_hash", sa.String(length=128), nullable=False),
        sa.Column("original_filename", sa.String(length=255), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=True),
        sa.Column("language", sa.String(length=20), nullable=True),
        sa.Column("file_size_bytes", sa.Integer(), nullable=True),
        sa.Column("storage_key", sa.String(length=500), nullable=False),
        sa.Column("text_extract_status", sa.String(length=20), nullable=False),
        sa.Column("created_by_user_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=False),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_books_file_hash"), "books", ["file_hash"], unique=True)

    op.create_table(
        "user_vocabularies",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=True),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("is_primary", sa.Boolean(), nullable=False),
        sa.Column("source_type", sa.String(length=20), nullable=False),
        sa.Column("source_file_key", sa.String(length=500), nullable=True),
        sa.Column("item_count", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_user_vocabularies_user_id"), "user_vocabularies", ["user_id"], unique=False)

    op.create_table(
        "analysis_jobs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=True),
        sa.Column("book_id", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("known_words_level", sa.Integer(), nullable=False),
        sa.Column("vocabulary_snapshot_count", sa.Integer(), nullable=False),
        sa.Column("error_code", sa.String(length=50), nullable=True),
        sa.Column("error_message", sa.String(length=500), nullable=True),
        sa.Column("queued_at", sa.DateTime(timezone=True), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=False),
        sa.ForeignKeyConstraint(["book_id"], ["books.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_analysis_jobs_book_id"), "analysis_jobs", ["book_id"], unique=False)
    op.create_index(op.f("ix_analysis_jobs_known_words_level"), "analysis_jobs", ["known_words_level"], unique=False)
    op.create_index(op.f("ix_analysis_jobs_status"), "analysis_jobs", ["status"], unique=False)
    op.create_index(op.f("ix_analysis_jobs_user_id"), "analysis_jobs", ["user_id"], unique=False)

    op.create_table(
        "analysis_job_vocabulary_snapshots",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("job_id", sa.Integer(), nullable=False),
        sa.Column("word", sa.String(length=100), nullable=False),
        sa.Column("normalized_word", sa.String(length=100), nullable=False),
        sa.Column("source_type", sa.String(length=20), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=False),
        sa.ForeignKeyConstraint(["job_id"], ["analysis_jobs.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("job_id", "normalized_word", "source_type", name="uq_job_snapshot_word_source"),
    )
    op.create_index(
        op.f("ix_analysis_job_vocabulary_snapshots_job_id"),
        "analysis_job_vocabulary_snapshots",
        ["job_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_analysis_job_vocabulary_snapshots_normalized_word"),
        "analysis_job_vocabulary_snapshots",
        ["normalized_word"],
        unique=False,
    )

    op.create_table(
        "analysis_results",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("job_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=True),
        sa.Column("book_id", sa.Integer(), nullable=False),
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
        sa.ForeignKeyConstraint(["book_id"], ["books.id"]),
        sa.ForeignKeyConstraint(["job_id"], ["analysis_jobs.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_analysis_results_book_id"), "analysis_results", ["book_id"], unique=False)
    op.create_index(op.f("ix_analysis_results_job_id"), "analysis_results", ["job_id"], unique=True)
    op.create_index(op.f("ix_analysis_results_user_id"), "analysis_results", ["user_id"], unique=False)

    op.create_table(
        "analysis_result_items",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("result_id", sa.Integer(), nullable=False),
        sa.Column("sequence_no", sa.Integer(), nullable=False),
        sa.Column("word", sa.String(length=100), nullable=False),
        sa.Column("lemma", sa.String(length=100), nullable=True),
        sa.Column("book_frequency", sa.Integer(), nullable=False),
        sa.Column("coca_rank", sa.Integer(), nullable=True),
        sa.Column("is_known", sa.Boolean(), nullable=False),
        sa.Column("list_type", sa.String(length=30), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=False),
        sa.ForeignKeyConstraint(["result_id"], ["analysis_results.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("result_id", "list_type", "sequence_no", name="uq_result_list_sequence"),
    )
    op.create_index(op.f("ix_analysis_result_items_list_type"), "analysis_result_items", ["list_type"], unique=False)
    op.create_index(op.f("ix_analysis_result_items_result_id"), "analysis_result_items", ["result_id"], unique=False)
    op.create_index(op.f("ix_analysis_result_items_word"), "analysis_result_items", ["word"], unique=False)

    op.create_table(
        "user_vocabulary_items",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("vocabulary_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=True),
        sa.Column("word", sa.String(length=100), nullable=False),
        sa.Column("lemma", sa.String(length=100), nullable=True),
        sa.Column("normalized_word", sa.String(length=100), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["vocabulary_id"], ["user_vocabularies.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("vocabulary_id", "normalized_word", name="uq_vocabulary_word"),
    )
    op.create_index(op.f("ix_user_vocabulary_items_normalized_word"), "user_vocabulary_items", ["normalized_word"], unique=False)
    op.create_index(op.f("ix_user_vocabulary_items_user_id"), "user_vocabulary_items", ["user_id"], unique=False)
    op.create_index(op.f("ix_user_vocabulary_items_vocabulary_id"), "user_vocabulary_items", ["vocabulary_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_user_vocabulary_items_vocabulary_id"), table_name="user_vocabulary_items")
    op.drop_index(op.f("ix_user_vocabulary_items_user_id"), table_name="user_vocabulary_items")
    op.drop_index(op.f("ix_user_vocabulary_items_normalized_word"), table_name="user_vocabulary_items")
    op.drop_table("user_vocabulary_items")

    op.drop_index(op.f("ix_analysis_result_items_word"), table_name="analysis_result_items")
    op.drop_index(op.f("ix_analysis_result_items_result_id"), table_name="analysis_result_items")
    op.drop_index(op.f("ix_analysis_result_items_list_type"), table_name="analysis_result_items")
    op.drop_table("analysis_result_items")

    op.drop_index(op.f("ix_analysis_results_user_id"), table_name="analysis_results")
    op.drop_index(op.f("ix_analysis_results_job_id"), table_name="analysis_results")
    op.drop_index(op.f("ix_analysis_results_book_id"), table_name="analysis_results")
    op.drop_table("analysis_results")

    op.drop_index(
        op.f("ix_analysis_job_vocabulary_snapshots_normalized_word"),
        table_name="analysis_job_vocabulary_snapshots",
    )
    op.drop_index(
        op.f("ix_analysis_job_vocabulary_snapshots_job_id"),
        table_name="analysis_job_vocabulary_snapshots",
    )
    op.drop_table("analysis_job_vocabulary_snapshots")

    op.drop_index(op.f("ix_analysis_jobs_user_id"), table_name="analysis_jobs")
    op.drop_index(op.f("ix_analysis_jobs_status"), table_name="analysis_jobs")
    op.drop_index(op.f("ix_analysis_jobs_known_words_level"), table_name="analysis_jobs")
    op.drop_index(op.f("ix_analysis_jobs_book_id"), table_name="analysis_jobs")
    op.drop_table("analysis_jobs")

    op.drop_index(op.f("ix_user_vocabularies_user_id"), table_name="user_vocabularies")
    op.drop_table("user_vocabularies")

    op.drop_index(op.f("ix_books_file_hash"), table_name="books")
    op.drop_table("books")

    op.drop_index(op.f("ix_users_email"), table_name="users")
    op.drop_table("users")

from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class AnalysisJob(Base):
    __tablename__ = "analysis_jobs"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), index=True, nullable=True)
    book_id: Mapped[int] = mapped_column(ForeignKey("books.id"), index=True)
    status: Mapped[str] = mapped_column(String(20), default="pending", index=True)
    known_words_level: Mapped[int | None] = mapped_column(index=True, nullable=True)
    known_words_mode: Mapped[str] = mapped_column(String(20), default="coca_rank", index=True)
    known_words_value: Mapped[str] = mapped_column(String(20), default="3000")
    vocabulary_snapshot_count: Mapped[int] = mapped_column(default=0)
    error_code: Mapped[str | None] = mapped_column(String(50), nullable=True)
    error_message: Mapped[str | None] = mapped_column(String(500), nullable=True)
    queued_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class AnalysisJobVocabularySnapshot(Base):
    __tablename__ = "analysis_job_vocabulary_snapshots"
    __table_args__ = (
        UniqueConstraint("job_id", "normalized_word", "source_type", name="uq_job_snapshot_word_source"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    job_id: Mapped[int] = mapped_column(ForeignKey("analysis_jobs.id"), index=True)
    word: Mapped[str] = mapped_column(String(100))
    normalized_word: Mapped[str] = mapped_column(String(100), index=True)
    source_type: Mapped[str] = mapped_column(String(20))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class AnalysisResult(Base):
    __tablename__ = "analysis_results"

    id: Mapped[int] = mapped_column(primary_key=True)
    job_id: Mapped[int] = mapped_column(ForeignKey("analysis_jobs.id"), unique=True, index=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), index=True, nullable=True)
    book_id: Mapped[int] = mapped_column(ForeignKey("books.id"), index=True)
    total_word_count: Mapped[int] = mapped_column()
    unique_word_count: Mapped[int] = mapped_column()
    to_memorize_word_count: Mapped[int] = mapped_column()
    coverage_95_word_count: Mapped[int] = mapped_column()
    reading_level: Mapped[str] = mapped_column(String(20))
    reading_message: Mapped[str] = mapped_column(String(255))
    all_words_file_key: Mapped[str | None] = mapped_column(String(500), nullable=True)
    to_memorize_file_key: Mapped[str | None] = mapped_column(String(500), nullable=True)
    coverage_95_file_key: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class AnalysisResultChapter(Base):
    __tablename__ = "analysis_result_chapters"
    __table_args__ = (
        UniqueConstraint("result_id", "chapter_index", name="uq_result_chapter_index"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    result_id: Mapped[int] = mapped_column(ForeignKey("analysis_results.id"), index=True)
    chapter_index: Mapped[int] = mapped_column()
    chapter_title: Mapped[str] = mapped_column(String(255))
    total_word_count: Mapped[int] = mapped_column()
    unique_word_count: Mapped[int] = mapped_column()
    to_memorize_word_count: Mapped[int] = mapped_column()
    coverage_95_word_count: Mapped[int] = mapped_column()
    reading_level: Mapped[str] = mapped_column(String(20))
    reading_message: Mapped[str] = mapped_column(String(255))
    all_words_file_key: Mapped[str | None] = mapped_column(String(500), nullable=True)
    to_memorize_file_key: Mapped[str | None] = mapped_column(String(500), nullable=True)
    coverage_95_file_key: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class AnalysisResultItem(Base):
    __tablename__ = "analysis_result_items"
    __table_args__ = (
        UniqueConstraint("result_id", "list_type", "sequence_no", name="uq_result_list_sequence"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    result_id: Mapped[int] = mapped_column(ForeignKey("analysis_results.id"), index=True)
    sequence_no: Mapped[int] = mapped_column()
    word: Mapped[str] = mapped_column(String(100), index=True)
    lemma: Mapped[str | None] = mapped_column(String(100), nullable=True)
    book_frequency: Mapped[int] = mapped_column()
    coca_rank: Mapped[int | None] = mapped_column(nullable=True)
    is_known: Mapped[bool] = mapped_column(Boolean, default=False)
    is_to_memorize: Mapped[bool] = mapped_column(Boolean, default=False)
    is_coverage_95: Mapped[bool] = mapped_column(Boolean, default=False)
    list_type: Mapped[str] = mapped_column(String(30), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

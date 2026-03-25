from __future__ import annotations

import logging
from datetime import UTC, datetime
from pathlib import Path

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models.analysis import AnalysisJob, AnalysisResult, AnalysisResultItem
from app.models.book import Book
from app.models.user import UserVocabularyItem
from app.pipeline.analysis_pipeline import AnalysisPipeline
from app.schemas.analysis import AnalysisJobResponse, AnalysisResultResponse, KnownWordsMode


logger = logging.getLogger(__name__)


class AnalysisService:
    def __init__(self) -> None:
        self.settings = get_settings()
        self.pipeline = AnalysisPipeline()

    def create_job(
        self,
        db: Session,
        user_id: int,
        book_id: int,
        known_words_mode: KnownWordsMode,
        known_words_value: str,
    ) -> AnalysisJobResponse:
        book = db.get(Book, book_id)
        if book is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="book not found")

        job = AnalysisJob(
            user_id=user_id,
            book_id=book_id,
            status="pending",
            known_words_level=self._legacy_known_words_level(known_words_mode, known_words_value),
            known_words_mode=known_words_mode.value,
            known_words_value=known_words_value,
            vocabulary_snapshot_count=0,
        )
        db.add(job)
        db.commit()
        db.refresh(job)

        try:
            job.status = "processing"
            job.started_at = datetime.now(UTC)
            db.commit()

            user_known_words = self._load_user_known_words(db, user_id)
            pipeline_result = self.pipeline.run(
                Path(book.storage_key),
                known_words_mode,
                known_words_value,
                user_known_words=user_known_words,
            )
            result = AnalysisResult(
                job_id=job.id,
                user_id=user_id,
                book_id=book.id,
                total_word_count=pipeline_result.total_word_count,
                unique_word_count=pipeline_result.unique_word_count,
                to_memorize_word_count=pipeline_result.to_memorize_word_count,
                coverage_95_word_count=pipeline_result.coverage_95_word_count,
                reading_level=pipeline_result.reading_level,
                reading_message=pipeline_result.reading_message,
            )
            db.add(result)
            db.commit()
            db.refresh(result)

            result_dir = self.settings.results_storage_dir / str(result.id)
            all_words_path = result_dir / "all_words.csv"
            to_memorize_path = result_dir / "to_memorize.csv"
            coverage_95_path = result_dir / "coverage_95.csv"
            self.pipeline.write_csv(pipeline_result.all_words_rows, all_words_path)
            self.pipeline.write_csv(pipeline_result.to_memorize_rows, to_memorize_path)
            self.pipeline.write_csv(pipeline_result.coverage_95_rows, coverage_95_path)

            result.all_words_file_key = str(all_words_path.as_posix())
            result.to_memorize_file_key = str(to_memorize_path.as_posix())
            result.coverage_95_file_key = str(coverage_95_path.as_posix())
            db.commit()

            self._persist_result_items(
                db,
                result.id,
                pipeline_result.all_words_rows,
                pipeline_result.to_memorize_rows,
                pipeline_result.coverage_95_rows,
            )

            job.status = "completed"
            job.finished_at = datetime.now(UTC)
            db.commit()
            db.refresh(job)

            return self.to_job_response(job=job, result_id=result.id)
        except Exception as exc:
            job.status = "failed"
            job.error_code = "internal_error"
            job.error_message = str(exc)[:500]
            job.finished_at = datetime.now(UTC)
            db.commit()
            db.refresh(job)
            logger.exception("analysis_job_failed job_id=%s error=%s", job.id, exc)
            return self.to_job_response(job=job, result_id=None)

    def get_job(self, db: Session, user_id: int, job_id: int) -> AnalysisJobResponse:
        job = db.get(AnalysisJob, job_id)
        if job is None or job.user_id != user_id:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="job not found")

        result = db.scalar(select(AnalysisResult).where(AnalysisResult.job_id == job.id))
        result_id = result.id if result else None
        return self.to_job_response(job=job, result_id=result_id)

    def get_result(self, db: Session, user_id: int, result_id: int) -> AnalysisResultResponse:
        result = db.get(AnalysisResult, result_id)
        if result is None or result.user_id != user_id:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="result not found")

        book = db.get(Book, result.book_id)
        if book is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="book not found")

        created_at = result.created_at.isoformat() if result.created_at else datetime.now(UTC).isoformat()
        return self.pipeline.build_result_response(
            result_id=result.id,
            job_id=result.job_id,
            book_id=book.id,
            title=book.title,
            original_filename=book.original_filename,
            known_words_mode=self._get_job_known_words_mode(db, result.job_id),
            known_words_value=self._get_job_known_words_value(db, result.job_id),
            created_at=created_at,
            total_word_count=result.total_word_count,
            unique_word_count=result.unique_word_count,
            to_memorize_word_count=result.to_memorize_word_count,
            coverage_95_word_count=result.coverage_95_word_count,
            reading_level=result.reading_level,
            reading_label=self._reading_label(result.reading_level),
            reading_color=self._reading_color(result.reading_level),
            reading_message=result.reading_message,
        )

    def get_download_path(self, db: Session, user_id: int, result_id: int, download_type: str) -> Path:
        result = db.get(AnalysisResult, result_id)
        if result is None or result.user_id != user_id:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="result not found")
        path_map = {
            "all_words": result.all_words_file_key,
            "to_memorize": result.to_memorize_file_key,
            "coverage_95": result.coverage_95_file_key,
        }
        file_key = path_map[download_type]
        if not file_key:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="download file not found")
        return Path(file_key)

    def _persist_result_items(
        self,
        db: Session,
        result_id: int,
        all_rows: list[dict[str, object]],
        to_memorize_rows: list[dict[str, object]],
        coverage_95_rows: list[dict[str, object]],
    ) -> None:
        to_memorize_words = {str(row["单词"]) for row in to_memorize_rows}
        coverage_95_words = {str(row["单词"]) for row in coverage_95_rows}
        items = [
            AnalysisResultItem(
                result_id=result_id,
                sequence_no=int(row["序号"]),
                word=str(row["单词"]),
                lemma=str(row["原型"]) or None,
                book_frequency=int(row["书籍出现频率"]),
                coca_rank=int(row["COCA 排行"]) if row["COCA 排行"] not in ("", None) else None,
                is_known=str(row["是否已掌握"]).lower() == "true",
                is_to_memorize=str(row["单词"]) in to_memorize_words,
                is_coverage_95=str(row["单词"]) in coverage_95_words,
                list_type="all_words",
            )
            for row in all_rows
        ]
        db.add_all(items)
        db.commit()

    def _load_user_known_words(self, db: Session, user_id: int) -> set[str]:
        rows = db.scalars(
            select(UserVocabularyItem.normalized_word).where(UserVocabularyItem.user_id == user_id)
        )
        return set(rows.all())

    def _get_job(self, db: Session, job_id: int) -> AnalysisJob:
        job = db.get(AnalysisJob, job_id)
        if job is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="job not found")
        return job

    def _get_job_known_words_mode(self, db: Session, job_id: int) -> KnownWordsMode:
        job = self._get_job(db, job_id)
        return self._coerce_known_words_mode(job)

    def _get_job_known_words_value(self, db: Session, job_id: int) -> str:
        job = self._get_job(db, job_id)
        return self._coerce_known_words_value(job)

    def _reading_label(self, level: str) -> str:
        return {
            "level_1": "强推荐阅读",
            "level_2": "推荐阅读 + 学习",
            "level_3": "不推荐直接阅读",
        }[level]

    def _reading_color(self, level: str) -> str:
        return {
            "level_1": "green",
            "level_2": "yellow",
            "level_3": "red",
        }[level]

    def to_job_response(self, job: AnalysisJob, result_id: int | None) -> AnalysisJobResponse:
        return AnalysisJobResponse(
            job_id=job.id,
            book_id=job.book_id,
            status=job.status,
            known_words_mode=self._coerce_known_words_mode(job),
            known_words_value=self._coerce_known_words_value(job),
            error_code=job.error_code,
            error_message=job.error_message,
            queued_at=job.queued_at.isoformat() if job.queued_at else "",
            started_at=job.started_at.isoformat() if job.started_at else None,
            finished_at=job.finished_at.isoformat() if job.finished_at else None,
            result_id=result_id,
        )

    def _legacy_known_words_level(self, known_words_mode: KnownWordsMode, known_words_value: str) -> int | None:
        if known_words_mode == KnownWordsMode.coca_rank:
            return int(known_words_value)
        return None

    def _coerce_known_words_mode(self, job: AnalysisJob) -> KnownWordsMode:
        if job.known_words_mode:
            return KnownWordsMode(job.known_words_mode)
        return KnownWordsMode.coca_rank

    def _coerce_known_words_value(self, job: AnalysisJob) -> str:
        if job.known_words_value:
            return job.known_words_value
        if job.known_words_level is not None:
            return str(job.known_words_level)
        return "3000"

from __future__ import annotations

import csv
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
from app.schemas.analysis import (
    AnalysisDistributionResponse,
    AnalysisJobResponse,
    AnalysisResultResponse,
    DistributionBucket,
    KnownWordsMode,
)


logger = logging.getLogger(__name__)


DISTRIBUTION_BUCKETS = [
    {"key": "coca_1_1000", "label": "1-1000", "min_rank": 1, "max_rank": 1000},
    {"key": "coca_1001_2000", "label": "1001-2000", "min_rank": 1001, "max_rank": 2000},
    {"key": "coca_2001_3000", "label": "2001-3000", "min_rank": 2001, "max_rank": 3000},
    {"key": "coca_3001_5000", "label": "3001-5000", "min_rank": 3001, "max_rank": 5000},
    {"key": "coca_5001_8000", "label": "5001-8000", "min_rank": 5001, "max_rank": 8000},
    {"key": "coca_8001_12000", "label": "8001-12000", "min_rank": 8001, "max_rank": 12000},
    {"key": "coca_12001_15000", "label": "12001-15000", "min_rank": 12001, "max_rank": 15000},
    {"key": "coca_15001_plus", "label": "15001+", "min_rank": 15001, "max_rank": None},
    {"key": "unknown", "label": "未收录", "min_rank": None, "max_rank": None},
]


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
                book.file_type,
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
            coverage_95_anki_path = result_dir / "coverage_95_anki.csv"
            self.pipeline.write_csv(pipeline_result.all_words_rows, all_words_path)
            self.pipeline.write_csv(pipeline_result.to_memorize_rows, to_memorize_path)
            self.pipeline.write_csv(pipeline_result.coverage_95_rows, coverage_95_path)
            self.pipeline.write_anki_csv(pipeline_result.coverage_95_rows, coverage_95_anki_path)

            result.all_words_file_key = str(all_words_path.as_posix())
            result.to_memorize_file_key = str(to_memorize_path.as_posix())
            result.coverage_95_file_key = str(coverage_95_path.as_posix())
            db.commit()

            if self.settings.enable_analysis_result_items:
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
            file_type=book.file_type,
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
            "coverage_95_anki": self._build_anki_download_path(result.coverage_95_file_key),
        }
        file_key = path_map[download_type]
        if not file_key:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="download file not found")
        download_path = Path(file_key)
        if download_type == "coverage_95_anki" and not download_path.exists():
            self._ensure_anki_export(download_path=download_path, coverage_95_file_key=result.coverage_95_file_key)
        if not download_path.exists():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="download file not found")
        return download_path

    def get_distribution(self, db: Session, user_id: int, result_id: int) -> AnalysisDistributionResponse:
        result = db.get(AnalysisResult, result_id)
        if result is None or result.user_id != user_id:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="result not found")

        job = self._get_job(db, result.job_id)
        bucket_totals = self._load_distribution_from_items(db=db, result_id=result.id)
        if bucket_totals is None:
            bucket_totals = self._load_distribution_from_csv(result.all_words_file_key)

        total_word_count = result.total_word_count if result.total_word_count > 0 else sum(bucket_totals.values())
        buckets = [
            DistributionBucket(
                key=bucket["key"],
                label=bucket["label"],
                token_count=bucket_totals[bucket["key"]],
                token_ratio=(bucket_totals[bucket["key"]] / total_word_count) if total_word_count > 0 else 0,
            )
            for bucket in DISTRIBUTION_BUCKETS
        ]
        return AnalysisDistributionResponse(
            buckets=buckets,
            known_words_mode=self._coerce_known_words_mode(job),
            known_words_value=self._coerce_known_words_value(job),
            total_word_count=total_word_count,
        )

    def _build_anki_download_path(self, coverage_95_file_key: str | None) -> str | None:
        if not coverage_95_file_key:
            return None
        return str(Path(coverage_95_file_key).with_name("coverage_95_anki.csv"))

    def _init_distribution_totals(self) -> dict[str, int]:
        return {bucket["key"]: 0 for bucket in DISTRIBUTION_BUCKETS}

    def _load_distribution_from_items(self, db: Session, result_id: int) -> dict[str, int] | None:
        rows = db.scalars(select(AnalysisResultItem).where(AnalysisResultItem.result_id == result_id)).all()
        if not rows:
            return None

        bucket_totals = self._init_distribution_totals()
        for row in rows:
            bucket_totals[self._bucket_key_for_rank(row.coca_rank)] += row.book_frequency
        return bucket_totals

    def _load_distribution_from_csv(self, all_words_file_key: str | None) -> dict[str, int]:
        if not all_words_file_key:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="distribution source not found")

        all_words_path = Path(all_words_file_key)
        if not all_words_path.exists():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="distribution source not found")

        bucket_totals = self._init_distribution_totals()
        with all_words_path.open("r", newline="", encoding="utf-8-sig") as file:
            reader = csv.DictReader(file)
            for row in reader:
                coca_rank_raw = row.get("COCA 排行")
                frequency_raw = row.get("书籍出现频率")
                coca_rank = int(coca_rank_raw) if coca_rank_raw not in ("", None) else None
                frequency = int(frequency_raw) if frequency_raw not in ("", None) else 0
                bucket_totals[self._bucket_key_for_rank(coca_rank)] += frequency
        return bucket_totals

    def _bucket_key_for_rank(self, coca_rank: int | None) -> str:
        if coca_rank is None:
            return "unknown"

        for bucket in DISTRIBUTION_BUCKETS:
            min_rank = bucket["min_rank"]
            max_rank = bucket["max_rank"]
            if min_rank is None:
                continue
            if max_rank is None and coca_rank >= min_rank:
                return str(bucket["key"])
            if min_rank <= coca_rank <= max_rank:
                return str(bucket["key"])
        return "unknown"

    def _ensure_anki_export(self, download_path: Path, coverage_95_file_key: str | None) -> None:
        if not coverage_95_file_key:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="download file not found")

        coverage_95_path = Path(coverage_95_file_key)
        if not coverage_95_path.exists():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="download file not found")

        with coverage_95_path.open("r", newline="", encoding="utf-8-sig") as file:
            reader = csv.DictReader(file)
            coverage_rows = list(reader)

        self.pipeline.write_anki_csv(coverage_rows, download_path)

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

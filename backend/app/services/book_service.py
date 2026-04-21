from __future__ import annotations

import hashlib
import logging
import uuid
from dataclasses import dataclass
from pathlib import Path
from zipfile import BadZipFile, ZipFile

from fastapi import HTTPException, UploadFile, status
from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models.analysis import AnalysisJob, AnalysisJobVocabularySnapshot, AnalysisResult, AnalysisResultItem
from app.models.book import Book
from app.schemas.books import HistoryItem


logger = logging.getLogger(__name__)


@dataclass(slots=True)
class BookUploadResult:
    book: Book
    is_duplicate: bool


class BookService:
    """Handle book upload, validation, storage, and deduplication."""

    def __init__(self) -> None:
        self.settings = get_settings()

    async def create_or_get_book(
        self,
        db: Session,
        user_id: int,
        file: UploadFile,
        original_filename: str | None = None,
    ) -> BookUploadResult:
        filename = (original_filename or "unknown.epub").strip() or "unknown.epub"
        self._validate_extension(filename)
        storage_root = self.settings.books_storage_dir
        storage_root.mkdir(parents=True, exist_ok=True)
        temp_path = storage_root / f"upload-{uuid.uuid4().hex}.tmp"

        try:
            file_hash, file_size_bytes = await self._save_upload_to_temp(file=file, temp_path=temp_path)

            self._validate_epub_file(temp_path)

            existing_book = db.scalar(select(Book).where(Book.file_hash == file_hash))
            if existing_book is not None:
                temp_path.unlink(missing_ok=True)
                return BookUploadResult(book=existing_book, is_duplicate=True)

            storage_path = self._build_storage_path(file_hash)
            storage_path.parent.mkdir(parents=True, exist_ok=True)
            temp_path.replace(storage_path)
        except Exception:
            temp_path.unlink(missing_ok=True)
            logger.exception("book_upload_failed user_id=%s filename=%s", user_id, filename)
            raise

        book = Book(
            file_hash=file_hash,
            original_filename=filename,
            title=Path(filename).stem,
            language="en",
            file_size_bytes=file_size_bytes,
            storage_key=str(storage_path.as_posix()),
            text_extract_status="pending",
            created_by_user_id=user_id,
        )
        db.add(book)
        db.commit()
        db.refresh(book)
        return BookUploadResult(book=book, is_duplicate=False)

    def get_history(self, db: Session, user_id: int, page: int = 1, page_size: int = 20) -> tuple[list[HistoryItem], int]:
        offset = max(page - 1, 0) * page_size
        query = (
            select(AnalysisResult, AnalysisJob, Book)
            .join(AnalysisJob, AnalysisResult.job_id == AnalysisJob.id)
            .join(Book, AnalysisResult.book_id == Book.id)
            .where(AnalysisResult.user_id == user_id)
            .order_by(AnalysisResult.created_at.desc())
        )

        rows = db.execute(query.offset(offset).limit(page_size)).all()
        items = [
            HistoryItem(
                result_id=result.id,
                job_id=job.id,
                book_id=book.id,
                title=book.title,
                original_filename=book.original_filename,
                status=job.status,
                known_words_mode=job.known_words_mode or "coca_rank",
                known_words_value=job.known_words_value or str(job.known_words_level or 3000),
                to_memorize_word_count=result.to_memorize_word_count,
                created_at=result.created_at.isoformat() if result.created_at else "",
            )
            for result, job, book in rows
        ]

        total = int(
            db.scalar(select(func.count()).select_from(AnalysisResult).where(AnalysisResult.user_id == user_id))
            or 0
        )
        return items, total

    def delete_history(self, db: Session, user_id: int, result_id: int) -> bool:
        result = db.get(AnalysisResult, result_id)
        if result is None or result.user_id != user_id:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="history not found")

        job = db.get(AnalysisJob, result.job_id)
        book = db.get(Book, result.book_id)

        self._delete_result_files(result)

        db.execute(delete(AnalysisResultItem).where(AnalysisResultItem.result_id == result.id))
        db.delete(result)

        if job is not None:
            db.execute(delete(AnalysisJobVocabularySnapshot).where(AnalysisJobVocabularySnapshot.job_id == job.id))
            db.delete(job)

        db.commit()

        if book is not None:
            remaining_job_count = int(
                db.scalar(select(func.count()).select_from(AnalysisJob).where(AnalysisJob.book_id == book.id)) or 0
            )
            remaining_result_count = int(
                db.scalar(select(func.count()).select_from(AnalysisResult).where(AnalysisResult.book_id == book.id)) or 0
            )
            if remaining_job_count == 0 and remaining_result_count == 0:
                self._delete_book_file(book)
                db.delete(book)
                db.commit()

        return True

    def _validate_extension(self, filename: str) -> None:
        if Path(filename).suffix.lower() != ".epub":
            raise HTTPException(
                status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
                detail="only .epub files are supported",
            )

    async def _save_upload_to_temp(self, file: UploadFile, temp_path: Path) -> tuple[str, int]:
        hasher = hashlib.sha256()
        total_size = 0
        max_size_bytes = self.settings.book_upload_max_size_bytes

        with temp_path.open("wb") as target:
            while True:
                chunk = await file.read(1024 * 1024)
                if not chunk:
                    break
                total_size += len(chunk)
                if total_size > max_size_bytes:
                    temp_path.unlink(missing_ok=True)
                    raise HTTPException(
                        status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                        detail=f"epub file too large, max {self.settings.book_upload_max_size_mb}MB",
                    )
                hasher.update(chunk)
                target.write(chunk)

        if total_size == 0:
            temp_path.unlink(missing_ok=True)
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="empty file")

        return hasher.hexdigest(), total_size

    def _validate_epub_file(self, file_path: Path) -> None:
        try:
            with ZipFile(file_path) as archive:
                names = set(archive.namelist())
                mimetype = archive.read("mimetype") if "mimetype" in names else b""
        except KeyError as exc:
            raise HTTPException(
                status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
                detail="invalid epub file",
            ) from exc
        except BadZipFile as exc:
            raise HTTPException(
                status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
                detail="invalid epub file",
            ) from exc

        mimetype_text = mimetype.decode("utf-8", errors="ignore").strip()
        if mimetype_text == "application/epub+zip":
            return

        # 兼容部分可正常阅读但打包不规范的 EPUB。
        has_container = "META-INF/container.xml" in names
        has_package_document = any(name.lower().endswith(".opf") for name in names)
        has_readable_content = any(
            name.lower().endswith((".xhtml", ".html", ".htm"))
            for name in names
        )
        if has_container and has_package_document and has_readable_content:
            return

        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="invalid epub mimetype",
        )

    def _build_storage_path(self, file_hash: str) -> Path:
        return self.settings.books_storage_dir / f"{file_hash}.epub"

    def _delete_result_files(self, result: AnalysisResult) -> None:
        paths = [
            result.all_words_file_key,
            result.to_memorize_file_key,
            result.coverage_95_file_key,
        ]
        deleted_parents: set[Path] = set()

        for raw_path in paths:
            if not raw_path:
                continue
            file_path = Path(raw_path)
            try:
                if file_path.exists():
                    file_path.unlink()
                parent = file_path.parent
                if parent not in deleted_parents and parent.exists() and not any(parent.iterdir()):
                    parent.rmdir()
                    deleted_parents.add(parent)
            except OSError:
                continue

    def _delete_book_file(self, book: Book) -> None:
        file_path = Path(book.storage_key)
        try:
            if file_path.exists():
                file_path.unlink()
        except OSError:
            return

from __future__ import annotations

import io
import tempfile
import unittest
import zipfile
from pathlib import Path

from fastapi import HTTPException, UploadFile
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.db.base import Base
from app.pipeline.analysis_pipeline import AnalysisPipeline
from app.services.book_service import BookService


class BookTxtSupportTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.storage_root = Path(self.temp_dir.name)

        self.engine = create_engine("sqlite:///:memory:", future=True)
        Base.metadata.create_all(self.engine)
        self.session_factory = sessionmaker(bind=self.engine, autoflush=False, autocommit=False, class_=Session)

        self.book_service = BookService()
        self.book_service.settings.storage_root = str(self.storage_root)
        self.pipeline = AnalysisPipeline()

    def tearDown(self) -> None:
        self.engine.dispose()
        self.temp_dir.cleanup()

    def test_txt_book_upload_and_deduplication(self) -> None:
        with self.session_factory() as db:
            upload = UploadFile(filename="novel.txt", file=io.BytesIO(b"hello world\nhello reading"))
            created = self._run_async(
                self.book_service.create_or_get_book(db=db, user_id=1, file=upload, original_filename="novel.txt")
            )

            self.assertFalse(created.is_duplicate)
            self.assertEqual(created.book.file_type, "txt")
            self.assertTrue(created.book.storage_key.endswith(".txt"))

            duplicate_upload = UploadFile(filename="novel-copy.txt", file=io.BytesIO(b"hello world\nhello reading"))
            duplicate = self._run_async(
                self.book_service.create_or_get_book(
                    db=db,
                    user_id=1,
                    file=duplicate_upload,
                    original_filename="novel-copy.txt",
                )
            )

            self.assertTrue(duplicate.is_duplicate)
            self.assertEqual(duplicate.book.id, created.book.id)

    def test_txt_pipeline_extracts_plain_text(self) -> None:
        txt_path = self.storage_root / "sample.txt"
        txt_path.write_text("Hello reader.\nThis book is only English text.", encoding="utf-8")

        result = self.pipeline.run(
            book_path=txt_path,
            file_type="txt",
            known_words_mode="coca_rank",
            known_words_value="3000",
            user_known_words=set(),
        )

        self.assertGreater(result.total_word_count, 0)
        self.assertGreater(result.unique_word_count, 0)

    def test_empty_txt_raises_readable_error(self) -> None:
        txt_path = self.storage_root / "blank.txt"
        txt_path.write_text("   \n\t", encoding="utf-8")

        with self.assertRaises(HTTPException) as context:
            self.pipeline.extract_book_text(book_path=txt_path, file_type="txt")

        self.assertEqual(context.exception.status_code, 422)
        self.assertEqual(context.exception.detail, "unable to extract readable text from txt")

    def test_epub_pipeline_still_extracts_content(self) -> None:
        epub_path = self.storage_root / "sample.epub"
        with zipfile.ZipFile(epub_path, "w") as archive:
            archive.writestr("mimetype", "application/epub+zip")
            archive.writestr("META-INF/container.xml", "<container></container>")
            archive.writestr("OPS/content.opf", "<package></package>")
            archive.writestr("OPS/chapter1.xhtml", "<html><body>Hello epub world</body></html>")

        text = self.pipeline.extract_book_text(book_path=epub_path, file_type="epub")
        self.assertIn("Hello epub world", text)

    def test_unsupported_extension_is_rejected(self) -> None:
        with self.assertRaises(HTTPException) as context:
            self.book_service._validate_extension("book.pdf")

        self.assertEqual(context.exception.status_code, 415)
        self.assertEqual(context.exception.detail, "only .epub, .txt files are supported")

    @staticmethod
    def _run_async(awaitable):
        import asyncio

        return asyncio.run(awaitable)

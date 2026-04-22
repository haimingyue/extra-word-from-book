from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from ebooklib import epub
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.db.base import Base
from app.models.analysis import AnalysisResult, AnalysisResultChapter
from app.models.book import Book
from app.models.user import User
from app.models.user import UserVocabulary, UserVocabularyItem
from app.pipeline.analysis_pipeline import AnalysisPipeline
from app.schemas.analysis import KnownWordsMode
from app.services.analysis_service import AnalysisService
from app.services.book_service import BookService


class AnalysisChaptersTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.storage_root = Path(self.temp_dir.name)

        self.engine = create_engine("sqlite:///:memory:", future=True)
        Base.metadata.create_all(self.engine)
        self.session_factory = sessionmaker(bind=self.engine, autoflush=False, autocommit=False, class_=Session)

        self.pipeline = AnalysisPipeline()
        self.analysis_service = AnalysisService()
        self.analysis_service.settings.storage_root = str(self.storage_root)
        self.analysis_service.settings.enable_analysis_result_items = False

        self.book_service = BookService()
        self.book_service.settings.storage_root = str(self.storage_root)

    def tearDown(self) -> None:
        self.engine.dispose()
        self.temp_dir.cleanup()

    def test_epub_chapter_extraction_respects_spine_and_filters_short_sections(self) -> None:
        epub_path = self._build_epub(
            "ordered.epub",
            [
                ("版权页", "rights " * 20),
                ("Second Chapter", "orange apple reader future language " * 80),
                ("First Chapter", "forest bright window travel memory " * 90),
            ],
            spine_order=[3, 2, 1],
        )

        chapters = self.pipeline.extract_chapters(epub_path, "epub")

        self.assertEqual(len(chapters), 2)
        self.assertEqual(chapters[0].chapter_title, "First Chapter")
        self.assertEqual(chapters[1].chapter_title, "Second Chapter")
        self.assertEqual(chapters[0].chapter_index, 1)
        self.assertGreater(len(chapters[0].text.split()), 80)

    def test_analysis_service_persists_chapters_and_chapter_downloads(self) -> None:
        epub_path = self._build_epub(
            "novel.epub",
            [
                ("Chapter One", "orange apple reader future language " * 90),
                ("Chapter Two", "forest bright window travel memory " * 95),
            ],
        )

        with self.session_factory() as db:
            user = User(email="reader@example.com", password_hash="hashed", status="active")
            db.add(user)
            db.commit()
            db.refresh(user)

            book = Book(
                file_hash="book-hash",
                file_type="epub",
                original_filename="novel.epub",
                title="novel",
                language="en",
                file_size_bytes=epub_path.stat().st_size,
                storage_key=str(epub_path),
                text_extract_status="done",
                created_by_user_id=user.id,
            )
            db.add(book)
            db.commit()
            db.refresh(book)

            job = self.analysis_service.create_job(
                db=db,
                user_id=user.id,
                book_id=book.id,
                known_words_mode=KnownWordsMode.coca_rank,
                known_words_value="3000",
            )

            self.assertEqual(job.status, "completed")
            self.assertIsNotNone(job.result_id)

            result = db.get(AnalysisResult, job.result_id)
            self.assertIsNotNone(result)

            chapters = db.query(AnalysisResultChapter).filter(AnalysisResultChapter.result_id == result.id).all()
            self.assertEqual(len(chapters), 2)

            chapter_list = self.analysis_service.list_chapters(db=db, user_id=user.id, result_id=result.id)
            self.assertTrue(chapter_list.supported)
            self.assertEqual(len(chapter_list.items), 2)

            chapter_detail = self.analysis_service.get_chapter_detail(
                db=db,
                user_id=user.id,
                result_id=result.id,
                chapter_id=chapters[0].id,
            )
            self.assertTrue(chapter_detail.downloads.all_words.endswith("/downloads/all_words"))

            chapter_download = self.analysis_service.get_chapter_download_path(
                db=db,
                user_id=user.id,
                result_id=result.id,
                chapter_id=chapters[0].id,
                download_type="coverage_95_anki",
            )
            self.assertTrue(chapter_download.exists())

            import_response = self.analysis_service.import_chapter_words_to_vocabulary(
                db=db,
                user_id=user.id,
                result_id=result.id,
                chapter_id=chapters[0].id,
            )
            self.assertGreater(import_response.imported_count, 0)
            vocabulary = db.get(UserVocabulary, import_response.vocabulary_id)
            self.assertIsNotNone(vocabulary)
            imported_items = db.query(UserVocabularyItem).filter(UserVocabularyItem.vocabulary_id == vocabulary.id).count()
            self.assertEqual(imported_items, vocabulary.item_count)

            self.book_service.delete_history(db=db, user_id=user.id, result_id=result.id)
            self.assertFalse(chapter_download.exists())
            self.assertEqual(
                db.query(AnalysisResultChapter).filter(AnalysisResultChapter.result_id == result.id).count(),
                0,
            )

    def _build_epub(self, filename: str, chapters: list[tuple[str, str]], spine_order: list[int] | None = None) -> Path:
        book = epub.EpubBook()
        book.set_identifier(f"id-{filename}")
        book.set_title("Sample")
        book.set_language("en")

        items = []
        for index, (title, body) in enumerate(chapters, start=1):
            item = epub.EpubHtml(title=title, file_name=f"chapter{index}.xhtml", lang="en")
            item.content = f"<html><head><title>{title}</title></head><body><h1>{title}</h1><p>{body}</p></body></html>"
            book.add_item(item)
            items.append(item)

        ordered_items = items if spine_order is None else [items[index - 1] for index in spine_order]
        book.toc = tuple(ordered_items)
        book.spine = ["nav", *ordered_items]
        book.add_item(epub.EpubNcx())
        book.add_item(epub.EpubNav())

        output_path = self.storage_root / filename
        epub.write_epub(str(output_path), book)
        return output_path

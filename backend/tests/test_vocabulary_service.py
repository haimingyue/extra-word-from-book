from __future__ import annotations

import unittest

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.db.base import Base
from app.models.user import User, UserVocabulary, UserVocabularyItem
from app.services.vocabulary_service import VocabularyService


class VocabularyServiceTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = create_engine("sqlite:///:memory:", future=True)
        Base.metadata.create_all(self.engine)
        self.session_factory = sessionmaker(bind=self.engine, autoflush=False, autocommit=False, class_=Session)
        self.service = VocabularyService()

    def tearDown(self) -> None:
        self.engine.dispose()

    def test_add_item_without_vocabulary_id_creates_primary_vocabulary(self) -> None:
        with self.session_factory() as db:
            user = User(email="owner@example.com", password_hash="hashed", status="active")
            db.add(user)
            db.commit()
            db.refresh(user)

            item_id, created = self.service.add_item(
                db=db,
                user_id=user.id,
                vocabulary_id=None,
                word="Reader",
            )

            self.assertTrue(created)
            item = db.get(UserVocabularyItem, item_id)
            self.assertIsNotNone(item)
            self.assertEqual(item.word, "reader")
            self.assertIsNotNone(item.vocabulary_id)

            vocabulary = db.get(UserVocabulary, item.vocabulary_id)
            self.assertIsNotNone(vocabulary)
            self.assertEqual(vocabulary.user_id, user.id)
            self.assertTrue(vocabulary.is_primary)
            self.assertEqual(vocabulary.item_count, 1)

            duplicate_item_id, duplicate_created = self.service.add_item(
                db=db,
                user_id=user.id,
                vocabulary_id=None,
                word="reader",
            )

            self.assertEqual(duplicate_item_id, item_id)
            self.assertFalse(duplicate_created)
            db.refresh(vocabulary)
            self.assertEqual(vocabulary.item_count, 1)

    def test_clear_items_removes_all_words_and_resets_count(self) -> None:
        with self.session_factory() as db:
            user = User(email="owner@example.com", password_hash="hashed", status="active")
            db.add(user)
            db.commit()
            db.refresh(user)

            vocabulary = UserVocabulary(
                user_id=user.id,
                name="我的主词库",
                is_primary=True,
                source_type="manual",
                item_count=3,
            )
            db.add(vocabulary)
            db.commit()
            db.refresh(vocabulary)

            for word in ["apple", "orange", "reader"]:
                db.add(
                    UserVocabularyItem(
                        vocabulary_id=vocabulary.id,
                        user_id=user.id,
                        word=word,
                        lemma=word,
                        normalized_word=word,
                    )
                )
            db.commit()

            deleted_count = self.service.clear_items(db=db, user_id=user.id, vocabulary_id=vocabulary.id)

            self.assertEqual(deleted_count, 3)
            self.assertEqual(
                db.query(UserVocabularyItem).filter(UserVocabularyItem.vocabulary_id == vocabulary.id).count(),
                0,
            )
            db.refresh(vocabulary)
            self.assertEqual(vocabulary.item_count, 0)

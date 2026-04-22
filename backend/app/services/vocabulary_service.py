from __future__ import annotations

import re
from datetime import UTC, datetime

from fastapi import HTTPException, UploadFile, status
from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.models.user import UserVocabulary, UserVocabularyItem
from app.schemas.vocabularies import VocabularyItem, VocabularyListItem


class VocabularyService:
    def list_vocabularies(self, db: Session, user_id: int) -> list[VocabularyListItem]:
        vocabularies = db.scalars(
            select(UserVocabulary)
            .where(UserVocabulary.user_id == user_id)
            .order_by(UserVocabulary.created_at.desc())
        ).all()
        return [
            VocabularyListItem(
                vocabulary_id=vocab.id,
                name=vocab.name,
                is_primary=vocab.is_primary,
                item_count=vocab.item_count,
                created_at=vocab.created_at.isoformat() if vocab.created_at else "",
            )
            for vocab in vocabularies
        ]

    async def import_txt(
        self,
        db: Session,
        user_id: int,
        file: UploadFile,
        name: str | None = None,
    ) -> tuple[int, str, int, int]:
        filename = file.filename or "vocabulary.txt"
        if not filename.lower().endswith(".txt"):
            raise HTTPException(
                status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
                detail="only .txt files are supported for vocabulary import",
            )

        content = await file.read()
        if not content:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="empty vocabulary file")

        try:
            text = content.decode("utf-8-sig")
        except UnicodeDecodeError:
            text = content.decode("utf-8", errors="ignore")

        words = self._extract_words_from_txt(text)
        if not words:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="no valid words found in txt")

        vocabulary = self._get_or_create_primary_vocabulary(
            db,
            user_id=user_id,
            provided_name=name or filename,
        )
        imported_count, deduplicated_count = self._upsert_items(db, vocabulary, words)
        vocabulary.item_count = self._count_vocabulary_items(db, vocabulary.id)
        vocabulary.source_type = "txt_upload"
        vocabulary.source_file_key = filename
        vocabulary.updated_at = datetime.now(UTC)
        db.commit()
        db.refresh(vocabulary)
        return vocabulary.id, vocabulary.name, imported_count, deduplicated_count

    def get_items(
        self,
        db: Session,
        user_id: int,
        vocabulary_id: int,
        page: int = 1,
        page_size: int = 20,
        keyword: str | None = None,
        starts_with: str | None = None,
    ) -> tuple[list[VocabularyItem], int]:
        vocabulary = db.get(UserVocabulary, vocabulary_id)
        if vocabulary is None or vocabulary.user_id != user_id:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="vocabulary not found")

        query = select(UserVocabularyItem).where(UserVocabularyItem.vocabulary_id == vocabulary_id)
        if keyword:
            normalized_keyword = self._normalize_search_keyword(keyword)
            if normalized_keyword:
                query = query.where(UserVocabularyItem.normalized_word.contains(normalized_keyword))
        if starts_with:
            initial = self._normalize_search_keyword(starts_with)[:1]
            if initial:
                query = query.where(UserVocabularyItem.normalized_word.startswith(initial))
        total = db.scalar(select(func.count()).select_from(query.subquery())) or 0
        offset = max(page - 1, 0) * page_size
        rows = db.scalars(
            query.order_by(UserVocabularyItem.id.desc()).offset(offset).limit(page_size)
        ).all()
        return (
            [VocabularyItem(item_id=row.id, word=row.word, lemma=row.lemma) for row in rows],
            int(total),
        )

    def add_item(self, db: Session, user_id: int, vocabulary_id: int | None, word: str) -> tuple[int, bool]:
        if vocabulary_id is None:
            vocabulary = self._get_or_create_primary_vocabulary(
                db,
                user_id=user_id,
                provided_name="我的主词库",
            )
        else:
            vocabulary = db.get(UserVocabulary, vocabulary_id)
            if vocabulary is None or vocabulary.user_id != user_id:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="vocabulary not found")

        normalized = self._normalize_word(word)
        if not normalized:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="invalid word")

        existing = db.scalar(
            select(UserVocabularyItem).where(
                UserVocabularyItem.vocabulary_id == vocabulary_id,
                UserVocabularyItem.normalized_word == normalized,
            )
        )
        if existing is not None:
            return existing.id, False

        item = UserVocabularyItem(
            vocabulary_id=vocabulary_id,
            user_id=vocabulary.user_id,
            word=normalized,
            lemma=None,
            normalized_word=normalized,
        )
        db.add(item)
        db.commit()
        db.refresh(item)

        vocabulary.item_count = self._count_vocabulary_items(db, vocabulary.id)
        vocabulary.updated_at = datetime.now(UTC)
        db.commit()
        return item.id, True

    def import_words(
        self,
        db: Session,
        user_id: int,
        words: list[str],
        vocabulary_id: int | None = None,
        source_type: str = "manual",
        source_file_key: str | None = None,
    ) -> tuple[int, str, int, int]:
        normalized_words = [normalized for word in words if (normalized := self._normalize_word(word))]
        if not normalized_words:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="no valid words found")

        if vocabulary_id is None:
            vocabulary = self._get_or_create_primary_vocabulary(
                db,
                user_id=user_id,
                provided_name="我的主词库",
            )
        else:
            vocabulary = db.get(UserVocabulary, vocabulary_id)
            if vocabulary is None or vocabulary.user_id != user_id:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="vocabulary not found")

        imported_count, deduplicated_count = self._upsert_items(db, vocabulary, normalized_words)
        vocabulary.item_count = self._count_vocabulary_items(db, vocabulary.id)
        vocabulary.source_type = source_type
        vocabulary.source_file_key = source_file_key
        vocabulary.updated_at = datetime.now(UTC)
        db.commit()
        db.refresh(vocabulary)
        return vocabulary.id, vocabulary.name, imported_count, deduplicated_count

    def delete_item(self, db: Session, user_id: int, item_id: int) -> bool:
        item = db.get(UserVocabularyItem, item_id)
        if item is None:
            return False

        vocabulary = db.get(UserVocabulary, item.vocabulary_id)
        if vocabulary is None or vocabulary.user_id != user_id:
            return False
        db.delete(item)
        db.commit()

        if vocabulary is not None:
            vocabulary.item_count = self._count_vocabulary_items(db, vocabulary.id)
            vocabulary.updated_at = datetime.now(UTC)
            db.commit()
        return True

    def batch_delete_items(self, db: Session, user_id: int, item_ids: list[int]) -> int:
        normalized_ids = sorted({item_id for item_id in item_ids if item_id > 0})
        if not normalized_ids:
            return 0

        items = db.scalars(
            select(UserVocabularyItem).where(
                UserVocabularyItem.id.in_(normalized_ids),
                UserVocabularyItem.user_id == user_id,
            )
        ).all()
        if not items:
            return 0

        vocabulary_ids = {item.vocabulary_id for item in items}
        db.execute(
            delete(UserVocabularyItem).where(
                UserVocabularyItem.id.in_([item.id for item in items]),
                UserVocabularyItem.user_id == user_id,
            )
        )
        db.commit()

        for vocabulary_id in vocabulary_ids:
            vocabulary = db.get(UserVocabulary, vocabulary_id)
            if vocabulary is None or vocabulary.user_id != user_id:
                continue
            vocabulary.item_count = self._count_vocabulary_items(db, vocabulary_id)
            vocabulary.updated_at = datetime.now(UTC)
        db.commit()
        return len(items)

    def clear_items(self, db: Session, user_id: int, vocabulary_id: int) -> int:
        vocabulary = db.get(UserVocabulary, vocabulary_id)
        if vocabulary is None or vocabulary.user_id != user_id:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="vocabulary not found")

        deleted_count = db.scalar(
            select(func.count()).select_from(
                select(UserVocabularyItem.id)
                .where(
                    UserVocabularyItem.vocabulary_id == vocabulary_id,
                    UserVocabularyItem.user_id == user_id,
                )
                .subquery()
            )
        )
        if not deleted_count:
            vocabulary.item_count = 0
            vocabulary.updated_at = datetime.now(UTC)
            db.commit()
            return 0

        db.execute(
            delete(UserVocabularyItem).where(
                UserVocabularyItem.vocabulary_id == vocabulary_id,
                UserVocabularyItem.user_id == user_id,
            )
        )
        vocabulary.item_count = 0
        vocabulary.updated_at = datetime.now(UTC)
        db.commit()
        return int(deleted_count)

    def _extract_words_from_txt(self, text: str) -> list[str]:
        words: list[str] = []
        for line in text.splitlines():
            raw = line.strip()
            if not raw or raw.startswith("#"):
                continue

            parts = raw.split("\t")
            candidate = ""
            if len(parts) >= 2:
                candidate = parts[1].strip()
            if not candidate:
                candidate = parts[0].strip()

            normalized = self._normalize_word(candidate)
            if normalized:
                words.append(normalized)
                continue

            # fallback: extract the first English token in the line
            match = re.search(r"[A-Za-z]+(?:'[A-Za-z]+)?", raw)
            if match:
                fallback = self._normalize_word(match.group(0))
                if fallback:
                    words.append(fallback)
        return words

    def _normalize_word(self, value: str) -> str:
        token = value.strip().lower()
        token = token.replace("’", "'")
        if not token:
            return ""
        if not re.fullmatch(r"[a-z]+(?:'[a-z]+)?", token):
            return ""
        return token

    def _normalize_search_keyword(self, value: str) -> str:
        return re.sub(r"[^a-z']", "", value.strip().lower().replace("’", "'"))

    def _get_or_create_primary_vocabulary(
        self,
        db: Session,
        user_id: int,
        provided_name: str,
    ) -> UserVocabulary:
        vocabulary = db.scalar(
            select(UserVocabulary).where(
                UserVocabulary.user_id == user_id,
                UserVocabulary.is_primary == True,  # noqa: E712
            )
        )
        if vocabulary is not None:
            return vocabulary

        vocabulary = UserVocabulary(
            user_id=user_id,
            name=provided_name,
            is_primary=True,
            source_type="manual",
            source_file_key=None,
            item_count=0,
        )
        db.add(vocabulary)
        db.commit()
        db.refresh(vocabulary)
        return vocabulary

    def _upsert_items(self, db: Session, vocabulary: UserVocabulary, words: list[str]) -> tuple[int, int]:
        existing_words = set(
            db.scalars(
                select(UserVocabularyItem.normalized_word).where(
                    UserVocabularyItem.vocabulary_id == vocabulary.id
                )
            ).all()
        )
        unique_input = []
        seen_input: set[str] = set()
        for word in words:
            if word in seen_input:
                continue
            seen_input.add(word)
            unique_input.append(word)

        to_insert = [word for word in unique_input if word not in existing_words]
        imported_count = len(to_insert)
        deduplicated_count = len(words) - imported_count

        for word in to_insert:
            db.add(
                UserVocabularyItem(
                    vocabulary_id=vocabulary.id,
                    user_id=vocabulary.user_id,
                    word=word,
                    lemma=None,
                    normalized_word=word,
                )
            )
        db.commit()
        return imported_count, deduplicated_count

    def _count_vocabulary_items(self, db: Session, vocabulary_id: int) -> int:
        count = db.scalar(
            select(func.count()).select_from(UserVocabularyItem).where(
                UserVocabularyItem.vocabulary_id == vocabulary_id
            )
        )
        return int(count or 0)

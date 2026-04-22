from __future__ import annotations

import csv
import logging
import re
from collections import Counter
from collections.abc import Iterable, Iterator
from dataclasses import dataclass
from html import unescape
from pathlib import Path
from zipfile import BadZipFile, ZipFile

from fastapi import HTTPException, status

from app.pipeline.resources import load_coca_rank_dict, load_dictionary_words, load_exam_level_dict, load_lemma_dict
from app.schemas.analysis import (
    AnalysisResultResponse,
    AnalysisSummary,
    BookSummary,
    KnownWordsMode,
    ReadingAdvice,
    ResultDownloads,
)


logger = logging.getLogger(__name__)


ABBREVIATION_BLOCKLIST = {"isbn", "jr", "pp"}
SHORT_WORD_BLOCKLIST = {"b", "c", "d", "er", "h", "j", "k", "m", "mr", "o", "p", "t"}
SHORT_WORD_WHITELIST = {
    "a",
    "am",
    "an",
    "as",
    "at",
    "be",
    "by",
    "do",
    "go",
    "he",
    "i",
    "if",
    "in",
    "is",
    "it",
    "me",
    "my",
    "no",
    "of",
    "on",
    "or",
    "ox",
    "so",
    "to",
    "up",
    "us",
    "we",
}
VALID_TOKEN_PATTERN = re.compile(r"[a-z]+(?:'[a-z]+)?")
RAW_TOKEN_PATTERN = re.compile(r"[A-Za-z]+(?:['’-][A-Za-z]+|-[A-Za-z]+)*")
CHAPTER_TITLE_TAG_PATTERN = re.compile(r"<(?:title|h1)[^>]*>(.*?)</(?:title|h1)>", flags=re.IGNORECASE | re.DOTALL)
CHAPTER_CONTENT_MIN_WORDS = 80


@dataclass(slots=True)
class PipelineResources:
    lemma_dict: dict[str, str]
    coca_rank_dict: dict[str, int]
    exam_level_dict: dict[str, set[str]]
    dictionary_words: set[str]
    valid_words: set[str]


@dataclass(slots=True)
class PipelineResult:
    total_word_count: int
    unique_word_count: int
    to_memorize_word_count: int
    coverage_95_word_count: int
    reading_level: str
    reading_label: str
    reading_color: str
    reading_message: str
    all_words_rows: list[dict[str, object]]
    to_memorize_rows: list[dict[str, object]]
    coverage_95_rows: list[dict[str, object]]


@dataclass(slots=True)
class ChapterText:
    chapter_index: int
    chapter_title: str
    text: str


class AnalysisPipeline:
    """Clean, normalize, filter, and rank book vocabulary for learning output."""

    def run(
        self,
        book_path: Path,
        file_type: str,
        known_words_mode: KnownWordsMode,
        known_words_value: str,
        user_known_words: set[str] | None = None,
    ) -> PipelineResult:
        raw_text = self.extract_book_text(book_path=book_path, file_type=file_type)
        resources = self.load_resources()
        return self.run_for_text(
            raw_text=raw_text,
            known_words_mode=known_words_mode,
            known_words_value=known_words_value,
            user_known_words=user_known_words,
            resources=resources,
        )

    def run_for_text(
        self,
        raw_text: str,
        known_words_mode: KnownWordsMode,
        known_words_value: str,
        user_known_words: set[str] | None = None,
        resources: PipelineResources | None = None,
    ) -> PipelineResult:
        resources = resources or self.load_resources()
        user_known_words = user_known_words or set()

        word_freq, total_word_count = self.count_cleaned_tokens(
            self.extract_words(raw_text),
            dictionary_words=resources.dictionary_words,
            coca_rank_dict=resources.coca_rank_dict,
            lemma_dict=resources.lemma_dict,
            valid_words=resources.valid_words,
        )
        ranked_words = word_freq.most_common()

        all_rows: list[dict[str, object]] = []
        known_word_cutoff = self.parse_coca_threshold(known_words_mode, known_words_value)
        allowed_exam_tags = self.get_allowed_exam_tags(known_words_mode, known_words_value)

        for index, (word, frequency) in enumerate(ranked_words, start=1):
            lemma = resources.lemma_dict.get(word, "")
            coca_rank = resources.coca_rank_dict.get(word)
            if coca_rank is None and lemma:
                coca_rank = resources.coca_rank_dict.get(lemma)
            exam_tags = resources.exam_level_dict.get(word) or (
                resources.exam_level_dict.get(lemma) if lemma else None
            )
            is_known = (
                (known_word_cutoff is not None and coca_rank is not None and coca_rank <= known_word_cutoff)
                or bool(allowed_exam_tags and exam_tags and allowed_exam_tags.intersection(exam_tags))
                or word in user_known_words
                or (lemma in user_known_words if lemma else False)
            )
            all_rows.append(
                {
                    "序号": index,
                    "单词": word,
                    "书籍出现频率": frequency,
                    "COCA 排行": coca_rank or "",
                    "原型": lemma,
                    "是否已掌握": "true" if is_known else "false",
                }
            )

        to_memorize_rows = [row for row in all_rows if row["是否已掌握"] == "false"]
        coverage_95_rows = self.calculate_coverage_rows(all_rows, to_memorize_rows, total_word_count)
        reading_level, reading_label, reading_color, reading_message = self.calculate_reading_level(
            len(coverage_95_rows)
        )

        return PipelineResult(
            total_word_count=total_word_count,
            unique_word_count=len(all_rows),
            to_memorize_word_count=len(to_memorize_rows),
            coverage_95_word_count=len(coverage_95_rows),
            reading_level=reading_level,
            reading_label=reading_label,
            reading_color=reading_color,
            reading_message=reading_message,
            all_words_rows=all_rows,
            to_memorize_rows=self.resequence_rows(to_memorize_rows),
            coverage_95_rows=self.resequence_rows(coverage_95_rows),
        )

    def load_resources(self) -> PipelineResources:
        lemma_dict = load_lemma_dict()
        coca_rank_dict = load_coca_rank_dict()
        exam_level_dict = load_exam_level_dict()
        dictionary_words = load_dictionary_words()
        valid_words = self.build_valid_word_set(dictionary_words, coca_rank_dict, lemma_dict)
        return PipelineResources(
            lemma_dict=lemma_dict,
            coca_rank_dict=coca_rank_dict,
            exam_level_dict=exam_level_dict,
            dictionary_words=dictionary_words,
            valid_words=valid_words,
        )

    def extract_chapters(self, book_path: Path, file_type: str) -> list[ChapterText]:
        if file_type != "epub":
            return []

        chapters = self.extract_epub_chapters(book_path)
        if chapters:
            return chapters

        logger.info("epub_chapter_extract_empty book_path=%s", book_path)
        return []

    def extract_epub_chapters(self, book_path: Path) -> list[ChapterText]:
        try:
            from ebooklib import ITEM_DOCUMENT, epub

            book = epub.read_epub(str(book_path))
            item_by_id = {
                getattr(item, "get_id", lambda: "")(): item
                for item in book.get_items()
                if getattr(item, "media_type", "") in {"application/xhtml+xml", "text/html", "application/xml", "text/plain"}
            }
            chapters: list[ChapterText] = []

            for spine_item in book.spine:
                item_id = spine_item[0] if isinstance(spine_item, tuple) else spine_item
                item = item_by_id.get(item_id)
                if item is None or item.get_type() != ITEM_DOCUMENT:
                    continue

                content = self.decode_item_content(item.get_content())
                if not content:
                    continue

                text = self.normalize_text_content(self.remove_html_tags(content))
                if not self.is_valid_chapter_text(text):
                    continue

                chapters.append(
                    ChapterText(
                        chapter_index=len(chapters) + 1,
                        chapter_title=self.resolve_chapter_title(content, fallback_index=len(chapters) + 1),
                        text=text,
                    )
                )

            return chapters
        except Exception:
            logger.exception("epub_chapter_extract_failed book_path=%s", book_path)
            return []

    def resolve_chapter_title(self, html_content: str, fallback_index: int) -> str:
        match = CHAPTER_TITLE_TAG_PATTERN.search(html_content)
        if match:
            title = self.normalize_text_content(self.remove_html_tags(match.group(1)))
            if title:
                return title[:255]
        return f"Chapter {fallback_index}"

    def is_valid_chapter_text(self, text: str) -> bool:
        if not text.strip():
            return False
        token_count = sum(1 for _ in self.extract_words(text))
        return token_count >= CHAPTER_CONTENT_MIN_WORDS

    def parse_coca_threshold(self, known_words_mode: KnownWordsMode, known_words_value: str) -> int | None:
        if known_words_mode != KnownWordsMode.coca_rank:
            return None

        threshold = int(known_words_value)
        if threshold < 1000 or threshold > 15000:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="known_words_value must be within 1000..15000 for coca_rank mode",
            )
        return threshold

    def get_allowed_exam_tags(self, known_words_mode: KnownWordsMode, known_words_value: str) -> set[str]:
        if known_words_mode != KnownWordsMode.exam_level:
            return set()

        allowed_map = {
            "初中": {"小学", "初中"},
            "高中": {"小学", "初中", "高中"},
            "四级": {"小学", "初中", "高中", "四级"},
            "六级": {"小学", "初中", "高中", "四级", "六级"},
            "GRE": {"小学", "初中", "高中", "四级", "六级", "考研", "GRE"},
            "TOEFL": {"小学", "初中", "高中", "四级", "六级", "TOEFL"},
            "托福": {"小学", "初中", "高中", "四级", "六级", "TOEFL"},
        }
        allowed_tags = allowed_map.get(known_words_value)
        if allowed_tags is None:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="known_words_value must be one of 初中、高中、四级、六级、GRE、TOEFL、托福 for exam_level mode",
            )
        return allowed_tags

    def extract_book_text(self, book_path: Path, file_type: str) -> str:
        if file_type == "txt":
            return self.extract_txt_text(book_path)
        if file_type != "epub":
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"unsupported book file type: {file_type}",
            )

        all_text: list[str] = []
        chapters = self.extract_epub_chapters(book_path)
        if chapters:
            all_text = [chapter.text for chapter in chapters]
        else:
            all_text = self.extract_book_text_from_zip(book_path)

        if not all_text:
            logger.warning("epub_extract_no_text book_path=%s", book_path)
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="unable to extract readable text from epub",
            )

        return "\n".join(all_text)

    def extract_txt_text(self, book_path: Path) -> str:
        try:
            content = book_path.read_bytes()
        except OSError as exc:
            logger.exception("txt_extract_failed book_path=%s", book_path)
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="unable to extract readable text from txt",
            ) from exc

        text = self.normalize_text_content(self.decode_item_content(content))
        if text.strip():
            return text

        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="unable to extract readable text from txt",
        )

    def extract_book_text_from_zip(self, book_path: Path) -> list[str]:
        try:
            with ZipFile(book_path) as archive:
                candidate_names = [name for name in archive.namelist() if self.is_candidate_text_item(name)]
                texts: list[str] = []
                for name in sorted(candidate_names):
                    content = self.decode_item_content(archive.read(name))
                    if not content:
                        continue
                    text = self.normalize_text_content(self.remove_html_tags(content))
                    if text.strip():
                        texts.append(text)
                return texts
        except (BadZipFile, KeyError, OSError):
            logger.exception("epub_extract_fallback_failed book_path=%s", book_path)
            return []

    def is_candidate_text_item(self, name: str) -> bool:
        lower_name = name.lower()
        if lower_name.endswith((".opf", ".ncx", ".jpg", ".jpeg", ".png", ".gif", ".svg", ".css", ".ttf", ".otf")):
            return False
        if lower_name.startswith("meta-inf/"):
            return False
        if "/styles/" in lower_name or "/fonts/" in lower_name or "/images/" in lower_name:
            return False
        return lower_name.endswith((".xhtml", ".html", ".htm", ".xml", ".txt"))

    def decode_item_content(self, content: bytes) -> str:
        if not content:
            return ""

        for encoding in ("utf-8", "utf-16", "utf-16-le", "utf-16-be", "gb18030", "big5", "latin-1"):
            try:
                return content.decode(encoding)
            except UnicodeDecodeError:
                continue
        return content.decode("utf-8", errors="ignore")

    def remove_html_tags(self, html_text: str) -> str:
        text = unescape(html_text)
        text = re.sub(r"<script[^>]*>.*?</script>", "", text, flags=re.DOTALL | re.IGNORECASE)
        text = re.sub(r"<style[^>]*>.*?</style>", "", text, flags=re.DOTALL | re.IGNORECASE)
        return re.sub(r"<[^>]+>", " ", text)

    def normalize_text_content(self, text: str) -> str:
        return re.sub(r"\s+", " ", text).strip()

    def extract_words(self, text: str) -> Iterator[str]:
        for match in RAW_TOKEN_PATTERN.finditer(text):
            yield match.group(0)

    def count_cleaned_tokens(
        self,
        tokens: Iterable[str],
        dictionary_words: set[str],
        coca_rank_dict: dict[str, int],
        lemma_dict: dict[str, str],
        valid_words: set[str],
    ) -> tuple[Counter[str], int]:
        word_freq: Counter[str] = Counter()
        total_word_count = 0

        for token in tokens:
            for candidate in self.split_raw_token(token):
                normalized = self.normalize_token(candidate)
                if not normalized:
                    continue

                if self.should_drop_token(
                    normalized,
                    dictionary_words=dictionary_words,
                    coca_rank_dict=coca_rank_dict,
                    lemma_dict=lemma_dict,
                    valid_words=valid_words,
                ):
                    continue

                word_freq[normalized] += 1
                total_word_count += 1

        return word_freq, total_word_count

    def split_raw_token(self, token: str) -> list[str]:
        normalized = token.replace("’", "'").replace("–", "-")
        if "-" not in normalized:
            return [normalized]
        return [part for part in normalized.split("-") if part]

    def normalize_token(self, token: str) -> str:
        normalized = token.strip().lower().replace("’", "'")
        normalized = re.sub(r"^[^a-z]+|[^a-z]+$", "", normalized)
        normalized = re.sub(r"[^a-z']", "", normalized)
        if not normalized:
            return ""
        if "'" in normalized:
            return ""
        if not VALID_TOKEN_PATTERN.fullmatch(normalized):
            return ""
        return normalized

    def should_drop_token(
        self,
        token: str,
        dictionary_words: set[str],
        coca_rank_dict: dict[str, int],
        lemma_dict: dict[str, str],
        valid_words: set[str],
    ) -> bool:
        base_form = token.replace("'", "")
        lemma = lemma_dict.get(token) or lemma_dict.get(base_form)

        if token in ABBREVIATION_BLOCKLIST or base_form in ABBREVIATION_BLOCKLIST:
            return True

        if len(base_form) < 3:
            return not self.is_short_word_allowed(token, base_form, dictionary_words, coca_rank_dict, lemma_dict)

        if token in valid_words:
            return False

        if base_form in valid_words:
            return False

        if lemma and lemma in valid_words:
            return False

        if self.looks_like_ocr_noise(base_form):
            return True

        return True

    def is_short_word_allowed(
        self,
        token: str,
        base_form: str,
        dictionary_words: set[str],
        coca_rank_dict: dict[str, int],
        lemma_dict: dict[str, str],
    ) -> bool:
        if token in SHORT_WORD_BLOCKLIST or base_form in SHORT_WORD_BLOCKLIST:
            return False
        if token in SHORT_WORD_WHITELIST or base_form in SHORT_WORD_WHITELIST:
            return True
        if token in dictionary_words or base_form in dictionary_words:
            return True
        if token in coca_rank_dict or base_form in coca_rank_dict:
            return True
        lemma = lemma_dict.get(token) or lemma_dict.get(base_form)
        return bool(lemma and (lemma in dictionary_words or lemma in coca_rank_dict))

    def looks_like_ocr_noise(self, token: str) -> bool:
        if not token:
            return True
        if re.search(r"(.)\1\1", token):
            return True
        if len(token) >= 4 and re.search(r"[bcdfghjklmnpqrstvwxyz]{4,}", token):
            return True
        if not re.search(r"[aeiouy]", token):
            return True
        return False

    def build_valid_word_set(
        self,
        dictionary_words: set[str],
        coca_rank_dict: dict[str, int],
        lemma_dict: dict[str, str],
    ) -> set[str]:
        valid_words = set(dictionary_words)
        valid_words.update(coca_rank_dict.keys())
        valid_words.update(lemma_dict.keys())
        valid_words.update(lemma_dict.values())
        valid_words.update(SHORT_WORD_WHITELIST)
        return valid_words

    def calculate_coverage_rows(
        self,
        all_rows: list[dict[str, object]],
        to_memorize_rows: list[dict[str, object]],
        total_word_count: int,
    ) -> list[dict[str, object]]:
        if total_word_count <= 0:
            return []

        known_coverage_count = sum(
            int(row["书籍出现频率"])
            for row in all_rows
            if str(row["是否已掌握"]).lower() == "true"
        )
        if known_coverage_count / total_word_count * 100 >= 95:
            return []

        cumulative = known_coverage_count
        coverage_rows: list[dict[str, object]] = []
        for row in to_memorize_rows:
            coverage_rows.append(row)
            cumulative += int(row["书籍出现频率"])
            coverage = cumulative / total_word_count * 100 if total_word_count else 0
            if coverage >= 95:
                break
        return coverage_rows

    def resequence_rows(self, rows: list[dict[str, object]]) -> list[dict[str, object]]:
        resequenced = []
        for index, row in enumerate(rows, start=1):
            updated = dict(row)
            updated["序号"] = index
            resequenced.append(updated)
        return resequenced

    def calculate_reading_level(self, coverage_95_word_count: int) -> tuple[str, str, str, str]:
        if coverage_95_word_count <= 200:
            return ("level_1", "强推荐阅读", "green", "非常适合阅读，几乎无压力，可自然习得。")
        if coverage_95_word_count < 800:
            return ("level_2", "推荐阅读 + 学习", "yellow", "可以阅读，但建议先学习核心词表。")
        return ("level_3", "不推荐直接阅读", "red", "当前不建议直接开始阅读，应先积累基础词汇。")

    def write_csv(self, rows: list[dict[str, object]], output_path: Path) -> None:
        fieldnames = ["序号", "单词", "书籍出现频率", "COCA 排行", "原型", "是否已掌握"]
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with output_path.open("w", newline="", encoding="utf-8-sig") as file:
            writer = csv.DictWriter(file, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)

    def write_anki_csv(self, rows: list[dict[str, object]], output_path: Path) -> None:
        fieldnames = ["单词", "排行", "tag"]
        anki_rows = [
            {
                "单词": row["单词"],
                "排行": row["COCA 排行"],
                "tag": "tag",
            }
            for row in rows
            if row["COCA 排行"] not in ("", None)
        ]
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with output_path.open("w", newline="", encoding="utf-8-sig") as file:
            writer = csv.DictWriter(file, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(anki_rows)

    def build_result_response(
        self,
        result_id: int,
        job_id: int,
        book_id: int,
        file_type: str,
        title: str | None,
        original_filename: str,
        known_words_mode: KnownWordsMode,
        known_words_value: str,
        created_at: str,
        total_word_count: int,
        unique_word_count: int,
        to_memorize_word_count: int,
        coverage_95_word_count: int,
        reading_level: str,
        reading_label: str,
        reading_color: str,
        reading_message: str,
        chapter_analysis_supported: bool = False,
    ) -> AnalysisResultResponse:
        return AnalysisResultResponse(
            result_id=result_id,
            job_id=job_id,
            book=BookSummary(
                book_id=book_id,
                file_type=file_type,
                title=title,
                original_filename=original_filename,
            ),
            summary=AnalysisSummary(
                total_word_count=total_word_count,
                unique_word_count=unique_word_count,
                to_memorize_word_count=to_memorize_word_count,
                coverage_95_word_count=coverage_95_word_count,
            ),
            reading_advice=ReadingAdvice(
                level=reading_level,
                label=reading_label,
                color=reading_color,
                message=reading_message,
            ),
            known_words_mode=known_words_mode,
            known_words_value=known_words_value,
            created_at=created_at,
            downloads=ResultDownloads(
                all_words=f"/api/v1/analysis/results/{result_id}/downloads/all_words",
                to_memorize=f"/api/v1/analysis/results/{result_id}/downloads/to_memorize",
                coverage_95=f"/api/v1/analysis/results/{result_id}/downloads/coverage_95",
                coverage_95_anki=f"/api/v1/analysis/results/{result_id}/downloads/coverage_95_anki",
            ),
            chapter_analysis_supported=chapter_analysis_supported,
        )

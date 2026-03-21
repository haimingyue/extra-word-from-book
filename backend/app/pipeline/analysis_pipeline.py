from __future__ import annotations

import csv
import logging
import re
from collections import Counter
from dataclasses import dataclass
from html import unescape
from pathlib import Path
from zipfile import BadZipFile, ZipFile

from fastapi import HTTPException, status

from app.pipeline.resources import load_coca_rank_dict, load_dictionary_words, load_lemma_dict
from app.schemas.analysis import AnalysisResultResponse, AnalysisSummary, BookSummary, ReadingAdvice, ResultDownloads


logger = logging.getLogger(__name__)


ABBREVIATION_BLOCKLIST = {"isbn", "jr", "pp"}
SHORT_WORD_BLOCKLIST = {"b", "c", "d", "er", "h", "j", "k", "m", "mr", "o", "p", "t"}
SHORT_WORD_WHITELIST = {"a", "am", "an", "as", "at", "be", "by", "do", "go", "he", "i", "if", "in", "is", "it", "me", "my", "no", "of", "on", "or", "ox", "so", "to", "up", "us", "we"}
VALID_TOKEN_PATTERN = re.compile(r"[a-z]+(?:'[a-z]+)?")
RAW_TOKEN_PATTERN = re.compile(r"[A-Za-z]+(?:['’-][A-Za-z]+|-[A-Za-z]+)*")


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


class AnalysisPipeline:
    """Clean, normalize, filter, and rank book vocabulary for learning output."""

    def run(self, book_path: Path, known_words_level: int, user_known_words: set[str] | None = None) -> PipelineResult:
        raw_text = self.extract_book_text(book_path)
        raw_tokens = self.extract_words(raw_text)

        lemma_dict = load_lemma_dict()
        coca_rank_dict = load_coca_rank_dict()
        dictionary_words = load_dictionary_words()
        valid_words = self.build_valid_word_set(dictionary_words, coca_rank_dict, lemma_dict)

        words = self.clean_and_filter_tokens(
            raw_tokens,
            dictionary_words=dictionary_words,
            coca_rank_dict=coca_rank_dict,
            lemma_dict=lemma_dict,
            valid_words=valid_words,
        )
        word_freq = Counter(words)
        total_word_count = len(words)
        ranked_words = word_freq.most_common()
        user_known_words = user_known_words or set()

        all_rows = []
        known_word_cutoff = known_words_level

        for index, (word, frequency) in enumerate(ranked_words, start=1):
            lemma = lemma_dict.get(word, "")
            coca_rank = coca_rank_dict.get(word)
            if coca_rank is None and lemma:
                coca_rank = coca_rank_dict.get(lemma)
            is_known = (
                (coca_rank is not None and coca_rank <= known_word_cutoff)
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

    def extract_book_text(self, book_path: Path) -> str:
        from ebooklib import epub

        all_text: list[str] = []
        try:
            book = epub.read_epub(str(book_path))
            for item in book.get_items():
                if item.media_type not in ["application/xhtml+xml", "text/html", "application/xml", "text/plain"]:
                    continue

                content = self.decode_item_content(item.get_content())
                if not content:
                    continue

                text = self.remove_html_tags(content)
                if text.strip():
                    all_text.append(text)
        except Exception:
            logger.exception("epub_extract_primary_failed book_path=%s", book_path)
            all_text = []

        if not all_text:
            all_text = self.extract_book_text_from_zip(book_path)

        if not all_text:
            logger.warning("epub_extract_no_text book_path=%s", book_path)
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="unable to extract readable text from epub",
            )

        return "\n".join(all_text)

    def extract_book_text_from_zip(self, book_path: Path) -> list[str]:
        try:
            with ZipFile(book_path) as archive:
                candidate_names = [
                    name
                    for name in archive.namelist()
                    if self.is_candidate_text_item(name)
                ]
                texts: list[str] = []
                for name in sorted(candidate_names):
                    content = self.decode_item_content(archive.read(name))
                    if not content:
                        continue
                    text = self.remove_html_tags(content)
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

    def extract_words(self, text: str) -> list[str]:
        return RAW_TOKEN_PATTERN.findall(text)

    def clean_and_filter_tokens(
        self,
        tokens: list[str],
        dictionary_words: set[str],
        coca_rank_dict: dict[str, int],
        lemma_dict: dict[str, str],
        valid_words: set[str],
    ) -> list[str]:
        cleaned: list[str] = []
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

                cleaned.append(normalized)
        return cleaned

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

    def build_result_response(
        self,
        result_id: int,
        job_id: int,
        book_id: int,
        title: str | None,
        original_filename: str,
        known_words_level: int,
        created_at: str,
        total_word_count: int,
        unique_word_count: int,
        to_memorize_word_count: int,
        coverage_95_word_count: int,
        reading_level: str,
        reading_label: str,
        reading_color: str,
        reading_message: str,
    ) -> AnalysisResultResponse:
        return AnalysisResultResponse(
            result_id=result_id,
            job_id=job_id,
            book=BookSummary(
                book_id=book_id,
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
            known_words_level=known_words_level,
            created_at=created_at,
            downloads=ResultDownloads(
                all_words=f"/api/v1/analysis/results/{result_id}/downloads/all_words",
                to_memorize=f"/api/v1/analysis/results/{result_id}/downloads/to_memorize",
                coverage_95=f"/api/v1/analysis/results/{result_id}/downloads/coverage_95",
            ),
        )

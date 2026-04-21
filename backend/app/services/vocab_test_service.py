from __future__ import annotations

import csv
import math
import random
import re
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from functools import lru_cache
from pathlib import Path
from uuid import uuid4

from fastapi import HTTPException, status

from app.core.config import get_settings
from app.schemas.vocab_test import (
    DurationMode,
    TestResponseValue,
    VocabularyTestAnswer,
    VocabularyTestBandScore,
    VocabularyTestProgressResponse,
    VocabularyTestQuestion,
    VocabularyTestResultResponse,
)


QUESTION_WORD_RE = re.compile(r"^[A-Za-z]+$")
POS_PREFIX_RE = re.compile(r"^(?:[a-z]{1,5}\.)+\s*")
INLINE_POS_RE = re.compile(r"(?<!^)(?=(?:adj|adv|art|aux|conj|det|int|n|num|prep|pron|v|vi|vt)\.)")
WHITESPACE_RE = re.compile(r"\s+")
STOP_WORDS = {
    "a",
    "an",
    "and",
    "are",
    "as",
    "at",
    "be",
    "by",
    "for",
    "from",
    "had",
    "has",
    "have",
    "he",
    "her",
    "him",
    "his",
    "i",
    "in",
    "is",
    "it",
    "its",
    "me",
    "of",
    "on",
    "or",
    "our",
    "she",
    "that",
    "the",
    "their",
    "them",
    "they",
    "this",
    "to",
    "us",
    "we",
    "were",
    "with",
    "you",
    "your",
}
BANDS = list(range(1000, 15001, 1000))
STAGE_LABELS = {
    1: "全局粗定位",
    2: "边界加测",
    3: "最终确认",
}
CONFIDENCE_LABELS = (
    (0.82, "高"),
    (0.64, "中"),
    (0.0, "低"),
)
DURATION_SETTINGS = {
    DurationMode.quick: {
        "coarse_bands": [1000, 3000, 5000, 7000, 9000, 11000, 13000, 15000],
        "coarse_count": 3,
        "focus_window": 4,
        "focus_count": 5,
        "confirm_window": 3,
        "confirm_count": 4,
        "minimum_question_target": 44,
        "maximum_question_target": 56,
        "allow_stage_two_stop": True,
    },
    DurationMode.standard: {
        "coarse_bands": [1000, 3000, 5000, 7000, 9000, 11000, 13000, 15000],
        "coarse_count": 4,
        "focus_window": 4,
        "focus_count": 12,
        "confirm_window": 3,
        "confirm_count": 6,
        "minimum_question_target": 80,
        "maximum_question_target": 98,
        "allow_stage_two_stop": True,
    },
    DurationMode.deep: {
        "coarse_bands": [1000, 2000, 4000, 6000, 8000, 10000, 12000, 14000, 15000],
        "coarse_count": 5,
        "focus_window": 4,
        "focus_count": 20,
        "confirm_window": 3,
        "confirm_count": 10,
        "minimum_question_target": 125,
        "maximum_question_target": 155,
        "allow_stage_two_stop": False,
    },
}


@dataclass(frozen=True)
class BankWord:
    word: str
    rank: int
    band: int
    lemma: str
    meaning: str
    quality_score: float


@dataclass
class SessionQuestion:
    question_id: str
    bank_word: BankWord


@dataclass
class TestSession:
    session_id: str
    duration_mode: DurationMode
    created_at: datetime
    expires_at: datetime
    minimum_question_target: int
    current_question_count: int = 0
    stop_allowed: bool = False
    stage_number: int = 1
    current_questions: list[SessionQuestion] = field(default_factory=list)
    answered_questions: dict[str, SessionQuestion] = field(default_factory=dict)
    answers: dict[str, TestResponseValue] = field(default_factory=dict)
    used_words: set[str] = field(default_factory=set)
    candidate_band: int | None = None
    question_counter: int = 0


def _now_utc() -> datetime:
    return datetime.now(UTC)


def _build_window(center_band: int, size: int) -> list[int]:
    center_index = BANDS.index(center_band)
    if size % 2 == 0:
        start_index = center_index - (size // 2 - 1)
    else:
        start_index = center_index - size // 2
    start_index = max(0, min(start_index, len(BANDS) - size))
    return BANDS[start_index : start_index + size]


class VocabularyTestService:
    def __init__(self) -> None:
        self._sessions: dict[str, TestSession] = {}
        self._session_ttl = timedelta(hours=2)

    def create_session(self, duration_mode: DurationMode) -> VocabularyTestProgressResponse:
        self._cleanup_expired_sessions()
        session_id = uuid4().hex
        settings = DURATION_SETTINGS[duration_mode]
        session = TestSession(
            session_id=session_id,
            duration_mode=duration_mode,
            created_at=_now_utc(),
            expires_at=_now_utc() + self._session_ttl,
            minimum_question_target=int(settings["minimum_question_target"]),
        )
        session.current_questions = self._build_stage_questions(session)
        self._sessions[session_id] = session
        return self._build_progress_response(session)

    def submit_answers(self, session_id: str, answers: list[VocabularyTestAnswer]) -> VocabularyTestProgressResponse:
        self._cleanup_expired_sessions()
        session = self._sessions.get(session_id)
        if session is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="test session not found or expired")

        expected_ids = {question.question_id for question in session.current_questions}
        if not expected_ids:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="test session is already completed")

        provided_ids = [answer.question_id for answer in answers]
        if not answers:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="answers cannot be empty")
        if len(provided_ids) != len(set(provided_ids)):
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="duplicate question ids found")
        if set(provided_ids) != expected_ids:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="answers must match current stage questions")

        current_by_id = {question.question_id: question for question in session.current_questions}
        for answer in answers:
            question = current_by_id[answer.question_id]
            session.answers[answer.question_id] = answer.response
            session.answered_questions[answer.question_id] = question
        session.current_question_count = len(session.answers)
        session.current_questions = []
        session.stop_allowed = self._can_stop(session)

        if session.stop_allowed:
            result = self._build_result(session)
            return VocabularyTestProgressResponse(
                session_id=session.session_id,
                completed=True,
                stage_number=session.stage_number,
                stage_label="结果",
                questions=[],
                result=result,
            )

        session.stage_number += 1
        session.current_questions = self._build_stage_questions(session)
        if not session.current_questions:
            result = self._build_result(session)
            return VocabularyTestProgressResponse(
                session_id=session.session_id,
                completed=True,
                stage_number=max(session.stage_number - 1, 1),
                stage_label="结果",
                questions=[],
                result=result,
            )
        return self._build_progress_response(session)

    def _build_progress_response(self, session: TestSession) -> VocabularyTestProgressResponse:
        return VocabularyTestProgressResponse(
            session_id=session.session_id,
            completed=False,
            stage_number=session.stage_number,
            stage_label=STAGE_LABELS.get(session.stage_number, "测试中"),
            questions=[
                VocabularyTestQuestion(
                    question_id=question.question_id,
                    word=question.bank_word.word,
                    meaning=question.bank_word.meaning,
                    coca_rank=question.bank_word.rank,
                    coca_band=question.bank_word.band,
                )
                for question in session.current_questions
            ],
        )

    def _build_stage_questions(self, session: TestSession) -> list[SessionQuestion]:
        settings = DURATION_SETTINGS[session.duration_mode]
        if session.stage_number == 1:
            target_bands = list(settings["coarse_bands"])
            count_per_band = int(settings["coarse_count"])
        elif session.stage_number == 2:
            target_bands = self._focus_bands(session, int(settings["focus_window"]))
            count_per_band = int(settings["focus_count"])
        else:
            target_bands = self._confirmation_bands(session, int(settings["confirm_window"]))
            count_per_band = int(settings["confirm_count"])

        questions: list[SessionQuestion] = []
        for band in target_bands:
            questions.extend(self._draw_questions(session, band, count_per_band))
        return questions

    def _draw_questions(self, session: TestSession, band: int, count: int) -> list[SessionQuestion]:
        bank = load_test_word_bank()
        candidates = [word for word in bank.get(band, []) if word.word not in session.used_words]
        if not candidates:
            return []

        rng = random.Random(f"{session.session_id}:{session.stage_number}:{band}")
        rng.shuffle(candidates)
        selected = candidates[:count]
        questions: list[SessionQuestion] = []
        for item in selected:
            session.question_counter += 1
            session.used_words.add(item.word)
            questions.append(SessionQuestion(question_id=f"q{session.question_counter}", bank_word=item))
        return questions

    def _focus_bands(self, session: TestSession, window_size: int) -> list[int]:
        candidate = self._estimate_candidate_band(session)
        session.candidate_band = candidate
        return _build_window(candidate, window_size)

    def _confirmation_bands(self, session: TestSession, window_size: int) -> list[int]:
        candidate = session.candidate_band or self._estimate_candidate_band(session)
        return _build_window(candidate, window_size)

    def _can_stop(self, session: TestSession) -> bool:
        settings = DURATION_SETTINGS[session.duration_mode]
        if session.current_question_count < session.minimum_question_target:
            return False
        if session.stage_number == 1:
            return False
        if session.stage_number == 2 and not bool(settings["allow_stage_two_stop"]):
            return False
        if session.stage_number >= 3:
            return True
        return self._boundary_is_clear(session)

    def _boundary_is_clear(self, session: TestSession) -> bool:
        band_scores = self._smoothed_band_scores(session)
        candidate = self._estimate_candidate_band(session, band_scores)
        current_score = band_scores.get(candidate, 0.0)
        next_score = band_scores.get(min(candidate + 1000, 15000), current_score)
        previous_score = band_scores.get(max(candidate - 1000, 1000), current_score)
        boundary_gap = max(abs(current_score - next_score), abs(previous_score - current_score))
        uncertainty_gap = abs(current_score - 0.58)
        return boundary_gap >= 0.16 and uncertainty_gap >= 0.1 and self._unsure_ratio(session) <= 0.22

    def _estimate_candidate_band(self, session: TestSession, band_scores: dict[int, float] | None = None) -> int:
        scores = band_scores or self._smoothed_band_scores(session)
        threshold = 0.58
        candidate = 1000
        for band in BANDS:
            if scores.get(band, 0.0) >= threshold:
                candidate = band
        return candidate

    def _smoothed_band_scores(self, session: TestSession) -> dict[int, float]:
        raw_scores = self._raw_band_scores(session)
        observed_bands = [band for band in BANDS if raw_scores[band]["count"] > 0]
        if not observed_bands:
            return {band: 0.0 for band in BANDS}

        interpolated: list[float] = []
        for band in BANDS:
            if raw_scores[band]["count"] > 0:
                interpolated.append(float(raw_scores[band]["score"]))
                continue
            left = next((candidate for candidate in reversed(BANDS[: BANDS.index(band)]) if raw_scores[candidate]["count"] > 0), None)
            right = next((candidate for candidate in BANDS[BANDS.index(band) + 1 :] if raw_scores[candidate]["count"] > 0), None)
            if left is None and right is None:
                interpolated.append(0.0)
            elif left is None:
                interpolated.append(float(raw_scores[right]["score"]))
            elif right is None:
                interpolated.append(float(raw_scores[left]["score"]))
            else:
                left_score = float(raw_scores[left]["score"])
                right_score = float(raw_scores[right]["score"])
                ratio = (band - left) / (right - left)
                interpolated.append(left_score + (right_score - left_score) * ratio)

        smoothed = self._pava_decreasing(interpolated)
        return {band: max(0.0, min(1.0, round(score, 4))) for band, score in zip(BANDS, smoothed, strict=True)}

    def _raw_band_scores(self, session: TestSession) -> dict[int, dict[str, float]]:
        weighted_totals: dict[int, float] = defaultdict(float)
        weight_sums: dict[int, float] = defaultdict(float)
        counts: dict[int, int] = defaultdict(int)

        for question_id, response in session.answers.items():
            question = session.answered_questions[question_id]
            answer_weight = self._response_weight(response)
            quality_weight = question.bank_word.quality_score
            weighted_totals[question.bank_word.band] += answer_weight * quality_weight
            weight_sums[question.bank_word.band] += quality_weight
            counts[question.bank_word.band] += 1

        band_scores: dict[int, dict[str, float]] = {}
        for band in BANDS:
            total_weight = weight_sums.get(band, 0.0)
            band_scores[band] = {
                "count": counts.get(band, 0),
                "score": weighted_totals[band] / total_weight if total_weight else 0.0,
            }
        return band_scores

    def _response_weight(self, response: TestResponseValue) -> float:
        if response == TestResponseValue.know:
            return 1.0
        if response == TestResponseValue.unsure:
            return 0.35
        return 0.0

    def _pava_decreasing(self, values: list[float]) -> list[float]:
        blocks: list[dict[str, float | int]] = []
        for value in values:
            blocks.append({"sum": value, "count": 1})
            while len(blocks) >= 2:
                right = blocks[-1]
                left = blocks[-2]
                left_avg = float(left["sum"]) / int(left["count"])
                right_avg = float(right["sum"]) / int(right["count"])
                if left_avg >= right_avg:
                    break
                merged = {
                    "sum": float(left["sum"]) + float(right["sum"]),
                    "count": int(left["count"]) + int(right["count"]),
                }
                blocks[-2:] = [merged]

        smoothed: list[float] = []
        for block in blocks:
            average = float(block["sum"]) / int(block["count"])
            smoothed.extend([average] * int(block["count"]))
        return smoothed

    def _build_result(self, session: TestSession) -> VocabularyTestResultResponse:
        scores = self._smoothed_band_scores(session)
        recommended_band = self._estimate_candidate_band(session, scores)
        estimated_size = self._estimate_continuous_size(scores, recommended_band)
        confidence = self._estimate_confidence(session, scores, recommended_band)
        confidence_label = next(label for threshold, label in CONFIDENCE_LABELS if confidence >= threshold)
        band_scores = self._result_band_scores(session, scores, recommended_band)
        answered_count = len(session.answers)
        unsure_count = sum(1 for value in session.answers.values() if value == TestResponseValue.unsure)
        result = VocabularyTestResultResponse(
            recommended_coca_rank=recommended_band,
            recommended_coca_label=f"COCA {recommended_band}",
            estimated_vocabulary_size=estimated_size,
            confidence=round(confidence, 2),
            confidence_label=confidence_label,
            answered_count=answered_count,
            unsure_count=unsure_count,
            band_scores=band_scores,
            summary=self._build_summary(recommended_band, estimated_size, confidence_label, unsure_count, answered_count),
        )
        self._sessions.pop(session.session_id, None)
        return result

    def _estimate_continuous_size(self, scores: dict[int, float], recommended_band: int) -> int:
        current_score = scores.get(recommended_band, 0.58)
        if recommended_band >= 15000:
            return 15000
        next_band = recommended_band + 1000
        next_score = scores.get(next_band, current_score)
        previous_band = max(1000, recommended_band - 1000)
        previous_score = scores.get(previous_band, current_score)

        if current_score <= 0.58:
            denominator = max(previous_score - current_score, 0.08)
            ratio = max(0.0, min(1.0, (previous_score - 0.58) / denominator))
            estimate = previous_band + int(ratio * 1000)
            return max(1000, min(15000, estimate))

        denominator = max(current_score - next_score, 0.08)
        ratio = max(0.0, min(1.0, (current_score - 0.58) / denominator))
        estimate = recommended_band + int((1 - ratio) * 1000)
        return max(recommended_band, min(15000, estimate))

    def _estimate_confidence(self, session: TestSession, scores: dict[int, float], recommended_band: int) -> float:
        answered_count = len(session.answers)
        unsure_ratio = self._unsure_ratio(session)
        next_band = min(recommended_band + 1000, 15000)
        previous_band = max(recommended_band - 1000, 1000)
        boundary_gap = max(
            abs(scores.get(recommended_band, 0.0) - scores.get(next_band, 0.0)),
            abs(scores.get(previous_band, 0.0) - scores.get(recommended_band, 0.0)),
        )
        target_ratio = min(1.0, answered_count / max(session.minimum_question_target, 1))
        confidence = 0.44 + target_ratio * 0.26 + min(boundary_gap / 0.24, 1.0) * 0.22 - unsure_ratio * 0.2
        return max(0.0, min(0.98, confidence))

    def _result_band_scores(
        self,
        session: TestSession,
        scores: dict[int, float],
        recommended_band: int,
    ) -> list[VocabularyTestBandScore]:
        raw = self._raw_band_scores(session)
        window = [band for band in range(max(1000, recommended_band - 2000), min(15000, recommended_band + 2000) + 1, 1000)]
        return [
            VocabularyTestBandScore(
                coca_band=band,
                score=round(scores.get(band, 0.0), 2),
                answered_count=int(raw[band]["count"]),
            )
            for band in window
        ]

    def _build_summary(
        self,
        recommended_band: int,
        estimated_size: int,
        confidence_label: str,
        unsure_count: int,
        answered_count: int,
    ) -> str:
        summary = f"推荐把默认词汇基础设为 COCA {recommended_band}，当前预估词汇量约 {estimated_size} 词。"
        if unsure_count and answered_count and unsure_count / answered_count > 0.25:
            return f"{summary} 本次“不确定”回答较多，建议换一组题再测一次。"
        return f"{summary} 本次结果置信度为 {confidence_label}，可直接用于后续书籍分析。"

    def _unsure_ratio(self, session: TestSession) -> float:
        answered_count = len(session.answers)
        if answered_count == 0:
            return 0.0
        unsure_count = sum(1 for value in session.answers.values() if value == TestResponseValue.unsure)
        return unsure_count / answered_count

    def _cleanup_expired_sessions(self) -> None:
        now = _now_utc()
        expired_ids = [session_id for session_id, session in self._sessions.items() if session.expires_at <= now]
        for session_id in expired_ids:
            self._sessions.pop(session_id, None)


def _clean_meaning(raw_meaning: str) -> str:
    normalized = WHITESPACE_RE.sub(" ", raw_meaning).strip()
    normalized = INLINE_POS_RE.sub("\n", normalized)
    normalized = normalized.replace("原型:", "\n原型:")
    normalized = normalized.replace("原型：", "\n原型：")
    parts = [
        part.strip(" ,，。;；")
        for part in re.split(r"[\n；;]", normalized)
        if part.strip(" ,，。;；")
    ]
    cleaned = "\n".join(parts[:2])
    cleaned = cleaned[:48].rstrip(" ,，。;；\n")
    return cleaned


def _meaning_quality_score(meaning: str) -> float:
    chinese_chars = len(re.findall(r"[\u4e00-\u9fff]", meaning))
    if chinese_chars >= 4:
        return 1.0
    if chinese_chars >= 2:
        return 0.88
    return 0.75


@lru_cache
def load_test_word_bank() -> dict[int, list[BankWord]]:
    settings = get_settings()
    buckets: dict[int, list[BankWord]] = {band: [] for band in BANDS}
    seen_lemmas: dict[int, set[str]] = {band: set() for band in BANDS}

    with Path(settings.coca_words_file_path).open("r", encoding="utf-8-sig") as file:
        reader = csv.DictReader(file)
        for row in reader:
            word = row.get("Word", "").strip().lower()
            rank_value = row.get("COCA_Rank", "").strip()
            lemma = row.get("Lemma", "").strip().lower() or word
            meaning = _clean_meaning(row.get("Meaning", ""))
            if not rank_value or not word or not meaning:
                continue
            if not QUESTION_WORD_RE.fullmatch(word):
                continue
            if len(word) <= 3 or word in STOP_WORDS:
                continue
            rank = int(rank_value)
            band = math.ceil(rank / 1000) * 1000
            band = min(max(band, 1000), 15000)
            if lemma in seen_lemmas[band]:
                continue
            seen_lemmas[band].add(lemma)
            buckets[band].append(
                BankWord(
                    word=word,
                    rank=rank,
                    band=band,
                    lemma=lemma,
                    meaning=meaning,
                    quality_score=_meaning_quality_score(meaning),
                )
            )

    return buckets

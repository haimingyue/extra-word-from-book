from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field


class DurationMode(str, Enum):
    quick = "quick"
    standard = "standard"
    deep = "deep"


class TestResponseValue(str, Enum):
    know = "know"
    dont_know = "dont_know"
    unsure = "unsure"


class VocabularyTestSessionCreateRequest(BaseModel):
    duration_mode: DurationMode = Field(default=DurationMode.standard)


class VocabularyTestQuestion(BaseModel):
    question_id: str
    word: str
    meaning: str
    coca_rank: int
    coca_band: int


class VocabularyTestAnswer(BaseModel):
    question_id: str
    response: TestResponseValue


class VocabularyTestAnswerRequest(BaseModel):
    answers: list[VocabularyTestAnswer]


class VocabularyTestBandScore(BaseModel):
    coca_band: int
    score: float
    answered_count: int


class VocabularyTestResultResponse(BaseModel):
    recommended_coca_rank: int
    recommended_coca_label: str
    estimated_vocabulary_size: int
    confidence: float
    confidence_label: str
    answered_count: int
    unsure_count: int
    band_scores: list[VocabularyTestBandScore]
    summary: str


class VocabularyTestProgressResponse(BaseModel):
    session_id: str
    completed: bool
    stage_number: int
    stage_label: str
    questions: list[VocabularyTestQuestion]
    result: VocabularyTestResultResponse | None = None

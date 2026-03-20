from enum import Enum

from pydantic import BaseModel, Field


class DownloadType(str, Enum):
    all_words = "all_words"
    to_memorize = "to_memorize"
    coverage_95 = "coverage_95"


class AnalysisJobCreateRequest(BaseModel):
    book_id: int
    known_words_level: int = Field(ge=1000, le=15000)


class AnalysisJobResponse(BaseModel):
    job_id: int
    book_id: int
    status: str
    known_words_level: int
    error_code: str | None = None
    error_message: str | None = None
    queued_at: str
    started_at: str | None = None
    finished_at: str | None = None
    result_id: int | None = None


class BookSummary(BaseModel):
    book_id: int
    title: str | None = None
    original_filename: str


class AnalysisSummary(BaseModel):
    total_word_count: int
    unique_word_count: int
    to_memorize_word_count: int
    coverage_95_word_count: int


class ReadingAdvice(BaseModel):
    level: str
    label: str
    color: str
    message: str


class ResultDownloads(BaseModel):
    all_words: str
    to_memorize: str
    coverage_95: str


class AnalysisResultResponse(BaseModel):
    result_id: int
    job_id: int
    book: BookSummary
    summary: AnalysisSummary
    reading_advice: ReadingAdvice
    known_words_level: int
    created_at: str
    downloads: ResultDownloads


class AnalysisJobCreateResult(BaseModel):
    job: AnalysisJobResponse
    result: AnalysisResultResponse | None = None

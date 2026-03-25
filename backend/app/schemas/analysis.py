from enum import Enum

from pydantic import BaseModel, Field, model_validator


class DownloadType(str, Enum):
    all_words = "all_words"
    to_memorize = "to_memorize"
    coverage_95 = "coverage_95"


class KnownWordsMode(str, Enum):
    exam_level = "exam_level"
    coca_rank = "coca_rank"


class AnalysisJobCreateRequest(BaseModel):
    book_id: int
    known_words_mode: KnownWordsMode
    known_words_value: str = Field(min_length=1, max_length=20)

    @model_validator(mode="after")
    def validate_known_words_selection(self) -> "AnalysisJobCreateRequest":
        if self.known_words_mode == KnownWordsMode.coca_rank:
            if not self.known_words_value.isdigit():
                raise ValueError("known_words_value must be a number for coca_rank mode")
            level = int(self.known_words_value)
            if level < 1000 or level > 15000:
                raise ValueError("known_words_value must be within 1000..15000 for coca_rank mode")
            return self

        if self.known_words_value not in {"初中", "高中", "四级", "六级"}:
            raise ValueError("known_words_value must be one of 初中、高中、四级、六级 for exam_level mode")
        return self


class AnalysisJobResponse(BaseModel):
    job_id: int
    book_id: int
    status: str
    known_words_mode: KnownWordsMode
    known_words_value: str
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
    known_words_mode: KnownWordsMode
    known_words_value: str
    created_at: str
    downloads: ResultDownloads


class AnalysisJobCreateResult(BaseModel):
    job: AnalysisJobResponse
    result: AnalysisResultResponse | None = None

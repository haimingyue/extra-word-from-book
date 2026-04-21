from enum import Enum

from pydantic import AliasChoices, BaseModel, ConfigDict, Field, model_validator


class DownloadType(str, Enum):
    all_words = "all_words"
    to_memorize = "to_memorize"
    coverage_95 = "coverage_95"
    coverage_95_anki = "coverage_95_anki"


class KnownWordsMode(str, Enum):
    exam_level = "exam_level"
    coca_rank = "coca_rank"


class AnalysisJobCreateRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    book_id: int = Field(validation_alias=AliasChoices("book_id", "bookId"))
    known_words_mode: KnownWordsMode | None = Field(
        default=None,
        validation_alias=AliasChoices("known_words_mode", "knownWordsMode"),
    )
    known_words_value: str | None = Field(
        default=None,
        min_length=1,
        max_length=20,
        validation_alias=AliasChoices("known_words_value", "knownWordsValue"),
    )
    known_words_level: int | None = Field(
        default=None,
        ge=1000,
        le=15000,
        validation_alias=AliasChoices("known_words_level", "knownWordsLevel"),
    )

    @model_validator(mode="before")
    @classmethod
    def unwrap_data_envelope(cls, value: object) -> object:
        # 兼容部分客户端将请求体包装在 data 字段中的写法。
        if isinstance(value, dict):
            nested = value.get("data")
            if isinstance(nested, dict):
                return nested
        return value

    @model_validator(mode="after")
    def normalize_known_words_selection(self) -> "AnalysisJobCreateRequest":
        if self.known_words_mode is None and self.known_words_value is None and self.known_words_level is not None:
            self.known_words_mode = KnownWordsMode.coca_rank
            self.known_words_value = str(self.known_words_level)

        if self.known_words_mode is None or self.known_words_value is None:
            raise ValueError("known_words_mode and known_words_value are required")

        if self.known_words_mode == KnownWordsMode.coca_rank:
            if not self.known_words_value.isdigit():
                raise ValueError("known_words_value must be a number for coca_rank mode")
            level = int(self.known_words_value)
            if level < 1000 or level > 15000:
                raise ValueError("known_words_value must be within 1000..15000 for coca_rank mode")
            self.known_words_level = level
            return self

        if self.known_words_value not in {"初中", "高中", "四级", "六级", "GRE", "TOEFL", "托福"}:
            raise ValueError(
                "known_words_value must be one of 初中、高中、四级、六级、GRE、TOEFL、托福 for exam_level mode"
            )
        self.known_words_level = None
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
    file_type: str
    title: str | None = None
    original_filename: str


class AnalysisSummary(BaseModel):
    total_word_count: int
    unique_word_count: int
    to_memorize_word_count: int
    coverage_95_word_count: int


class DistributionBucket(BaseModel):
    key: str
    label: str
    token_count: int
    token_ratio: float


class AnalysisDistributionResponse(BaseModel):
    buckets: list[DistributionBucket]
    known_words_mode: KnownWordsMode
    known_words_value: str
    total_word_count: int


class ReadingAdvice(BaseModel):
    level: str
    label: str
    color: str
    message: str


class ResultDownloads(BaseModel):
    all_words: str
    to_memorize: str
    coverage_95: str
    coverage_95_anki: str


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

from pydantic import BaseModel


class BookUploadResponse(BaseModel):
    book_id: int
    original_filename: str
    title: str | None = None
    language: str | None = None
    is_duplicate: bool


class HistoryItem(BaseModel):
    result_id: int
    job_id: int
    book_id: int
    title: str | None = None
    original_filename: str
    status: str
    known_words_level: int
    to_memorize_word_count: int
    created_at: str


class BookHistoryResponse(BaseModel):
    items: list[HistoryItem]
    total: int
    page: int
    page_size: int


class BookHistoryDeleteResponse(BaseModel):
    result_id: int
    deleted: bool

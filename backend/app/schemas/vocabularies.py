from pydantic import BaseModel


class VocabularyListItem(BaseModel):
    vocabulary_id: int
    name: str
    is_primary: bool
    item_count: int
    created_at: str


class VocabularyListResponse(BaseModel):
    items: list[VocabularyListItem]


class VocabularyUploadResponse(BaseModel):
    vocabulary_id: int
    name: str
    imported_count: int
    deduplicated_count: int


class VocabularyItem(BaseModel):
    item_id: int
    word: str
    lemma: str | None = None


class VocabularyItemsResponse(BaseModel):
    items: list[VocabularyItem]
    total: int
    page: int
    page_size: int


class VocabularyItemCreateRequest(BaseModel):
    vocabulary_id: int | None = None
    word: str


class VocabularyItemCreateResponse(BaseModel):
    item_id: int
    created: bool


class VocabularyItemDeleteResponse(BaseModel):
    item_id: int
    deleted: bool


class VocabularyItemBatchDeleteRequest(BaseModel):
    item_ids: list[int]


class VocabularyItemBatchDeleteResponse(BaseModel):
    deleted_count: int

from fastapi import APIRouter, Depends, File, Query, UploadFile, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user_id
from app.db.session import get_db
from app.schemas.common import ApiResponse, ErrorResponse
from app.schemas.vocabularies import (
    VocabularyItemBatchDeleteRequest,
    VocabularyItemBatchDeleteResponse,
    VocabularyItemCreateRequest,
    VocabularyItemCreateResponse,
    VocabularyItemDeleteResponse,
    VocabularyItemsResponse,
    VocabularyListResponse,
    VocabularyUploadResponse,
)
from app.services.vocabulary_service import VocabularyService


router = APIRouter()
vocabulary_service = VocabularyService()


@router.get(
    "",
    response_model=ApiResponse[VocabularyListResponse],
    summary="List Vocabularies",
    description="List vocabularies that belong to the current authenticated user.",
    responses={401: {"model": ErrorResponse}},
)
def list_vocabularies(
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
) -> ApiResponse[VocabularyListResponse]:
    items = vocabulary_service.list_vocabularies(db=db, user_id=user_id)
    return ApiResponse(data=VocabularyListResponse(items=items))


@router.post(
    "/upload",
    response_model=ApiResponse[VocabularyUploadResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Upload Vocabulary TXT",
    description="Import a TXT vocabulary file for the current authenticated user.",
    responses={401: {"model": ErrorResponse}, 415: {"model": ErrorResponse}},
)
async def upload_vocabulary(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
) -> ApiResponse[VocabularyUploadResponse]:
    vocabulary_id, name, imported_count, deduplicated_count = await vocabulary_service.import_txt(
        db=db,
        user_id=user_id,
        file=file,
    )
    return ApiResponse(
        data=VocabularyUploadResponse(
            vocabulary_id=vocabulary_id,
            name=name,
            imported_count=imported_count,
            deduplicated_count=deduplicated_count,
        )
    )


@router.get(
    "/{vocabulary_id}/items",
    response_model=ApiResponse[VocabularyItemsResponse],
    summary="List Vocabulary Items",
    description="List items in a vocabulary owned by the current authenticated user.",
    responses={401: {"model": ErrorResponse}, 404: {"model": ErrorResponse}},
)
def get_vocabulary_items(
    vocabulary_id: int,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=200),
    keyword: str | None = Query(default=None),
    starts_with: str | None = Query(default=None, min_length=1, max_length=1),
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
) -> ApiResponse[VocabularyItemsResponse]:
    items, total = vocabulary_service.get_items(
        db=db,
        user_id=user_id,
        vocabulary_id=vocabulary_id,
        page=page,
        page_size=page_size,
        keyword=keyword,
        starts_with=starts_with,
    )
    return ApiResponse(
        data=VocabularyItemsResponse(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
        )
    )


@router.post(
    "/items",
    response_model=ApiResponse[VocabularyItemCreateResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Create Vocabulary Item",
    description="Add a single word to a vocabulary owned by the current authenticated user.",
    responses={401: {"model": ErrorResponse}, 404: {"model": ErrorResponse}},
)
def create_vocabulary_item(
    payload: VocabularyItemCreateRequest,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
) -> ApiResponse[VocabularyItemCreateResponse]:
    item_id, created = vocabulary_service.add_item(
        db=db,
        user_id=user_id,
        vocabulary_id=payload.vocabulary_id,
        word=payload.word,
    )
    return ApiResponse(data=VocabularyItemCreateResponse(item_id=item_id, created=created))


@router.post(
    "/items/batch-delete",
    response_model=ApiResponse[VocabularyItemBatchDeleteResponse],
    summary="Batch Delete Vocabulary Items",
    description="Delete multiple vocabulary items owned by the current authenticated user.",
    responses={401: {"model": ErrorResponse}},
)
def batch_delete_vocabulary_items(
    payload: VocabularyItemBatchDeleteRequest,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
) -> ApiResponse[VocabularyItemBatchDeleteResponse]:
    deleted_count = vocabulary_service.batch_delete_items(
        db=db,
        user_id=user_id,
        item_ids=payload.item_ids,
    )
    return ApiResponse(data=VocabularyItemBatchDeleteResponse(deleted_count=deleted_count))


@router.delete(
    "/items/{item_id}",
    response_model=ApiResponse[VocabularyItemDeleteResponse],
    summary="Delete Vocabulary Item",
    description="Delete a vocabulary item owned by the current authenticated user.",
    responses={401: {"model": ErrorResponse}},
)
def delete_vocabulary_item(
    item_id: int,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
) -> ApiResponse[VocabularyItemDeleteResponse]:
    deleted = vocabulary_service.delete_item(db=db, user_id=user_id, item_id=item_id)
    return ApiResponse(data=VocabularyItemDeleteResponse(item_id=item_id, deleted=deleted))

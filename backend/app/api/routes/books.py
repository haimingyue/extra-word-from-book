from fastapi import APIRouter, Depends, File, Form, UploadFile
from sqlalchemy.orm import Session

from app.api.deps import get_current_user_id
from app.db.session import get_db
from app.schemas.books import BookHistoryDeleteResponse, BookHistoryResponse, BookUploadResponse
from app.schemas.common import ApiResponse, ErrorResponse
from app.services.book_service import BookService


router = APIRouter()
book_service = BookService()


@router.post(
    "/upload",
    response_model=ApiResponse[BookUploadResponse],
    summary="Upload EPUB",
    description="Upload an EPUB file, validate it, and deduplicate it by file hash.",
    responses={401: {"model": ErrorResponse}, 415: {"model": ErrorResponse}},
)
async def upload_book(
    file: UploadFile = File(...),
    original_filename: str | None = Form(default=None),
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
) -> ApiResponse[BookUploadResponse]:
    result = await book_service.create_or_get_book(
        db=db,
        user_id=user_id,
        file=file,
        original_filename=original_filename,
    )
    uploaded_book = result.book
    return ApiResponse(
        data=BookUploadResponse(
            book_id=uploaded_book.id,
            original_filename=uploaded_book.original_filename,
            title=uploaded_book.title,
            language=uploaded_book.language,
            is_duplicate=result.is_duplicate,
        )
    )


@router.get(
    "/history",
    response_model=ApiResponse[BookHistoryResponse],
    summary="List Book History",
    description="List analysis history for the current authenticated user.",
    responses={401: {"model": ErrorResponse}},
)
def get_history(
    page: int = 1,
    page_size: int = 20,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
) -> ApiResponse[BookHistoryResponse]:
    items, total = book_service.get_history(db=db, user_id=user_id, page=page, page_size=page_size)
    return ApiResponse(data=BookHistoryResponse(items=items, total=total, page=page, page_size=page_size))


@router.delete(
    "/history/{result_id}",
    response_model=ApiResponse[BookHistoryDeleteResponse],
    summary="Delete Book History",
    description="Delete one analysis history record for the current authenticated user.",
    responses={401: {"model": ErrorResponse}, 404: {"model": ErrorResponse}},
)
def delete_history(
    result_id: int,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
) -> ApiResponse[BookHistoryDeleteResponse]:
    deleted = book_service.delete_history(db=db, user_id=user_id, result_id=result_id)
    return ApiResponse(data=BookHistoryDeleteResponse(result_id=result_id, deleted=deleted))

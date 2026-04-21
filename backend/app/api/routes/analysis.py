from fastapi import APIRouter, Depends, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.api.deps import get_current_user_id
from app.db.session import get_db
from app.schemas.analysis import (
    AnalysisDistributionResponse,
    AnalysisJobCreateRequest,
    AnalysisJobResponse,
    AnalysisResultResponse,
    DownloadType,
)
from app.schemas.common import ApiResponse, ErrorResponse
from app.services.analysis_service import AnalysisService


router = APIRouter()
analysis_service = AnalysisService()


@router.post(
    "/jobs",
    response_model=ApiResponse[AnalysisJobResponse],
    status_code=status.HTTP_202_ACCEPTED,
    summary="Create Analysis Job",
    description="Create and execute an analysis job for a previously uploaded book.",
    responses={401: {"model": ErrorResponse}, 404: {"model": ErrorResponse}},
)
def create_job(
    payload: AnalysisJobCreateRequest,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
) -> ApiResponse[AnalysisJobResponse]:
    job = analysis_service.create_job(
        db=db,
        user_id=user_id,
        book_id=payload.book_id,
        known_words_mode=payload.known_words_mode,
        known_words_value=payload.known_words_value,
    )
    return ApiResponse(data=job)


@router.get(
    "/jobs/{job_id}",
    response_model=ApiResponse[AnalysisJobResponse],
    summary="Get Analysis Job",
    description="Get current status and result id for a user's analysis job.",
    responses={401: {"model": ErrorResponse}, 404: {"model": ErrorResponse}},
)
def get_job(
    job_id: int,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
) -> ApiResponse[AnalysisJobResponse]:
    job = analysis_service.get_job(db=db, user_id=user_id, job_id=job_id)
    return ApiResponse(data=job)


@router.get(
    "/results/{result_id}",
    response_model=ApiResponse[AnalysisResultResponse],
    summary="Get Analysis Result",
    description="Get result summary and download links for a finished analysis.",
    responses={401: {"model": ErrorResponse}, 404: {"model": ErrorResponse}},
)
def get_result(
    result_id: int,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
) -> ApiResponse[AnalysisResultResponse]:
    result = analysis_service.get_result(db=db, user_id=user_id, result_id=result_id)
    return ApiResponse(data=result)


@router.get(
    "/results/{result_id}/distribution",
    response_model=ApiResponse[AnalysisDistributionResponse],
    summary="Get Result Distribution",
    description="Get bucketed COCA distribution data for a finished analysis result.",
    responses={401: {"model": ErrorResponse}, 404: {"model": ErrorResponse}},
)
def get_result_distribution(
    result_id: int,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
) -> ApiResponse[AnalysisDistributionResponse]:
    distribution = analysis_service.get_distribution(db=db, user_id=user_id, result_id=result_id)
    return ApiResponse(data=distribution)


@router.get(
    "/results/{result_id}/downloads/{download_type}",
    summary="Download Result CSV",
    description="Download one of the generated CSV files for an analysis result.",
    responses={401: {"model": ErrorResponse}, 404: {"model": ErrorResponse}},
)
def download_result(
    result_id: int,
    download_type: DownloadType,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
) -> FileResponse:
    download_path = analysis_service.get_download_path(
        db=db,
        user_id=user_id,
        result_id=result_id,
        download_type=download_type.value,
    )
    return FileResponse(path=download_path, media_type="text/csv", filename=f"{download_type.value}.csv")

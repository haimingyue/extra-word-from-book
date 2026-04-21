from fastapi import APIRouter

from app.schemas.common import ApiResponse
from app.schemas.vocab_test import (
    VocabularyTestAnswerRequest,
    VocabularyTestProgressResponse,
    VocabularyTestSessionCreateRequest,
)
from app.services.vocab_test_service import VocabularyTestService


router = APIRouter()
vocab_test_service = VocabularyTestService()


@router.post(
    "/sessions",
    response_model=ApiResponse[VocabularyTestProgressResponse],
    summary="Create Vocabulary Test Session",
    description="Create a new anonymous vocabulary test session and return the first stage questions.",
)
def create_session(payload: VocabularyTestSessionCreateRequest) -> ApiResponse[VocabularyTestProgressResponse]:
    progress = vocab_test_service.create_session(duration_mode=payload.duration_mode)
    return ApiResponse(data=progress)


@router.post(
    "/sessions/{session_id}/answers",
    response_model=ApiResponse[VocabularyTestProgressResponse],
    summary="Submit Vocabulary Test Answers",
    description="Submit answers for the current test stage and get the next stage or final result.",
)
def submit_answers(
    session_id: str,
    payload: VocabularyTestAnswerRequest,
) -> ApiResponse[VocabularyTestProgressResponse]:
    progress = vocab_test_service.submit_answers(session_id=session_id, answers=payload.answers)
    return ApiResponse(data=progress)

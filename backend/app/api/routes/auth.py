from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.auth import LoginRequest, RegisterRequest, TokenResponse, UserResponse
from app.schemas.common import ApiResponse, ErrorResponse
from app.services.auth_service import AuthService


router = APIRouter()
auth_service = AuthService()


@router.post(
    "/register",
    response_model=ApiResponse[UserResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Register User",
    description="Create a new user with email and password.",
    responses={409: {"model": ErrorResponse}},
)
def register(payload: RegisterRequest, db: Session = Depends(get_db)) -> ApiResponse[UserResponse]:
    user = auth_service.register(
        db=db,
        email=payload.email,
        password=payload.password,
        display_name=payload.display_name,
    )
    return ApiResponse(data=user)


@router.post(
    "/login",
    response_model=ApiResponse[TokenResponse],
    summary="Login",
    description="Authenticate with email and password and get a JWT access token.",
    responses={401: {"model": ErrorResponse}},
)
def login(payload: LoginRequest, db: Session = Depends(get_db)) -> ApiResponse[TokenResponse]:
    token = auth_service.login(
        db=db,
        email=payload.email,
        password=payload.password,
    )
    return ApiResponse(data=token)

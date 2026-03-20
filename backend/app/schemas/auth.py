from pydantic import BaseModel, EmailStr, Field


class RegisterRequest(BaseModel):
    email: EmailStr = Field(examples=["alice@example.com"])
    password: str = Field(examples=["12345678"])
    display_name: str | None = Field(default=None, examples=["alice"])


class LoginRequest(BaseModel):
    email: EmailStr = Field(examples=["alice@example.com"])
    password: str = Field(examples=["12345678"])


class UserResponse(BaseModel):
    user_id: int
    email: EmailStr
    display_name: str | None = None


class TokenResponse(BaseModel):
    access_token: str
    token_type: str
    user: UserResponse

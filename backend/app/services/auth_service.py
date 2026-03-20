from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
from datetime import UTC, datetime, timedelta

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models.user import User
from app.schemas.auth import TokenResponse, UserResponse


class AuthService:
    def __init__(self) -> None:
        self.settings = get_settings()

    def register(
        self,
        db: Session,
        email: str,
        password: str,
        display_name: str | None,
    ) -> UserResponse:
        normalized_email = email.strip().lower()
        existing = db.scalar(select(User).where(User.email == normalized_email))
        if existing is not None:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="email already registered")

        user = User(
            email=normalized_email,
            password_hash=self.hash_password(password),
            display_name=display_name,
            status="active",
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        return UserResponse(
            user_id=user.id,
            email=user.email,
            display_name=user.display_name,
        )

    def login(self, db: Session, email: str, password: str) -> TokenResponse:
        normalized_email = email.strip().lower()
        user = db.scalar(select(User).where(User.email == normalized_email))
        if user is None or not self.verify_password(password, user.password_hash):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid email or password")

        user.last_login_at = datetime.now(UTC)
        db.commit()
        db.refresh(user)

        token = self.create_access_token(
            subject=str(user.id),
            email=user.email,
        )
        return TokenResponse(
            access_token=token,
            token_type="Bearer",
            user=UserResponse(
                user_id=user.id,
                email=user.email,
                display_name=user.display_name,
            ),
        )

    def create_access_token(self, subject: str, email: str) -> str:
        now = datetime.now(UTC)
        payload = {
            "sub": subject,
            "email": email,
            "iat": int(now.timestamp()),
            "exp": int((now + timedelta(minutes=self.settings.jwt_access_token_expire_minutes)).timestamp()),
        }
        if self.settings.jwt_algorithm != "HS256":
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="unsupported jwt algorithm")

        header = {
            "alg": self.settings.jwt_algorithm,
            "typ": "JWT",
        }
        encoded_header = self._b64url_encode_json(header)
        encoded_payload = self._b64url_encode_json(payload)
        signing_input = f"{encoded_header}.{encoded_payload}"
        signature = hmac.new(
            self.settings.jwt_secret_key.encode("utf-8"),
            signing_input.encode("utf-8"),
            hashlib.sha256,
        ).digest()
        encoded_signature = self._b64url_encode(signature)
        return f"{signing_input}.{encoded_signature}"

    def decode_access_token(self, token: str) -> dict[str, str | int]:
        try:
            header_segment, payload_segment, signature_segment = token.split(".")
            signing_input = f"{header_segment}.{payload_segment}"
            expected_signature = hmac.new(
                self.settings.jwt_secret_key.encode("utf-8"),
                signing_input.encode("utf-8"),
                hashlib.sha256,
            ).digest()
            actual_signature = self._b64url_decode(signature_segment)
            if not hmac.compare_digest(actual_signature, expected_signature):
                raise ValueError("signature mismatch")

            header = self._b64url_decode_json(header_segment)
            if header.get("alg") != self.settings.jwt_algorithm:
                raise ValueError("unsupported algorithm")

            payload = self._b64url_decode_json(payload_segment)
            exp = payload.get("exp")
            if not isinstance(exp, int):
                raise ValueError("missing exp")
            if exp < int(datetime.now(UTC).timestamp()):
                raise ValueError("token expired")
        except (ValueError, json.JSONDecodeError, UnicodeDecodeError) as exc:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid or expired token") from exc
        return payload

    def hash_password(self, password: str) -> str:
        salt = os.urandom(16)
        digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 100_000)
        return f"pbkdf2_sha256${base64.b64encode(salt).decode()}${base64.b64encode(digest).decode()}"

    def verify_password(self, password: str, stored_hash: str) -> bool:
        try:
            scheme, salt_b64, digest_b64 = stored_hash.split("$", 2)
        except ValueError:
            return False
        if scheme != "pbkdf2_sha256":
            return False
        salt = base64.b64decode(salt_b64.encode())
        expected = base64.b64decode(digest_b64.encode())
        actual = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 100_000)
        return hmac.compare_digest(actual, expected)

    def _b64url_encode_json(self, value: dict[str, str | int]) -> str:
        return self._b64url_encode(
            json.dumps(value, separators=(",", ":"), ensure_ascii=True).encode("utf-8")
        )

    def _b64url_encode(self, value: bytes) -> str:
        return base64.urlsafe_b64encode(value).rstrip(b"=").decode("ascii")

    def _b64url_decode_json(self, value: str) -> dict[str, str | int]:
        return json.loads(self._b64url_decode(value).decode("utf-8"))

    def _b64url_decode(self, value: str) -> bytes:
        padding = "=" * (-len(value) % 4)
        return base64.urlsafe_b64decode((value + padding).encode("ascii"))

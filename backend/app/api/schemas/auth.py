"""Request and response models for authentication endpoints."""

from __future__ import annotations

import re
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field, field_validator

_EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def _validate_email(value: str) -> str:
    stripped = value.strip()
    if not _EMAIL_PATTERN.match(stripped):
        raise ValueError("Enter a valid email address.")
    return stripped


class RegisterRequest(BaseModel):
    email: str = Field(min_length=3, max_length=320)
    password: str = Field(min_length=8, max_length=256)
    display_name: str = Field(min_length=1, max_length=255)

    @field_validator("email")
    @classmethod
    def _email(cls, value: str) -> str:
        return _validate_email(value)


class LoginRequest(BaseModel):
    email: str = Field(min_length=3, max_length=320)
    password: str = Field(min_length=1, max_length=256)

    @field_validator("email")
    @classmethod
    def _email(cls, value: str) -> str:
        return _validate_email(value)


class ChangePasswordRequest(BaseModel):
    current_password: str = Field(min_length=1, max_length=256)
    new_password: str = Field(min_length=8, max_length=256)


class ForgotPasswordRequest(BaseModel):
    email: str = Field(min_length=3, max_length=320)

    @field_validator("email")
    @classmethod
    def _email(cls, value: str) -> str:
        return _validate_email(value)


class ResetPasswordRequest(BaseModel):
    token: str = Field(min_length=1)
    new_password: str = Field(min_length=8, max_length=256)


class VerifyEmailConfirmRequest(BaseModel):
    token: str = Field(min_length=1)


class UserResponse(BaseModel):
    """Never gains a password_hash field -- see app.identity.contracts.User."""

    id: UUID
    email: str
    display_name: str
    is_active: bool
    email_verified: bool
    created_at: datetime
    updated_at: datetime
    last_login_at: datetime | None


class MessageResponse(BaseModel):
    message: str

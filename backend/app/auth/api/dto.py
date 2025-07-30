from pydantic import BaseModel, constr
from typing import Optional

class UserRegisterDTO(BaseModel):
    """DTO for user registration"""

    name: str
    email: str
    password: constr(min_length=8, max_length=100)  # type: ignore


class EmailVerificationDTO(BaseModel):
    """DTO for email verification"""

    email: str
    otp: str  # type: ignore


class LoginDTO(BaseModel):
    """DTO for user login"""

    email: str
    password: str




class PasswordResetRequestDTO(BaseModel):
    """DTO for password reset request"""

    email: str


class PasswordResetDTO(BaseModel):
    """DTO for password reset"""
    email: str
    otp: str
    new_password: constr(min_length=8, max_length=100)  # type: ignore


class RefreshTokenDTO(BaseModel):
    refresh_token: str

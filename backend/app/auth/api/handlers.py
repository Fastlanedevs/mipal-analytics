from typing import Any

from fastapi import HTTPException

from app.auth.api.dto import (
    EmailVerificationDTO,
    LoginDTO,
    PasswordResetDTO,
    PasswordResetRequestDTO,
    UserRegisterDTO,
)

from app.auth.service.auth_service import AuthService
from pkg.log.logger import Logger


class AuthHandler:
    def __init__(self, auth_service: AuthService, logger: Logger):
        self.auth_service = auth_service
        self.logger = logger

    async def register_user(self, user_data: UserRegisterDTO) -> dict[str, Any]:
        result = await self.auth_service.register_with_email(
            user_data.email,
            user_data.password,
            user_data.name,
        )
        return {
            "message": "Registration successful, please verify your email",
            "detail": result,
        }

    async def verify_email(
        self, verification_data: EmailVerificationDTO
    ) -> dict[str, Any]:
        tokens = await self.auth_service.verify_email_otp(
            verification_data.email, verification_data.otp
        )
        return {
            "message": "Email verified successfully",
            "access_token": tokens["access_token"],
            "refresh_token": tokens["refresh_token"],
            "token_type": "bearer",
        }

    async def login(self, login_data: LoginDTO) -> dict[str, Any]:
        tokens = await self.auth_service.login_with_email(
            login_data.email, login_data.password
        )
        return {
            "message": "Login successful",
            "access_token": tokens["access_token"],
            "refresh_token": tokens["refresh_token"],
            "token_type": "bearer",
        }


    async def refresh_token(self, refresh_token: str) -> dict[str, Any]:
        tokens = await self.auth_service.refresh_token(refresh_token)
        return {
            "access_token": tokens["access_token"],
            "refresh_token": tokens["refresh_token"],
            "token_type": "bearer",
        }

    async def logout(self) -> dict[str, str]:
        return {"message": "Logged out successfully"}

    async def request_password_reset(self, reset_data: PasswordResetRequestDTO):
        await self.auth_service.request_password_reset(reset_data.email)
        return {"message": "Password reset instructions sent to email"}

    async def reset_password(self, reset_data: PasswordResetDTO):
        await self.auth_service.reset_password(
            reset_data.email, reset_data.otp, reset_data.new_password
        )
        return {"message": "Password reset successful"}


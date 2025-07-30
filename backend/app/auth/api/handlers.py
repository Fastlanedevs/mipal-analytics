from typing import Any

from fastapi import HTTPException

from app.auth.api.dto import (
    AzureAuthDTO,
    EmailVerificationDTO,
    GoogleAuthDTO,
    LoginDTO,
    PasswordResetDTO,
    PasswordResetRequestDTO,
    UserRegisterDTO,
)
from app.auth.entity.entity import (
    AzureAccount,
    AzureAuth,
    AzureProfile,
    AzureUser,
    GoogleAccount,
    GoogleAuthData,
    GoogleProfile,
    GoogleUser,
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

    async def google_auth(self, google_auth_request: GoogleAuthDTO) -> dict[str, Any]:
        google_auth_entity = model_google_auth_dto_to_entity(google_auth_request)
        tokens = await self.auth_service.register_with_google(google_auth_entity)
        return {
            "message": "Google authentication successful",
            "access_token": tokens["access_token"],
            "refresh_token": tokens["refresh_token"],
            "token_type": "bearer",
        }

    async def azure_auth(self, azure_auth_request: AzureAuthDTO) -> dict[str, Any]:
        try:
            azure_auth_entity = model_azure_auth_dto_to_entity(azure_auth_request)
            tokens = await self.auth_service.register_with_azure(azure_auth_entity)
            return {
                "message": "Microsoft authentication successful",
                "access_token": tokens["access_token"],
                "refresh_token": tokens["refresh_token"],
                "token_type": "bearer",
            }
        except Exception as e:
            self.logger.error(f"Error during Azure authentication: {e!s}")
            raise HTTPException(status_code=500, detail="Unprocessable Entity")

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


def model_google_auth_dto_to_entity(data: GoogleAuthDTO) -> GoogleAuthData:
    user = GoogleUser(
        email=data.user.email,
        name=data.user.name,
        id=data.user.id,
        image=data.user.image,
    )
    account = GoogleAccount(
        provider=data.account.provider,
        type=data.account.type,
        providerAccountId=data.account.providerAccountId,
        access_token=data.account.access_token,
        expires_at=data.account.expires_at,
        refresh_token=data.account.refresh_token,
        scope=data.account.scope,
        token_type=data.account.token_type,
        id_token=data.account.id_token,
    )
    profile = GoogleProfile(
        iss=data.profile.iss,
        azp=data.profile.azp,
        aud=data.profile.aud,
        sub=data.profile.sub,
        hd=data.profile.hd,
        email=data.profile.email,
        email_verified=data.profile.email_verified,
        at_hash=data.profile.at_hash,
        name=data.profile.name,
        given_name=data.profile.given_name,
        family_name=data.profile.family_name,
        picture=data.profile.picture,
        iat=data.profile.iat,
        exp=data.profile.exp,
    )
    return GoogleAuthData(
        user=user,
        account=account,
        profile=profile,
    )


def model_azure_auth_dto_to_entity(data: AzureAuthDTO) -> AzureAuth:
    user = AzureUser(
        id=data.user.id,
        name=data.user.name,
        email=data.user.email,
        image=data.user.image,
    )
    account = AzureAccount(
        provider=data.account.provider,
        type=data.account.type,
        providerAccountId=data.account.providerAccountId,
        token_type=data.account.token_type,
        scope=data.account.scope,
        expires_at=data.account.expires_at,
        ext_expires_in=data.account.ext_expires_in,
        access_token=data.account.access_token,
        id_token=data.account.id_token,
    )
    profile = AzureProfile(
        ver=data.profile.ver,
        iss=data.profile.iss,
        sub=data.profile.sub,
        aud=data.profile.aud,
        exp=data.profile.exp,
        iat=data.profile.iat,
        nbf=data.profile.nbf,
        name=data.profile.name,
        preferred_username=data.profile.preferred_username,
        oid=data.profile.oid,
        email=data.profile.email,
        tid=data.profile.tid,
        aio=data.profile.aio,
    )
    return AzureAuth(
        user=user,
        account=account,
        profile=profile,
    )

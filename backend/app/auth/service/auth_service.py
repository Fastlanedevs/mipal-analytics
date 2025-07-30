import random
import string
from datetime import datetime, timedelta
from typing import Any

import bcrypt
from fastapi import HTTPException

from app.user.entities.aggregate import UserAggregate
from app.user.service.user_service import UserService
from pkg.auth_token_client.client import TokenClient, TokenPayload
from pkg.email_templates.signup_otp import get_email_subject, get_email_template
from pkg.email_templates.password_reset_otp import get_email_subject as get_reset_email_subject, get_email_template as get_reset_email_template
from pkg.log.logger import Logger
from pkg.smtp_client.client import EmailClient
from pkg.redis.client import RedisClient

REDIS_OTP_STRING = "otp_"
REDIS_PASSWORD_RESET_OTP = "password_reset_otp_"

class AuthService:
    def __init__(
        self,
        user_service: UserService,
        smtp_client: EmailClient,
        token_client: TokenClient,
        redis_client: RedisClient,
        logger: Logger,
    ):
        self.token_client: TokenClient = token_client
        self.redis_client = redis_client
        self.user_service: UserService = user_service
        self.smtp_client: EmailClient = smtp_client
        self.logger = logger

    def _generate_otp(self) -> str:
        """Generate a 6-digit OTP"""
        return "".join(random.choices(string.digits, k=6))

    def _hash_password(self, password: str) -> str:
        """Hash password using bcrypt"""
        salt = bcrypt.gensalt()
        return bcrypt.hashpw(password.encode(), salt).decode()

    def _verify_password(self, password: str, hashed: str) -> bool:
        """Verify password against hash"""
        return bcrypt.checkpw(password.encode(), hashed.encode())

    def _create_tokens(
        self,
        user_id: str,
        joined_org: bool,
        role: str = "MEMBER",
        org_id: str | None = None,
        email: str | None = None
    ) -> dict[str, str]:
        payload = TokenPayload(
            user_id=user_id, joined_org=joined_org, role=role, org_id=org_id, email=email
        )
        return self.token_client.create_tokens(payload)

    async def register_with_email(
        self, email: str, password: str, name: str
    ) -> dict[str, str]:
        """Register a new user with email and password"""
        # Check if user exists
        existing_user = await self.user_service.get_user_by_email(email)
        if existing_user:
            if existing_user.user.is_email_verified:
                raise HTTPException(status_code=400, detail="Email already registered, Please login")
            else:
                # Delete existing user
                await self.user_service.delete_user(existing_user.user.id)
                # Generate and store OTP
                otp = self._generate_otp()
                self.redis_client.set_value(REDIS_OTP_STRING + email, otp, expiry=600)
                email_body = get_email_template(otp=otp)
                subject = get_email_subject(otp=otp)
                # Send OTP email
                await self.smtp_client.send_email([email], subject, html_content=email_body)
                # Create user with same email but new hashed password
                hashed_password = self._hash_password(password)
                await self.user_service.create_user(
                    email, hashed_password, name, is_email_verified=False
                )
                return {"message": "Please verify your email with the OTP sent"}

        # Generate and store OTP
        otp = self._generate_otp()
        self.redis_client.set_value(REDIS_OTP_STRING + email, otp, expiry=600)

        email_body = get_email_template(otp=otp)
        subject = get_email_subject(otp=otp)
        # Send OTP email
        await self.smtp_client.send_email([email], subject, html_content=email_body)

        # Create user with hashed password
        hashed_password = self._hash_password(password)
        await self.user_service.create_user(
            email, hashed_password, name, is_email_verified=False
        )

        return {"message": "Please verify your email with the OTP sent"}

    async def verify_email_otp(self, email: str, otp: str) -> dict[str, str]:
        """Verify email using OTP"""
        try:
            stored_otp = self.redis_client.get_value(REDIS_OTP_STRING + email)

            if not stored_otp:
                raise HTTPException(status_code=400, detail="No OTP request found")
            else:
                stored_otp = str(stored_otp)

            if stored_otp != otp:
                raise HTTPException(status_code=400, detail="Invalid OTP")

            # Update user verification status
            user: UserAggregate | None = await self.user_service.get_user_by_email(email)
            if not user or not user.user:
                raise HTTPException(status_code=404, detail="User not found")

            await self.user_service.update_email_verification(
                user.user.id, is_verified=True
            )

            self.redis_client.delete(REDIS_OTP_STRING + email)

            return self._create_tokens(user.user.id, user.user.joined_org, email=email)
        except Exception as e:
            self.logger.error(f"Error verifying email OTP: {e}")
            raise HTTPException(status_code=400, detail="Invalid OTP")

    async def login_with_email(self, email: str, password: str) -> dict[str, str]:
        """Login with email and password"""
        user: UserAggregate | None = await self.user_service.get_user_by_email(email)
        if (
            not user
            or not user.user
            or not self._verify_password(password, user.user.password_hash)
        ):
            raise HTTPException(status_code=401, detail="Invalid credentials")

        if not user.user.is_email_verified:
            # Generate and store OTP
            otp = self._generate_otp()
            self.redis_client.set_value(REDIS_OTP_STRING + email, otp, expiry=600)


            email_body = get_email_template(otp)
            email_subject = get_email_subject(otp)
            # Send OTP email
            await self.smtp_client.send_email(
                [email], email_subject, html_content=email_body
            )
            raise HTTPException(status_code=403, detail=email)
        if user.user.joined_org:
            return self._create_tokens(
                user.user.id,
                user.user.joined_org,
                user.user.org.role,
                user.user.org.organisation_id,
                email=email
            )

        return self._create_tokens(user.user.id, user.user.joined_org, email=email)


    async def refresh_token(self, refresh_token: str) -> dict[str, str]:
        """Generate new access token using refresh token"""
        try:
            payload = self.token_client.decode_token(refresh_token, is_refresh=True)

            user: UserAggregate | None = await self.user_service.get_user_by_id(
                payload["user_id"]
            )
            if not user or not user.user:
                raise HTTPException(status_code=401, detail="User not found")
            if user.user.joined_org:
                return self._create_tokens(
                    user.user.id,
                    user.user.joined_org,
                    user.user.org.role,
                    user.user.org.organisation_id,
                    email=user.user.email
                )
            return self._create_tokens(user.user.id, user.user.joined_org, email=user.user.email)

        except Exception as e:
            self.logger.error(f"Error refreshing token: {e}")

            raise HTTPException(status_code=401, detail=e)

    async def request_password_reset(self, email: str) -> None:
        """Send password reset OTP to user email"""
        user: UserAggregate | None = await self.user_service.get_user_by_email(email)
        if not user or not user.user:
            # Don't reveal if user exists to prevent email enumeration
            self.logger.info(f"Password reset requested for non-existent email: {email}")
            return
            
        # Skip OTP for OAuth users who don't have passwords
        if user.user.auth_provider != "email":
            raise HTTPException(
                status_code=400, 
                detail=f"This account uses {user.user.auth_provider} authentication. Please log in with {user.user.auth_provider}."
            )

        # Generate and store OTP
        otp = self._generate_otp()
        # Store OTP with 10 minute expiry
        self.redis_client.set_value(REDIS_PASSWORD_RESET_OTP + email, otp, expiry=600)
        
        # Send password reset email with OTP
        subject = get_reset_email_subject(otp)
        body = get_reset_email_template(otp)
        await self.smtp_client.send_email([email], subject, html_content=body)
        
        self.logger.info(f"Password reset OTP sent to: {email}")

    async def reset_password(self, email: str, otp: str, new_password: str) -> None:
        """Reset user password with OTP"""
        user: UserAggregate | None = await self.user_service.get_user_by_email(email)
        if not user or not user.user:
            raise HTTPException(status_code=404, detail="User not found")
            
        if user.user.auth_provider != "email":
            raise HTTPException(
                status_code=400, 
                detail=f"Cannot reset password for {user.user.auth_provider} account"
            )
            
        # Get stored OTP from Redis
        stored_otp = self.redis_client.get_value(REDIS_PASSWORD_RESET_OTP + email)
        if not stored_otp:
            raise HTTPException(status_code=400, detail="OTP expired or not requested")
            
        # Convert to string if needed
        stored_otp = str(stored_otp)
        
        # Verify OTP
        if stored_otp != otp:
            raise HTTPException(status_code=400, detail="Invalid OTP")
            
        # Hash new password
        hashed_password = self._hash_password(new_password)
        
        # Update user password in repository
        await self._update_user_password(user.user.id, hashed_password)
        
        # Delete OTP after successful password reset
        self.redis_client.delete(REDIS_PASSWORD_RESET_OTP + email)
        
        self.logger.info(f"Password reset successful for user: {email}")
        
    async def _update_user_password(self, user_id: str, new_password_hash: str) -> None:
        """Update user's password hash in database"""
        try:
            # Get user by ID
            user = await self.user_service.get_user_by_id(user_id)
            if not user or not user.user:
                raise HTTPException(status_code=404, detail="User not found")
                
            # Update password using the user service
            await self.user_service.update_user_password(user_id, new_password_hash)
            
        except Exception as e:
            self.logger.error(f"Error updating user password: {e}")
            raise HTTPException(status_code=500, detail="Failed to update password")

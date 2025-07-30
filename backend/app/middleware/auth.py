import os
from enum import Enum
from typing import Optional
import jwt
from fastapi import HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import JSONResponse, Response

from pkg.log.logger import Logger


class AuthError(Enum):
    MISSING_TOKEN = "MISSING_TOKEN"
    EXPIRED_TOKEN = "EXPIRED_TOKEN"
    INVALID_TOKEN = "INVALID_TOKEN"
    VALIDATION_ERROR = "VALIDATION_ERROR"
    SERVER_ERROR = "SERVER_ERROR"


class TokenData(BaseModel):
    user_id: str
    joined_org: bool
    role: str = ""
    org_id: str = ""
    email: Optional[str] = None


class AuthException(HTTPException):
    def __init__(self, error_type: AuthError, detail: str):
        self.error_type = error_type
        status_code = 401 if error_type != AuthError.SERVER_ERROR else 500
        super().__init__(status_code=status_code, detail=detail)


class AuthMiddleware(BaseHTTPMiddleware):
    def __init__(self, app):
        super().__init__(app)
        self.public_paths: set[str] = {
            "/health",
            "/docs",
            "/openapi.json",
            "/auth/register",
            "/auth/login",
            "/auth/verify-email",
            "/auth/refresh-token",
            "/auth/password-reset-request",
            "/auth/password-reset",
            "/auth/refresh",
            "/",
            "/callback",
            "/admin/login",
            "/admin/",
        
        }
        
        self.logger = Logger()
        self.secret_key: str = os.getenv("JWT_SUPER_SECRET", "")
        if not self.secret_key:
            raise ValueError("JWT_SUPER_SECRET environment variable is not set")

        self.security = HTTPBearer(
            auto_error=False, description="Bearer token authentication"
        )

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        try:
            # Skip authentication for public paths
            if request.url.path in self.public_paths:
                return await call_next(request)
                
            # Skip authentication for all admin routes
            if request.url.path.startswith("/admin/"):
                return await call_next(request)

            return await self._authenticate(request, call_next)

        except AuthException as auth_err:
            self.logger.warning(
                f"Authentication error: {auth_err.error_type.value}",
                extra={
                    "path": request.url.path,
                    "error_type": auth_err.error_type.value,
                    "detail": auth_err.detail,
                },
            )
            return JSONResponse(
                status_code=auth_err.status_code,
                content={"error": auth_err.error_type.value, "detail": auth_err.detail},
            )
        except Exception:
            self.logger.error(
                "Unexpected error in auth middleware",
                exc_info=True,
                extra={"path": request.url.path},
            )
            return JSONResponse(
                status_code=500,
                content={
                    "error": AuthError.SERVER_ERROR.value,
                    "detail": "Internal server error",
                },
            )

    async def _authenticate(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        try:
            # Get token from Authorization header
            credentials: HTTPAuthorizationCredentials | None = await self.security(
                request
            )

            if not credentials:
                raise AuthException(
                    AuthError.MISSING_TOKEN,
                    "Missing or invalid Bearer token in Authorization header",
                )

            # Validate the token and extract user_id
            token_data = self._validate_token(credentials.credentials)

            # Set validated data in request state
            request.state.user_id = token_data.user_id
            request.state.role = token_data.role
            request.state.org_id = token_data.org_id
            request.state.joined_org = token_data.joined_org
            request.state.email = token_data.email

            return await call_next(request)

        except jwt.ExpiredSignatureError:
            raise AuthException(AuthError.EXPIRED_TOKEN, "Token has expired")
        except jwt.InvalidTokenError:
            raise AuthException(AuthError.INVALID_TOKEN, "Invalid token format")

    def _validate_token(self, token: str) -> TokenData:
        try:
            # Remove potential 'b' prefix and quotes from token
            token = token.strip("b'")

            payload = jwt.decode(token, self.secret_key, algorithms=["HS256"])

            # Validate required fields
            user_id = payload.get("user_id")
            if not user_id:
                raise ValueError("Missing user_id in token")
            if payload.get("joined_org"):
                return TokenData(
                    user_id=user_id,
                    joined_org=payload.get("joined_org", False),
                    role=payload.get("role", ""),
                    org_id=payload.get("org_id", ""),
                    email=payload.get("email", None)
                )
            return TokenData(
                user_id=user_id,
                joined_org=payload.get("joined_org", False),
                email=payload.get("email", None)
            )

            # Create TokenData with all fields

        except (jwt.ExpiredSignatureError, jwt.InvalidTokenError):
            raise
        except Exception as e:
            self.logger.error("Token validation failed", exc_info=True)
            raise AuthException(
                AuthError.VALIDATION_ERROR, f"Token validation failed: {e!s}"
            )


async def get_token_detail(request: Request) -> TokenData:
    """Dependency function to get current user ID from request state"""
    user_id = getattr(request.state, "user_id", None)
    if not user_id:
        raise AuthException(AuthError.VALIDATION_ERROR, "Not authenticated")
    joined_org = request.state.joined_org
    role: str = getattr(request.state, "role", None)
    org_id = getattr(request.state, "org_id", None)
    email: str = getattr(request.state, "email", None)
    if not joined_org:
        org_id = ""
        joined_org = False

    token_detail = TokenData(
        user_id=user_id, joined_org=joined_org, role=role, org_id=org_id, email=email
    )
    return token_detail

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


class GoogleUserDTO(BaseModel):
    """DTO for Google user data"""

    id: str
    name: str
    email: str
    image: str | None = None


class GoogleAccountDTO(BaseModel):
    """DTO for Google account data"""

    provider: str
    type: str
    providerAccountId: str
    access_token: str
    expires_at: int
    refresh_token: str
    scope: str
    token_type: str
    id_token: str


class GoogleProfileDTO(BaseModel):
    iss: str
    azp: str
    aud: str
    sub: str
    hd: Optional[str] = None
    email: str
    email_verified: bool
    at_hash: str
    name: str
    given_name: Optional[str] = None
    picture: Optional[str] = None
    family_name: Optional[str] = None
    iat: int
    exp: int


class GoogleAuthDTO(BaseModel):
    """DTO for Google authentication"""

    user: GoogleUserDTO
    account: GoogleAccountDTO
    profile: GoogleProfileDTO


class AzureUserDTO(BaseModel):
    id: str
    name: str
    email: str
    image: str | None = None


class AzureAccountDTO(BaseModel):
    provider: str
    type: str
    providerAccountId: str
    token_type: str
    scope: str
    expires_at: int
    ext_expires_in: int
    access_token: str
    id_token: str


class AzureProfileDTO(BaseModel):
    ver: str
    iss: str
    sub: str
    aud: str
    exp: int
    iat: int
    nbf: int
    name: str
    preferred_username: str
    oid: str
    email: str
    tid: str
    aio: str


class AzureAuthDTO(BaseModel):
    user: AzureUserDTO
    account: AzureAccountDTO
    profile: AzureProfileDTO


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

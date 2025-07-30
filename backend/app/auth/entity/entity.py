from pydantic import BaseModel
from typing import Optional


class GoogleUser(BaseModel):
    id: str
    name: str
    email: str
    image: str | None = None


class GoogleAccount(BaseModel):
    provider: str
    type: str
    providerAccountId: str
    access_token: str
    expires_at: int
    refresh_token: str
    scope: str
    token_type: str
    id_token: str


class GoogleProfile(BaseModel):
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


class GoogleAuthData(BaseModel):
    user: GoogleUser
    account: GoogleAccount
    profile: GoogleProfile


class AzureUser(BaseModel):
    id: str
    name: str
    email: str
    image: str | None = None


class AzureAccount(BaseModel):
    provider: str
    type: str
    providerAccountId: str
    token_type: str
    scope: str
    expires_at: int
    ext_expires_in: int
    access_token: str
    id_token: str


class AzureProfile(BaseModel):
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


class AzureAuth(BaseModel):
    user: AzureUser
    account: AzureAccount
    profile: AzureProfile

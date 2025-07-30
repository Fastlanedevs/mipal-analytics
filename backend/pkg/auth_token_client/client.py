from dataclasses import dataclass
from datetime import datetime, timedelta

import jwt


@dataclass
class TokenPayload:
    user_id: str
    joined_org: bool
    role: str
    org_id: str | None = None
    email: str | None = None


class TokenClient:
    def __init__(self, secret_key: str, refresh_secret_key: str):
        self.secret_key = secret_key
        self.refresh_secret_key = refresh_secret_key

    def create_tokens(self, payload: TokenPayload) -> dict[str, str]:
        """Create access and refresh tokens"""
        token_data = {
            "user_id": str(payload.user_id),
            "joined_org": payload.joined_org,
            "role": payload.role,
            "org_id": payload.org_id,
            "email": payload.email,
        }

        access_token = self._create_access_token(token_data)
        refresh_token = self._create_refresh_token(token_data)

        return {"access_token": access_token, "refresh_token": refresh_token}

    def _create_access_token(self, data: dict) -> str:
        """Create access token with 30 min expiry"""
        to_encode = data.copy()
        to_encode.update({"exp": datetime.utcnow() + timedelta(minutes=30)})
        return jwt.encode(to_encode, self.secret_key, algorithm="HS256")

    def _create_refresh_token(self, data: dict) -> str:
        """Create refresh token with 14 day expiry"""
        to_encode = data.copy()
        to_encode.update({"exp": datetime.utcnow() + timedelta(days=14)})
        return jwt.encode(to_encode, self.refresh_secret_key, algorithm="HS256")

    def decode_token(self, token: str, is_refresh: bool = False) -> dict:
        """Decode and verify a token"""
        try:
            secret = self.refresh_secret_key if is_refresh else self.secret_key
            return jwt.decode(token, secret, algorithms=["HS256"])
        except jwt.ExpiredSignatureError:
            raise ValueError("Token has expired")
        except jwt.InvalidTokenError:
            raise ValueError("Invalid token")

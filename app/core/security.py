from __future__ import annotations

import base64
import hashlib
import hmac
import json
import secrets
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.core.errors import error
from app.database import settings
from app.models import RefreshToken, User
from app.schemas import TokenPair

ACCESS_MINUTES = 20
REFRESH_DAYS = 14
ACCESS_SECRET = settings.jwt_secret
ACCESS_SECRET_BYTES = ACCESS_SECRET.encode()

def _b64encode(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).rstrip(b"=").decode()


def _b64decode(value: str) -> bytes:
    return base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))


def create_access_token(user_id: int) -> str:
    now = datetime.now(timezone.utc)
    header = _b64encode(b'{"alg":"HS256","typ":"JWT"}')
    payload = _b64encode(
        json.dumps({"sub": str(user_id), "iat": int(now.timestamp()),
                    "exp": int((now + timedelta(minutes=ACCESS_MINUTES)).timestamp())}).encode()
    )
    signing_input = f"{header}.{payload}"
    signature = hmac.new(ACCESS_SECRET_BYTES, signing_input.encode(), hashlib.sha256).digest()
    return f"{signing_input}.{_b64encode(signature)}"


def decode_access_token(token: str) -> int:
    try:
        header, payload, signature = token.split(".")
        signing_input = f"{header}.{payload}"
        expected = hmac.new(
            ACCESS_SECRET_BYTES, signing_input.encode(), hashlib.sha256
        ).digest()
        if not hmac.compare_digest(expected, _b64decode(signature)):
            raise ValueError("invalid signature")
        data = json.loads(_b64decode(payload))
        if int(data["exp"]) <= int(datetime.now(timezone.utc).timestamp()):
            raise ValueError("expired token")
        return int(data["sub"])
    except (ValueError, KeyError, TypeError, json.JSONDecodeError) as exc:
        raise error("INVALID_TOKEN", "The access token is invalid or expired.", 401) from exc


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 310_000)
    return f"pbkdf2_sha256${_b64encode(salt)}${_b64encode(digest)}"


def verify_password(password: str, encoded: str) -> bool:
    try:
        algorithm, salt, digest = encoded.split("$")
        if algorithm != "pbkdf2_sha256":
            return False
        actual = hashlib.pbkdf2_hmac("sha256", password.encode(), _b64decode(salt), 310_000)
        return hmac.compare_digest(actual, _b64decode(digest))
    except ValueError:
        return False


def issue_tokens(db: Session, user: User) -> TokenPair:
    raw_refresh = secrets.token_urlsafe(48)
    db.add(
        RefreshToken(
            user_id=user.id,
            token_hash=hashlib.sha256(raw_refresh.encode()).hexdigest(),
            expires_at=datetime.now(timezone.utc) + timedelta(days=REFRESH_DAYS),
        )
    )
    return TokenPair(access_token=create_access_token(user.id), refresh_token=raw_refresh)


from datetime import UTC, datetime, timedelta
from uuid import uuid4

import jwt
from pwdlib import PasswordHash

ALGORITHM = "HS256"
TOKEN_ISSUER = "autotestreport-hub"
TOKEN_AUDIENCE = "autotestreport-hub-api"
password_hash = PasswordHash.recommended()
DUMMY_PASSWORD_HASH = password_hash.hash("constant-time placeholder password")


def hash_password(password: str) -> str:
    return password_hash.hash(password)


def create_access_token(
    subject: str,
    secret_key: str,
    expires_delta: timedelta,
) -> str:
    now = datetime.now(UTC)
    payload = {
        "sub": subject,
        "iss": TOKEN_ISSUER,
        "aud": TOKEN_AUDIENCE,
        "iat": now,
        "exp": now + expires_delta,
        "jti": str(uuid4()),
    }
    return jwt.encode(payload, secret_key, algorithm=ALGORITHM)


def decode_access_token(token: str, secret_key: str) -> str | None:
    try:
        payload = jwt.decode(
            token,
            secret_key,
            algorithms=[ALGORITHM],
            issuer=TOKEN_ISSUER,
            audience=TOKEN_AUDIENCE,
            options={"require": ["sub", "iat", "exp", "iss", "aud", "jti"]},
        )
    except jwt.InvalidTokenError:
        return None

    subject = payload.get("sub")
    return subject if isinstance(subject, str) and subject else None

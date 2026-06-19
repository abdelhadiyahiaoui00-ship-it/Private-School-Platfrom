from datetime import datetime, timedelta, timezone
from typing import Any

from jose import JWTError, jwt

from src.core.config import settings


def encode_access_token(payload: dict[str, Any]) -> str:
    now = datetime.now(timezone.utc)
    expire = now + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    data = {**payload, "iat": now, "exp": expire, "type": "access"}
    return jwt.encode(data, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def decode_access_token(token: str) -> dict[str, Any]:
    from src.modules.auth.exceptions import TokenInvalid, TokenExpired

    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        if payload.get("type") != "access":
            raise TokenInvalid()
        return payload
    except jwt.ExpiredSignatureError:
        raise TokenExpired()
    except JWTError:
        raise TokenInvalid()

from datetime import datetime, timedelta, timezone
from jose import JWTError, jwt
from config import settings
from uuid import UUID


def create_access_token(data: dict) -> str:
    to_encode = data.copy()
    if "sub" in to_encode and isinstance(to_encode["sub"], UUID):
        to_encode["sub"] = str(to_encode["sub"])
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def decode_access_token(token: str) -> dict | None:
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        
        if "sub" in payload:
            payload["sub"] = UUID(payload["sub"])
        return payload

    except (JWTError, ValueError):
        return None
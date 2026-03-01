from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from datetime import datetime, timedelta, timezone
from uuid import UUID

from app.repositories import get_user_by_email, create_user
from app.repositories.refresh_token_repository import (
    create_refresh_token,
    get_refresh_token,
    revoke_token,
    revoke_all_user_tokens
)
from app.schemas import UserCreate, UserLogin, UserResponse, Token
from app.utils import verify_password, create_access_token
from app.utils.token_utils import generate_refresh_token
from config import settings


REFRESH_TOKEN_EXPIRE_DAYS = 7


def register_user(db: Session, user_data: UserCreate) -> UserResponse:
    existing_user = get_user_by_email(db, user_data.email)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    return create_user(db, user_data)


def login_user(db: Session, user_data: UserLogin) -> tuple[Token, str]:
    user = get_user_by_email(db, user_data.email)

    if not user or not verify_password(user_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token = create_access_token(data={"sub": str(user.id), "email": user.email})

    refresh_token = generate_refresh_token()
    expires_at = datetime.now(timezone.utc) + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    create_refresh_token(db, user_id=user.id, token=refresh_token, expires_at=expires_at)

    return Token(access_token=access_token), refresh_token


def refresh_access_token(db: Session, refresh_token: str) -> tuple[Token, str]:
    db_token = get_refresh_token(db, refresh_token)

    if db_token and db_token.revoked:
        revoke_all_user_tokens(db, db_token.user_id)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token reuse detected — all sessions revoked",
        )

    if not db_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token",
        )

    if datetime.now(timezone.utc) > db_token.expires_at.replace(tzinfo=timezone.utc):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token expired",
        )

    revoke_token(db, refresh_token)

    new_access_token = create_access_token(
        data={"sub": str(db_token.user_id), "email": db_token.user.email}
    )
    new_refresh_token = generate_refresh_token()
    expires_at = datetime.now(timezone.utc) + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    create_refresh_token(db, user_id=db_token.user_id, token=new_refresh_token, expires_at=expires_at)

    return Token(access_token=new_access_token), new_refresh_token


def logout_user(db: Session, refresh_token: str) -> None:
    db_token = get_refresh_token(db, refresh_token)
    if not db_token or db_token.revoked:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token",
        )
    revoke_token(db, refresh_token)
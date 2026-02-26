from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.repositories import get_user_by_email, create_user
from app.schemas import UserCreate, UserLogin, UserResponse, Token
from app.utils import verify_password, create_access_token


def register_user(db: Session, user_data: UserCreate) -> UserResponse:
    existing_user = get_user_by_email(db, user_data.email)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    return create_user(db, user_data)


def login_user(db: Session, user_data: UserLogin) -> Token:
    user = get_user_by_email(db, user_data.email)

    if not user or not verify_password(user_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = create_access_token(data={"sub": str(user.id), "email": user.email})
    return Token(access_token=token)
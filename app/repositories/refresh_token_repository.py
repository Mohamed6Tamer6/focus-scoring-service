from sqlalchemy.orm import Session
from app.models.refresh_token import RefreshToken
from app.utils.token_utils import hash_refresh_token
from datetime import datetime
from uuid import UUID


def create_refresh_token(db: Session, user_id: UUID, token: str, expires_at: datetime) -> RefreshToken:
    
    token_hash = hash_refresh_token(token)
    db_token = RefreshToken(
        user_id=user_id,
        token_hash=token_hash,
        expires_at=expires_at
    )
    db.add(db_token)
    db.commit()
    db.refresh(db_token)
    return db_token


def get_refresh_token(db: Session, token: str) -> RefreshToken | None:
    
    token_hash = hash_refresh_token(token)
    return db.query(RefreshToken).filter(
        RefreshToken.token_hash == token_hash
    ).first()


def revoke_token(db: Session, token: str) -> None:

    token_hash = hash_refresh_token(token)
    db.query(RefreshToken).filter(
        RefreshToken.token_hash == token_hash
    ).update({"revoked": True})
    db.commit()


def revoke_all_user_tokens(db: Session, user_id: UUID) -> None:

    db.query(RefreshToken).filter(
        RefreshToken.user_id == user_id
    ).update({"revoked": True})
    db.commit()
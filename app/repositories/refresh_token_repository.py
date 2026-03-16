from sqlalchemy.orm import Session
from app.models.refresh_token import RefreshToken
from app.utils.token_utils import get_token_lookup_hash, hash_token_for_storage, verify_stored_token
from datetime import datetime
from uuid import UUID


def create_refresh_token(db: Session, user_id: UUID, token: str, expires_at: datetime) -> RefreshToken:
    token_hash = get_token_lookup_hash(token)
    token_verifier = hash_token_for_storage(token)
    
    db_token = RefreshToken(
        user_id=user_id,
        token_hash=token_hash,
        token_verifier=token_verifier,
        expires_at=expires_at
    )
    db.add(db_token)
    db.commit()
    db.refresh(db_token)
    return db_token


def get_refresh_token(db: Session, token: str) -> RefreshToken | None:
    token_hash = get_token_lookup_hash(token)
    db_tokens = db.query(RefreshToken).filter(
        RefreshToken.token_hash == token_hash
    ).all()
    
    for db_token in db_tokens:
        if verify_stored_token(token, db_token.token_verifier):
            return db_token
            
    return None


def revoke_token(db: Session, token: str) -> None:
    db_token = get_refresh_token(db, token)
    if db_token:
        db_token.revoked = True
        db.commit()



def revoke_all_user_tokens(db: Session, user_id: UUID) -> None:

    db.query(RefreshToken).filter(
        RefreshToken.user_id == user_id
    ).update({"revoked": True})
    db.commit()
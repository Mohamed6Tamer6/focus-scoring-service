import secrets
import hashlib
from app.utils.hashing import hash_password, verify_password


def generate_refresh_token() -> str:
    """Generate a high-entropy random token."""
    return secrets.token_urlsafe(32)


def get_token_lookup_hash(token: str) -> str:
    """Fast hash for database indexing/searching."""
    return hashlib.sha256(token.encode()).hexdigest()


def hash_token_for_storage(token: str) -> str:
    """Secure salted hash (Bcrypt) for storage."""
    return hash_password(token)


def verify_stored_token(plain_token: str, hashed_token: str) -> bool:
    """Verify a raw token against its Bcrypt hash."""
    return verify_password(plain_token, hashed_token)
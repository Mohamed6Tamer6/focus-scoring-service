
from app.database import SessionLocal
from app.models.refresh_token import RefreshToken
from datetime import datetime, timezone, timedelta
import uuid

def test_db_datetime():
    db = SessionLocal()
    try:
        # Create a dummy user first or use an existing one
        user_id = uuid.uuid4()
        expires_at = datetime.now(timezone.utc) + timedelta(days=7)
        
        token = RefreshToken(
            id=uuid.uuid4(),
            user_id=None, # Should fail if user_id is required, but let's see datetime
            token_hash="test",
            token_verifier="test",
            expires_at=expires_at
        )
        # We won't actually commit if it fails at object creation or pre-commit
        print(f"Token object created with expires_at: {token.expires_at}")
        
    except Exception as e:
        print(f"Error: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    test_db_datetime()

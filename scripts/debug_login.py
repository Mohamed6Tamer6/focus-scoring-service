
from app.database import SessionLocal
from app.models.user import User
from app.services.auth import login_user
from app.schemas import UserLogin
import sys

def debug_login(email, password):
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.email == email).first()
        if not user:
            print(f"User {email} not found")
            return
        
        print(f"User found: {user.id}, name: {user.name}")
        
        user_login_data = UserLogin(email=email, password=password)
        try:
            token = login_user(db, user_login_data)
            print("Login success")
        except Exception as e:
            print(f"Login failed with error: {e}")
            import traceback
            traceback.print_exc()
            
    finally:
        db.close()

if __name__ == "__main__":
    email = sys.argv[1] if len(sys.argv) > 1 else "mohamed9@example.com"
    password = sys.argv[2] if len(sys.argv) > 2 else "password" # I don't know the real password
    debug_login(email, password)

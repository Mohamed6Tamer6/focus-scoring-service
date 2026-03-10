
import sys
import os
from uuid import UUID

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.database import SessionLocal
from app.models.rbac import Role, UserRole
from app.models.user import User
from app.repositories.rbac_repository import get_role_by_name, create_role, assign_role_to_user

def setup_admin(email: str = None):
    db = SessionLocal()
    try:
        admin_role = get_role_by_name(db, "admin")
        if not admin_role:
            print("Creating 'admin' role...")
            admin_role = create_role(db, name="admin", description="Full system access")
        else:
            print("'admin' role already exists.")

        if email:
            user = db.query(User).filter(User.email == email).first()
            if not user:
                print(f"User with email {email} not found.")
                return
            
            existing_ur = db.query(UserRole).filter(
                UserRole.user_id == user.id,
                UserRole.role_id == admin_role.id
            ).first()

            if not existing_ur:
                print(f"Assigning 'admin' role to {email}...")
                assign_role_to_user(db, user_id=user.id, role_id=admin_role.id)
            else:
                print(f"User {email} already has 'admin' role.")
        
        db.commit()
    except Exception as e:
        print(f"Error: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    email_arg = sys.argv[1] if len(sys.argv) > 1 else None
    setup_admin(email_arg)

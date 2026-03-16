from sqlalchemy.orm import Session
from app.models.user import User
from app.schemas.user import UserCreate
from app.utils.hashing import hash_password
from uuid import UUID


def get_user_by_email(db: Session, email: str):
    return db.query(User).filter(User.email == email).first()


def get_user_by_id(db: Session, user_id: UUID):
    return db.query(User).filter(User.id == user_id).first()


def create_user(db: Session, user_data: UserCreate):
    hashed = hash_password(user_data.password)
    new_user = User(
        name=user_data.name,
        email=user_data.email,
        hashed_password=hashed,
        admin_id=user_data.admin_id
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user

from app.models.rbac import Role, UserRole

def get_all_admins(db: Session):
    admin_role = db.query(Role).filter(Role.name == "admin").first()
    if not admin_role:
        return []
    
    # Get all users who have this role
    return db.query(User).join(UserRole, User.id == UserRole.user_id).filter(UserRole.role_id == admin_role.id).all()
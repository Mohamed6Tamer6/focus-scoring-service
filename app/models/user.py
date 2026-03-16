from sqlalchemy import Column, String, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship, foreign
from datetime import datetime
from app.database import Base
import uuid


class User(Base):

    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    name = Column(String, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    admin_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    refresh_tokens = relationship("RefreshToken", back_populates="user", cascade="all, delete-orphan")
    focus_sessions = relationship("FocusSession", back_populates="user", cascade="all, delete-orphan")
    user_roles = relationship("UserRole", primaryjoin="User.id == foreign(UserRole.user_id)", back_populates="user", cascade="all, delete-orphan")
    
    # Self-referential relationship for users managed by an admin
    admin = relationship("User", remote_side=[id], backref="subordinates")

    @property
    def admin_info(self):
        if self.admin:
            return {"name": self.admin.name, "email": self.admin.email}
        return None

    @property
    def roles(self):
        return [ur.role.name for ur in self.user_roles]
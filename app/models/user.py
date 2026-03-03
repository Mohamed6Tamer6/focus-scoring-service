from sqlalchemy import Column, String, DateTime
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from datetime import datetime
from app.database import Base
import uuid


class User(Base):

    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    name = Column(String, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    refresh_tokens = relationship("RefreshToken", back_populates="user", cascade="all, delete-orphan")
    focus_sessions = relationship("FocusSession", back_populates="user", cascade="all, delete-orphan")
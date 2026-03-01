from sqlalchemy import Column, String, Float, Integer, DateTime, ForeignKey, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from datetime import datetime
from app.database import Base
import uuid


class FocusSession(Base):

    __tablename__ = "focus"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    
    total_time = Column(Float, nullable=False, default=0)
    focus_time = Column(Float, nullable=False, default=0)
    unfocus_time = Column(Float, nullable=False, default=0)
    absence_time = Column(Float, nullable=False, default=0)
    focus_percentage = Column(Float, nullable=False, default=0)
    absence_percentage = Column(Float, nullable=False, default=0)
    effective_focus_rate = Column(Float, nullable=False, default=0)
    total_blinks = Column(Integer, nullable=False, default=0)
    unfocus_events = Column(Integer, nullable=False, default=0)
    absence_events = Column(Integer, nullable=False, default=0)
    unfocused_periods = Column(JSON, default=[])
    absence_periods = Column(JSON, default=[])
    focus_zone = Column(String, nullable=False, default="normal")
    overall_rating = Column(String, nullable=False, default="Poor")
    average_unfocus_duration = Column(Float, nullable=True)
    longest_unfocus = Column(Float, nullable=True)
    average_absence_duration = Column(Float, nullable=True)
    longest_absence = Column(Float, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    user = relationship("User", back_populates="focus_sessions")

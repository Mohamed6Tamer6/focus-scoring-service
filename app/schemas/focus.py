from pydantic import BaseModel
from datetime import datetime
from uuid import UUID


class FocusSessionResponse(BaseModel):
    id: UUID
    user_id: UUID
    total_time: float
    focus_time: float
    unfocus_time: float
    absence_time: float
    focus_percentage: float
    absence_percentage: float
    effective_focus_rate: float
    total_blinks: int
    unfocus_events: int
    absence_events: int
    unfocused_periods: list = []
    absence_periods: list = []
    focus_zone: str
    overall_rating: str
    average_unfocus_duration: float | None = None
    longest_unfocus: float | None = None
    average_absence_duration: float | None = None
    longest_absence: float | None = None
    report_url: str | None = None  
    created_at: datetime

    class Config:
        from_attributes = True
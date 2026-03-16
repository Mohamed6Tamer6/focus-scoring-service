from sqlalchemy.orm import Session
from app.models.focus_session import FocusSession
from app.utils.supabase_storage import get_signed_url
from uuid import UUID


def save_focus_session(db: Session, user_id: UUID, report: dict) -> FocusSession:
    def serialize_periods(periods):
        return [
            {
                'start': p['start'].isoformat() if hasattr(p['start'], 'isoformat') else str(p['start']),
                'end': p['end'].isoformat() if hasattr(p['end'], 'isoformat') else str(p['end']),
                'duration': round(p['duration'], 2)
            }
            for p in periods
        ]

    session = FocusSession(
        user_id=user_id,
        total_time=round(report.get('total_time', 0), 2),
        focus_time=round(report.get('focus_time', 0), 2),
        unfocus_time=round(report.get('unfocus_time', 0), 2),
        absence_time=round(report.get('absence_time', 0), 2),
        focus_percentage=round(report.get('focus_percentage', 0), 2),
        absence_percentage=round(report.get('absence_percentage', 0), 2),
        effective_focus_rate=round(report.get('effective_focus_rate', 0), 2),
        total_blinks=report.get('total_blinks', 0),
        unfocus_events=report.get('unfocus_events', 0),
        absence_events=report.get('absence_events', 0),
        unfocused_periods=serialize_periods(report.get('unfocused_periods', [])),
        absence_periods=serialize_periods(report.get('absence_periods', [])),
        focus_zone=report.get('current_zone', 'normal'),
        overall_rating=report.get('overall_rating', 'Poor'),
        average_unfocus_duration=round(report['average_unfocus_duration'], 2) if 'average_unfocus_duration' in report else None,
        longest_unfocus=round(report['longest_unfocus'], 2) if 'longest_unfocus' in report else None,
        average_absence_duration=round(report['average_absence_duration'], 2) if 'average_absence_duration' in report else None,
        longest_absence=round(report['longest_absence'], 2) if 'longest_absence' in report else None,
        report_path=report.get('report_path'), 
    )

    db.add(session)
    db.commit()
    db.refresh(session)
    return session


from datetime import date

def get_user_sessions(db: Session, user_id: UUID, target_date: date | None = None) -> list[dict]:
    query = db.query(FocusSession).filter(FocusSession.user_id == user_id)
    
    if target_date:
        from sqlalchemy import func
        query = query.filter(func.date(FocusSession.created_at) == target_date)

    sessions = query.order_by(FocusSession.created_at.desc()).all()

    result = []
    for s in sessions:
        session_dict = {
            "id": s.id,
            "user_id": s.user_id,
            "created_at": s.created_at,
            "total_time": s.total_time,
            "focus_time": s.focus_time,
            "unfocus_time": s.unfocus_time,
            "absence_time": s.absence_time,
            "focus_percentage": s.focus_percentage,
            "absence_percentage": s.absence_percentage,
            "effective_focus_rate": s.effective_focus_rate,
            "total_blinks": s.total_blinks,
            "unfocus_events": s.unfocus_events,
            "absence_events": s.absence_events,
            "unfocused_periods": s.unfocused_periods,
            "absence_periods": s.absence_periods,
            "focus_zone": s.focus_zone,
            "overall_rating": s.overall_rating,
            "average_unfocus_duration": s.average_unfocus_duration,
            "longest_unfocus": s.longest_unfocus,
            "average_absence_duration": s.average_absence_duration,
            "longest_absence": s.longest_absence,
            "report_url": get_signed_url(s.report_path) if s.report_path else None,
        }
        result.append(session_dict)

    return result


def get_user_session_dates(db: Session, user_id: UUID) -> list[date]:
    from sqlalchemy import func
    dates = db.query(func.date(FocusSession.created_at)).filter(FocusSession.user_id == user_id).distinct().all()
    return sorted([d[0] for d in dates], reverse=True)


def get_session_by_id(db: Session, session_id: UUID) -> dict | None:
    s = db.query(FocusSession).filter(FocusSession.id == session_id).first()
    if not s:
        return None

    return {
        **s.__dict__,
        "report_url": get_signed_url(s.report_path) if s.report_path else None,
    }
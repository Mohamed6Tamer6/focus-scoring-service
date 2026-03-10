from sqlalchemy.orm import Session
from app.models.focus_session import FocusSession
from uuid import UUID


def save_focus_session(db: Session, user_id: UUID, report: dict) -> FocusSession:
    def serialize_periods(periods):
        serialized = []
        for p in periods:
            serialized.append({
                'start': p['start'].isoformat() if hasattr(p['start'], 'isoformat') else str(p['start']),
                'end': p['end'].isoformat() if hasattr(p['end'], 'isoformat') else str(p['end']),
                'duration': round(p['duration'], 2)
            })
        return serialized

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
        report_url=report.get('report_url'),
    )

    db.add(session)
    db.commit()
    db.refresh(session)
    return session


def get_user_sessions(db: Session, user_id: UUID) -> list[FocusSession]:
    return db.query(FocusSession).filter(
        FocusSession.user_id == user_id
    ).order_by(FocusSession.created_at.desc()).all()


def get_session_by_id(db: Session, session_id: UUID) -> FocusSession | None:
    return db.query(FocusSession).filter(
        FocusSession.id == session_id
    ).first()

from uuid import UUID
from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from app.core.focus_detector import FocusProcessor
from app.repositories.focus_repository import save_focus_session, get_session_by_id
from app.utils.pdf_generator import generate_pdf_report
from dateutil.parser import parse as parse_date
from sqlalchemy.orm import Session
import base64
from fastapi import WebSocket, WebSocketDisconnect
from app.core.focus_detector import FocusProcessor
from app.repositories.focus_repository import save_focus_session

_active_sessions: dict[str, FocusProcessor] = {}


def start_session(user_id: str, focus_zone: str = "normal") -> bool:
    if user_id in _active_sessions:
        _active_sessions[user_id].stop()
        del _active_sessions[user_id]

    _active_sessions[user_id] = FocusProcessor(focus_zone=focus_zone)
    return True


def process_frame(user_id: str, frame_bytes: bytes) -> dict:
    processor = _active_sessions.get(user_id)
    if not processor:
        return {"error": "No active session", "face_detected": False}
    return processor.process_frame(frame_bytes)


def set_focus_zone(user_id: str, zone: str) -> bool:
    processor = _active_sessions.get(user_id)
    if not processor:
        return False
    processor.set_focus_zone(zone)
    return True


def stop_session(db: Session, user_id: str) -> dict | None:
    processor = _active_sessions.pop(user_id, None)
    if not processor:
        return None

    report = processor.stop()
    if report:
        try:
            db_session = save_focus_session(db, UUID(user_id), report)
            report['id'] = str(db_session.id)
        except Exception as e:
            print(f"Skipping DB save: {e}")
            db.rollback()
            report['id'] = ""

    return report


def has_active_session(user_id: str) -> bool:
    return user_id in _active_sessions

def serialize_report(report: dict) -> dict:
    if not report:
        return report

    serialized = {}
    for key, value in report.items():
        if key in ('unfocused_periods', 'absence_periods'):
            periods = []
            for p in value:
                periods.append({
                    'start': p['start'].isoformat() if hasattr(p['start'], 'isoformat') else str(p['start']),
                    'end': p['end'].isoformat() if hasattr(p['end'], 'isoformat') else str(p['end']),
                    'duration': round(p['duration'], 2),
                })
            serialized[key] = periods
        elif hasattr(value, 'isoformat'):
            serialized[key] = value.isoformat()
        else:
            serialized[key] = value
    return serialized


def _parse_periods(periods):
    parsed = []
    if not periods:
        return parsed
    for p in periods:
        start = p.get('start')
        end = p.get('end')
        if isinstance(start, str): start = parse_date(start)
        if isinstance(end, str): end = parse_date(end)
        parsed.append({'start': start, 'end': end, 'duration': p.get('duration', 0)})
    return parsed

def generate_session_pdf_bytes(db: Session, session_id: str, current_user_id: UUID) -> bytes:
    session = get_session_by_id(db, session_id)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found",
        )
        
    report_data = {
        'total_time': session.total_time,
        'focus_time': session.focus_time,
        'unfocus_time': session.unfocus_time,
        'absence_time': session.absence_time,
        'total_blinks': session.total_blinks,
        'unfocused_periods': _parse_periods(session.unfocused_periods),
        'absence_periods': _parse_periods(session.absence_periods)
    }
    
    return generate_pdf_report(report_data)




async def handle_focus_websocket(websocket: WebSocket, token: str):
    from app.utils.jwt import decode_access_token
    
    # Authenticate or fallback to demo dummy user
    payload = decode_access_token(token) if token else None
    user_id = str(payload.get("sub")) if payload else "00000000-0000-0000-0000-000000000000"

    await websocket.accept()
    from app.database import SessionLocal
    
    try:
        while True:
            data = await websocket.receive_json()
            action = data.get("action")

            if action == "start":
                focus_zone = data.get("focus_zone", "normal")
                start_session(user_id, focus_zone)
                await websocket.send_json({"type": "status", "status": "started"})

            elif action == "frame":
                frame_b64 = data.get("frame")
                if frame_b64:
                    if "," in frame_b64:
                        frame_b64 = frame_b64.split(",", 1)[1]
                    try:
                        frame_bytes = base64.b64decode(frame_b64)
                        result = process_frame(user_id, frame_bytes)
                        result["type"] = "frame_result"
                        await websocket.send_json(result)
                    except Exception as e:
                        print(f"Frame processing error: {e}")

            elif action == "set_zone":
                zone = data.get("zone", "normal")
                set_focus_zone(user_id, zone)
                await websocket.send_json({"type": "status", "status": f"zone_changed_{zone}"})

            elif action == "stop":
                db = SessionLocal()
                try:
                    report = stop_session(db, user_id)
                    serialized = serialize_report(report) if report else None
                    await websocket.send_json({"type": "report", "report": serialized})
                finally:
                    db.close()
                break

    except WebSocketDisconnect:
        pass
    except Exception as e:
        print(f"WebSocket unhandled error: {e}")
    finally:
        db = SessionLocal()
        try:
            stop_session(db, user_id)
        finally:
            db.close()

import base64
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, Query, HTTPException, status
from sqlalchemy.orm import Session
from fastapi.responses import Response
from app.repositories.focus_repository import get_user_sessions, get_session_by_id
from app.database import SessionLocal
from app.utils.jwt import decode_access_token
from app.api.dependencies import get_current_user
from app.database import get_db
from app.schemas.focus import FocusSessionResponse
from app.services.focus_service import (
    start_session,
    process_frame,
    stop_session,
    set_focus_zone,
    serialize_report,
    generate_session_pdf_bytes,
    handle_focus_websocket,
)

from uuid import UUID

router = APIRouter(prefix="/focus", tags=["Focus"])

DUMMY_USER_ID = UUID("00000000-0000-0000-0000-000000000000")


@router.websocket("/ws")
async def focus_websocket(
    websocket: WebSocket,
    token: str = Query(None),
):

    await handle_focus_websocket(websocket, token)


@router.get("/sessions", response_model=list[FocusSessionResponse])
def list_sessions(
    db: Session = Depends(get_db),
):
    from app.models import FocusSession
    return db.query(FocusSession).order_by(FocusSession.created_at.desc()).all()


@router.get("/sessions/{session_id}", response_model=FocusSessionResponse)
def get_session(
    session_id: str,
    db: Session = Depends(get_db),
):
    session = get_session_by_id(db, session_id)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found",
        )
    return session


@router.get("/sessions/{session_id}/pdf")
def download_session_pdf(
    session_id: str,
    db: Session = Depends(get_db),
):
    pdf_bytes = generate_session_pdf_bytes(db, session_id, DUMMY_USER_ID)
    headers = {
        'Content-Disposition': f'attachment; filename="focus_report_{session_id}.pdf"'
    }
    return Response(content=pdf_bytes, media_type="application/pdf", headers=headers)

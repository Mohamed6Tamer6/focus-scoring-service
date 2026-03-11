import base64
from fastapi import APIRouter, WebSocket, Depends, Query, HTTPException, status
from sqlalchemy.orm import Session
from fastapi.responses import Response
from app.repositories.focus_repository import get_user_sessions, get_session_by_id
from app.api.dependencies import get_current_user
from app.database import get_db
from app.schemas.focus import FocusSessionResponse
from app.models.user import User
from app.services.focus_service import (
    generate_session_pdf_bytes,
    handle_focus_websocket,
)
from app.utils.supabase_storage import get_signed_url
from uuid import UUID

router = APIRouter(prefix="/focus", tags=["Focus"])


@router.websocket("/ws")
async def focus_websocket(
    websocket: WebSocket,
    token: str = Query(None),
):
    await handle_focus_websocket(websocket, token)


@router.get("/sessions", response_model=list[FocusSessionResponse])
def list_sessions(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # ✅ get_user_sessions returns dicts with signed URLs already generated
    return get_user_sessions(db, current_user.id)


@router.get("/sessions/{session_id}", response_model=FocusSessionResponse)
def get_session(
    session_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        session_uuid = UUID(session_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid session ID format",
        )

    session = get_session_by_id(db, session_uuid)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found",
        )
    if session["user_id"] != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access this session",
        )

    return session


@router.get("/sessions/{session_id}/pdf")
def download_session_pdf(
    session_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        session_uuid = UUID(session_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid session ID format",
        )

    session = get_session_by_id(db, session_uuid)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found",
        )
    if session["user_id"] != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access this report",
        )

    pdf_bytes = generate_session_pdf_bytes(db, session_uuid, current_user.id)
    headers = {
        'Content-Disposition': f'attachment; filename="focus_report_{session_id}.pdf"'
    }
    return Response(content=pdf_bytes, media_type="application/pdf", headers=headers)
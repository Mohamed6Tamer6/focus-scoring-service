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
from uuid import UUID
from datetime import date
from app.api.dependencies import get_current_user, get_current_admin

router = APIRouter(prefix="/focus", tags=["Focus"])


@router.websocket("/ws")
async def focus_websocket(
    websocket: WebSocket,
    token: str = Query(None),
):
    await handle_focus_websocket(websocket, token)


@router.get("/sessions", response_model=list[FocusSessionResponse])
def list_sessions(
    target_date: date | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # Filter by date if provided
    return get_user_sessions(db, current_user.id, target_date)


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
    
    # Check if user owns the session or is the admin of the owner
    is_admin = any(ur.role.name == "admin" for ur in current_user.user_roles)
    
    if session["user_id"] != current_user.id:
        if not is_admin:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to access this session",
            )
        # If it is an admin, check if the session's user reports to them
        from app.repositories import get_user_by_id as get_session_owner
        owner = get_session_owner(db, session["user_id"])
        if not owner or owner.admin_id != current_user.id:
             raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to access this subordinate's session",
            )

    return session


@router.get("/sessions/{session_id}/pdf")
def download_session_pdf(
    session_id: str,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin), # Restrict to ADMIN only
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
    
    # Ensure admin owns the user who owns the session (or it's their own session)
    if session["user_id"] != current_admin.id:
        from app.repositories import get_user_by_id as get_session_owner
        owner = get_session_owner(db, session["user_id"])
        if not owner or owner.admin_id != current_admin.id:
             raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to download this report",
            )

    pdf_bytes = generate_session_pdf_bytes(db, session_uuid, current_admin.id)
    headers = {
        'Content-Disposition': f'attachment; filename="focus_report_{session_id}.pdf"'
    }
    return Response(content=pdf_bytes, media_type="application/pdf", headers=headers)

@router.get("/admin/sessions/{user_id}", response_model=list[FocusSessionResponse])
def admin_list_user_sessions(
    user_id: UUID,
    target_date: date | None = None,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin),
):
    # Verify user reports to this admin
    from app.repositories import get_user_by_id as get_target_user
    user = get_target_user(db, user_id)
    if not user or user.admin_id != current_admin.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not authorized to view this user's sessions",
        )
    
    return get_user_sessions(db, user_id, target_date)

@router.get("/admin/sessions/{user_id}/dates", response_model=list[date])
def admin_list_user_session_dates(
    user_id: UUID,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin),
):
    from app.repositories import get_user_by_id as get_target_user
    user = get_target_user(db, user_id)
    if not user or user.admin_id != current_admin.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not authorized to view this user's sessions",
        )
    
    from app.repositories.focus_repository import get_user_session_dates
    return get_user_session_dates(db, user_id)
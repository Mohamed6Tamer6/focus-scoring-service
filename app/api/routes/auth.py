from fastapi import APIRouter, Depends, status, Response, Cookie
from sqlalchemy.orm import Session
from typing import Annotated
from app.database import get_db
from app.schemas import UserCreate, UserLogin, UserResponse, Token, UserUpdate
from app.services.auth import register_user, login_user, refresh_access_token, logout_user
from fastapi import HTTPException

router = APIRouter(prefix="/auth", tags=["Auth"])

REFRESH_TOKEN_COOKIE = "refresh_token"
COOKIE_MAX_AGE = 7 * 24 * 60 * 60  


def set_refresh_cookie(response: Response, token: str) -> None:
    response.set_cookie(
        key=REFRESH_TOKEN_COOKIE,
        value=token,
        httponly=True,       
        secure=True,         
        samesite="none",     
        max_age=COOKIE_MAX_AGE,
    )


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def register(user_data: UserCreate, db: Session = Depends(get_db)):
    return register_user(db, user_data)


from fastapi.security import OAuth2PasswordRequestForm
from fastapi import Request, Form
from typing import Union

@router.post("/login", response_model=Token)
async def login(
    request: Request,
    response: Response,
    db: Session = Depends(get_db)
):
    # Manually check content type to avoid Form parameter consumption issues
    content_type = request.headers.get("content-type", "")
    
    if "application/json" in content_type:
        try:
            body = await request.json()
            user_login_data = UserLogin(**body)
        except Exception:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid JSON login data"
            )
    else:
        # Try to parse as form data
        try:
            form = await request.form()
            email = form.get("username") or form.get("email")
            password = form.get("password")
            if not email or not password:
                raise ValueError("Missing email or password in form data")
            user_login_data = UserLogin(email=email, password=password)
        except Exception:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid form login data or missing credentials"
            )
    
    from fastapi.concurrency import run_in_threadpool
    token = await run_in_threadpool(login_user, db, user_login_data)
    set_refresh_cookie(response, token.refresh_token)
    return token


@router.post("/refresh", response_model=Token)
def refresh(
    response: Response,
    db: Session = Depends(get_db),
    refresh_token: Annotated[str | None, Cookie()] = None
):
    if not refresh_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token missing",
        )
    token = refresh_access_token(db, refresh_token)
    set_refresh_cookie(response, token.refresh_token)
    return token


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(
    response: Response,
    db: Session = Depends(get_db),
    refresh_token: Annotated[str | None, Cookie()] = None
):
    if not refresh_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token missing",
        )
    logout_user(db, refresh_token)
    response.delete_cookie(key=REFRESH_TOKEN_COOKIE, httponly=True, secure=True, samesite="none")

from app.api.dependencies import get_current_user
from app.models.user import User as UserTable
from app.repositories.user_repository import get_all_admins

@router.get("/profile", response_model=UserResponse)
def get_profile(current_user: UserTable = Depends(get_current_user)):
    return current_user

@router.patch("/profile", response_model=UserResponse)
def update_profile(
    body: UserUpdate,
    db: Session = Depends(get_db),
    current_user: UserTable = Depends(get_current_user)
):
    if body.admin_id is not None:
        current_user.admin_id = body.admin_id
    
    db.commit()
    db.refresh(current_user)
    return current_user

@router.get("/admins", response_model=list[UserResponse])
def list_admins(db: Session = Depends(get_db)):
    return get_all_admins(db)

@router.get("/subordinates", response_model=list[UserResponse])
def list_subordinates(
    db: Session = Depends(get_db),
    current_admin: UserTable = Depends(get_current_user)
):
    subordinates = db.query(UserTable).filter(UserTable.admin_id == current_admin.id).all()
    return subordinates

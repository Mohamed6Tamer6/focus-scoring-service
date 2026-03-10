from fastapi import APIRouter, Depends, status, Response, Cookie
from sqlalchemy.orm import Session
from typing import Annotated
from app.database import get_db
from app.schemas import UserCreate, UserLogin, UserResponse, Token
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
    response: Response,
    db: Session = Depends(get_db),
    username: str = Form(None),
    password: str = Form(None),
    request: Request = None
):

    if username and password:
        user_login_data = UserLogin(email=username, password=password)
    else:
        body = await request.json()
        user_login_data = UserLogin(**body)
    
    token = login_user(db, user_login_data)
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

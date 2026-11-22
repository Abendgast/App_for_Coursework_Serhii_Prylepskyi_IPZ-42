from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db, get_settings
from app.core.config import Settings
from app.models import User
from app.schemas.auth import LoginRequest, RegisterRequest, TokenResponse, UserResponse
from app.services.auth import (
    EmailAlreadyRegistered,
    InvalidCredentials,
    authenticate_user,
    issue_access_token,
    register_user,
    serialize_user,
)

router = APIRouter(prefix="/auth", tags=["authentication"])
DatabaseSession = Annotated[Session, Depends(get_db)]
AppSettings = Annotated[Settings, Depends(get_settings)]
AuthenticatedUser = Annotated[User, Depends(get_current_user)]


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
)
def register(payload: RegisterRequest, session: DatabaseSession) -> UserResponse:
    try:
        user = register_user(payload, session)
    except EmailAlreadyRegistered as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this email already exists",
        ) from error
    return serialize_user(user)


@router.post("/login", response_model=TokenResponse)
def login(
    payload: LoginRequest,
    session: DatabaseSession,
    settings: AppSettings,
) -> TokenResponse:
    try:
        user = authenticate_user(payload, session)
    except InvalidCredentials as error:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
            headers={"WWW-Authenticate": "Bearer"},
        ) from error

    return TokenResponse(
        access_token=issue_access_token(user, settings),
        expires_in=settings.access_token_expire_minutes * 60,
        user=serialize_user(user),
    )


@router.get("/me", response_model=UserResponse)
def read_current_user(
    current_user: AuthenticatedUser,
) -> UserResponse:
    return serialize_user(current_user)

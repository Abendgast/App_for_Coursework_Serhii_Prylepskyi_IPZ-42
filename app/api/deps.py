from collections.abc import Generator
from typing import Annotated
from uuid import UUID

from fastapi import Depends, Header, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.core.security import decode_access_token
from app.models import Project, User
from app.services.projects import (
    ProjectAccessDenied,
    ProjectNotFound,
    get_project_for_ingestion,
)

bearer_scheme = HTTPBearer(auto_error=False)


def get_settings(request: Request) -> Settings:
    return request.app.state.settings


def get_db(request: Request) -> Generator[Session, None, None]:
    session = request.app.state.session_factory()
    try:
        yield session
    finally:
        session.close()


BearerCredentials = Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)]
DatabaseSession = Annotated[Session, Depends(get_db)]
AppSettings = Annotated[Settings, Depends(get_settings)]
ProjectApiKey = Annotated[str | None, Header(alias="X-Project-Key")]


def get_current_user(
    credentials: BearerCredentials,
    session: DatabaseSession,
    settings: AppSettings,
) -> User:
    unauthorized = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Authentication required",
        headers={"WWW-Authenticate": "Bearer"},
    )
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise unauthorized

    subject = decode_access_token(
        credentials.credentials,
        settings.secret_key.get_secret_value(),
    )
    if subject is None:
        raise unauthorized

    user = session.scalar(select(User).where(User.id == subject))
    if user is None or not user.is_active:
        raise unauthorized
    return user


def get_ingestion_project(
    project_id: UUID,
    credentials: BearerCredentials,
    session: DatabaseSession,
    settings: AppSettings,
    api_key: ProjectApiKey = None,
) -> Project:
    owner_id = None
    if api_key is None:
        if credentials is None or credentials.scheme.lower() != "bearer":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication required",
                headers={"WWW-Authenticate": "Bearer"},
            )
        subject = decode_access_token(
            credentials.credentials,
            settings.secret_key.get_secret_value(),
        )
        if subject is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication required",
                headers={"WWW-Authenticate": "Bearer"},
            )
        user = session.scalar(select(User).where(User.id == subject, User.is_active.is_(True)))
        if user is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication required",
                headers={"WWW-Authenticate": "Bearer"},
            )
        owner_id = user.id

    try:
        return get_project_for_ingestion(str(project_id), owner_id, api_key, session)
    except ProjectNotFound as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found",
        ) from error
    except ProjectAccessDenied as error:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid project credentials",
            headers={"WWW-Authenticate": "Bearer"},
        ) from error


IngestionProject = Annotated[Project, Depends(get_ingestion_project)]

from datetime import timedelta

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.core.security import (
    DUMMY_PASSWORD_HASH,
    create_access_token,
    hash_password,
    password_hash,
)
from app.models import User
from app.schemas.auth import LoginRequest, RegisterRequest, UserResponse


class EmailAlreadyRegistered(Exception):
    pass


class InvalidCredentials(Exception):
    pass


def register_user(payload: RegisterRequest, session: Session) -> User:
    email = str(payload.email).lower()
    existing_user = session.scalar(select(User.id).where(User.email == email))
    if existing_user is not None:
        raise EmailAlreadyRegistered

    user = User(
        email=email,
        display_name=payload.display_name,
        hashed_password=hash_password(payload.password.get_secret_value()),
    )
    session.add(user)

    try:
        session.commit()
    except IntegrityError as error:
        session.rollback()
        if session.scalar(select(User.id).where(User.email == email)) is not None:
            raise EmailAlreadyRegistered from error
        raise

    session.refresh(user)
    return user


def authenticate_user(payload: LoginRequest, session: Session) -> User:
    email = str(payload.email).lower()
    user = session.scalar(select(User).where(User.email == email))
    password = payload.password.get_secret_value()
    encoded_password = user.hashed_password if user is not None else DUMMY_PASSWORD_HASH
    password_is_valid = password_hash.verify(password, encoded_password)

    if user is None or not user.is_active or not password_is_valid:
        raise InvalidCredentials
    return user


def issue_access_token(user: User, settings: Settings) -> str:
    lifetime = timedelta(minutes=settings.access_token_expire_minutes)
    return create_access_token(
        subject=user.id,
        secret_key=settings.secret_key.get_secret_value(),
        expires_delta=lifetime,
    )


def serialize_user(user: User) -> UserResponse:
    return UserResponse.model_validate(user)

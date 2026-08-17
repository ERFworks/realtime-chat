import logging
import uuid

from jose import JWTError
from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError

from app.schemas.auth import UserOut, TokenOut
from app.services.unit_of_work import AbstractUnitOfWork
from app.services.token_store import AbstractTokenStore, RotationOutcome
from app.utils.normalization import normalize
from app.core.config import settings
from app.core.security import (
    hash_password,
    verify_password,
    create_access_token,
    create_refresh_token,
    decode_token
)

logger = logging.getLogger(__name__)


def _credentials_exception() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid refresh token",
        headers={"WWW-Authenticate": "Bearer"},
    )


def _refresh_ttl_seconds() -> int:
    return settings.REFRESH_TOKEN_EXPIRE_DAYS * 86400


async def register_user(
    uow: AbstractUnitOfWork,
    username: str,
    password: str,
    first_name: str,
    last_name: str | None = None
) -> UserOut:

    username = normalize(username)
    async with uow:
        if await uow.users.get_user_by_username(username) is not None:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Username already exists")

        try:
            user = await uow.users.create_user(
                username=username,
                password_hash=hash_password(password),
                first_name=first_name,
                last_name=last_name
            )
            await uow.profiles.create_profile(user.user_id)
            await uow.commit()

        except IntegrityError:
            await uow.rollback()
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Username already exists") from None

        return UserOut(
            user_id=user.user_id,
            username=user.username,
            first_name=user.first_name,
            last_name=user.last_name,
            profile_pic=None
        )


async def _issue_tokens(token_store: AbstractTokenStore, user_id: int) -> TokenOut:
    payload = {"sub": str(user_id)}
    family_id = uuid.uuid4().hex
    refresh_token = create_refresh_token(payload, family_id=family_id)
    await token_store.store_refresh_token(
        user_id, refresh_token, family_id, _refresh_ttl_seconds()
    )
    return TokenOut(
        access_token=create_access_token(payload),
        refresh_token=refresh_token
    )


async def authenticate_user(
    uow: AbstractUnitOfWork,
    token_store: AbstractTokenStore,
    username: str,
    password: str
) -> TokenOut:
    username = normalize(username)
    async with uow:
        user = await uow.users.get_user_by_username(username)
        if user is None or not verify_password(password, user.password_hash):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid username or password"
            )
        return await _issue_tokens(token_store, user.user_id)


def _decode_refresh_token(refresh_token: str) -> tuple[int, str]:
    """Validate a refresh JWT and return (user_id, family_id)."""
    credentials_exc = _credentials_exception()

    try:
        payload = decode_token(refresh_token)

    except JWTError:
        raise credentials_exc from None

    if payload.get("type") != "refresh":
        raise credentials_exc

    family_id = payload.get("fid")
    if not family_id:
        raise credentials_exc

    sub = payload.get("sub")
    if sub is None:
        raise credentials_exc

    try:
        user_id = int(sub)

    except (TypeError, ValueError):
        raise credentials_exc from None

    return user_id, family_id


async def refresh_tokens(
    uow: AbstractUnitOfWork,
    token_store: AbstractTokenStore,
    refresh_token: str
) -> TokenOut:
    user_id, family_id = _decode_refresh_token(refresh_token)

    async with uow:
        if await uow.users.get_user_by_id(user_id) is None:
            raise _credentials_exception()

    payload = {"sub": str(user_id)}
    new_refresh_token = create_refresh_token(payload, family_id=family_id)
    outcome = await token_store.rotate_refresh_token(
        user_id, refresh_token, new_refresh_token, family_id, _refresh_ttl_seconds()
    )

    if outcome is RotationOutcome.REUSE_DETECTED:
        logger.warning("Refresh token reuse detected, revoking family %s for user %s", family_id, user_id)
        raise _credentials_exception()

    if outcome is not RotationOutcome.ROTATED:
        raise _credentials_exception()

    return TokenOut(
        access_token=create_access_token(payload),
        refresh_token=new_refresh_token
    )


async def logout(
    token_store: AbstractTokenStore,
    user_id: int,
    access_token: str,
    refresh_token: str
) -> None:
    token_user_id, family_id = _decode_refresh_token(refresh_token)

    if token_user_id != user_id:
        raise _credentials_exception()

    await token_store.revoke_refresh_token(
        user_id, refresh_token, family_id, _refresh_ttl_seconds()
    )
    await token_store.revoke_access_token(access_token)

from jose import JWTError
from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError

from app.schemas.auth import UserOut, TokenOut
from app.services.unit_of_work import AbstractUnitOfWork
from app.utils.normalization import normalize
from app.core.security import(
    hash_password,
    verify_password,
    create_access_token,
    create_refresh_token,
    decode_token
) 


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


def _issue_tokens(user_id: int) -> TokenOut:
    payload = {"sub": str(user_id)}
    return TokenOut(
        access_token=create_access_token(payload),
        refresh_token=create_refresh_token(payload)
    )


async def authenticate_user(uow: AbstractUnitOfWork, username: str, password: str) -> TokenOut:
    username = normalize(username)
    async with uow:
        user = await uow.users.get_user_by_username(username)
        if user is None or not verify_password(password, user.password_hash):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid username or password"
            )
        return _issue_tokens(user.user_id)


async def refresh_tokens(uow: AbstractUnitOfWork, refresh_token: str) -> TokenOut:
    credentials_exc = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid refresh token",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = decode_token(refresh_token)

    except JWTError:
        raise credentials_exc from None

    if payload.get("type") != "refresh":
        raise credentials_exc

    sub = payload.get("sub")
    if sub is None:
        raise credentials_exc

    try:
        user_id = int(sub)

    except (TypeError, ValueError):
        raise credentials_exc from None

    async with uow:
        if await uow.users.get_user_by_id(user_id) is None:
            raise credentials_exc

    return _issue_tokens(user_id)

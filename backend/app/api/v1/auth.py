from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.auth import RegisterIn, TokenOut, UserOut, RefreshIn
from app.db.session import get_db
from app.models.user import User
from app.api.deps import get_current_user, get_profile_repo
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.exc import IntegrityError
from app.utils.normalization import normalize
from jose import JWTError
from app.repositories.profile import AbstractProfileRepository
from app.core.security import (
    hash_password,
    verify_password,
    create_access_token,
    create_refresh_token,
    decode_token
)


router = APIRouter(tags=["authentication"])

@router.post("/register", response_model=UserOut, status_code = status.HTTP_201_CREATED)
async def register (
    user: RegisterIn, 
    profile_repo: AbstractProfileRepository = Depends(get_profile_repo),
    db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.username == user.username))

    if result.scalar_one_or_none():
        raise HTTPException(
            status_code = status.HTTP_409_CONFLICT,
            detail = f"username already exists"
        )

    new_user = User(
        username = user.username,
        password_hash = hash_password(user.password),
        first_name = user.first_name,
        last_name = user.last_name
    )

    db.add(new_user)

    try:
        await db.flush()
        await profile_repo.create_profile(new_user.user_id)
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Username already exists"
        )from None


    await db.refresh(new_user)
    return new_user


@router.post("/login", response_model=TokenOut, status_code= status.HTTP_200_OK)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db)
):

    username = normalize(form_data.username)
    result = await db.execute(select(User).where(User.username == username))

    user = result.scalar_one_or_none()

    if not user or not verify_password(form_data.password, user.password_hash):
        raise HTTPException(
            status_code = status.HTTP_401_UNAUTHORIZED,
            detail = "Invalid username or password"
        )
    payload = {"sub": str(user.user_id)}
    return TokenOut(
        access_token = create_access_token(payload),
        refresh_token = create_refresh_token(payload)
    )

@router.post("/refresh", response_model=TokenOut, status_code=status.HTTP_200_OK)
async def refresh_access_token(payload_in: RefreshIn, db: AsyncSession = Depends(get_db)):

    credentials_exc = HTTPException(
        status_code = status.HTTP_401_UNAUTHORIZED,
        detail = "Invalid refresh token",
        headers={"WWW-Authenticate": "Bearer"}
    )
    try:
        payload = decode_token(payload_in.refresh_token)
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

    result = await db.execute(select(User).where(User.user_id == user_id))
    if result.scalar_one_or_none() is None:
        raise credentials_exc

    new_payload = {"sub": str(sub)}
    return TokenOut(
        access_token=create_access_token(new_payload),
        refresh_token=create_refresh_token(new_payload)
    )


@router.get("/me", response_model=UserOut)
async def me(current_user: User = Depends(get_current_user)):
    return current_user
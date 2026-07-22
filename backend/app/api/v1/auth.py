from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.schemas.auth import RegisterIn, LoginIn, TokenOut, UserOut
from app.db.session import get_db
from app.models.user import User
from app.core.security import (
    hash_password,
    verify_password,
    create_access_token,
    create_refresh_token
)


router = APIRouter(tags=["authentication"])

@router.post("/register", response_model=UserOut, status_code = status.HTTP_201_CREATED)
async def register (user: RegisterIn, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.username == user.username))

    if result.scalar_one_or_none():
        raise HTTPException(
            status_code = status.HTTP_400_BAD_REQUEST,
            detail = f"username already exists"
        )

    new_user = User(
        username = user.username,
        password_hash = hash_password(user.password),
        first_name = user.first_name,
        last_name = user.last_name
    )

    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)
    return new_user


@router.post("/login", response_model=TokenOut)
async def login(credentials: LoginIn, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.username == credentials.username))

    user = result.scalar_one_or_none()

    if not user or not verify_password(credentials.password, user.password_hash):
        raise HTTPException(
            status_code = status.HTTP_401_UNAUTHORIZED,
            detail = "Invalid username or password"
        )
    payload = {"sub": str(user.user_id)}
    return TokenOut(
        access_token = create_access_token(payload),
        refresh_token = create_refresh_token(payload)
    )


@router.get("/me", response_model=UserOut)
async def me(current_user: User = Depends(get_current_user)):
    return current_user
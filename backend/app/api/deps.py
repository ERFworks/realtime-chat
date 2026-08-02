from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.core.security import decode_token
from app.models.user import User
from app.repositories.user import AbstractUserRepository, SqlAlchemyUserRepository
from app.repositories.friend import AbstractFriendRepository, SqlAlchemyFriendRepository
from app.repositories.profile import AbstractProfileRepository, SqlAlchemyProfileRepository

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")

async def get_current_user(
        token: str = Depends(oauth2_scheme),
        db: AsyncSession = Depends(get_db)
) -> User:
    credentials_exc = HTTPException(
        status_code = status.HTTP_401_UNAUTHORIZED,
        detail = "Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = decode_token(token)
        if payload.get("type") != "access":
            raise credentials_exc

        user_id = int(payload.get("sub"))
        if user_id is None:
            raise credentials_exc

    except (JWTError, KeyError, TypeError, ValueError):
        raise credentials_exc from None

    result = await db.execute(select(User).where(User.user_id == user_id))
    user = result.scalar_one_or_none()

    if user is None:
        raise credentials_exc

    return user

async def get_friend_repo(db: AsyncSession = Depends(get_db)) -> AbstractFriendRepository:
    return SqlAlchemyFriendRepository(db)

async def get_user_repo(db: AsyncSession = Depends(get_db)) -> AbstractUserRepository:
    return SqlAlchemyUserRepository(db)

async def get_profile_repo(db: AsyncSession = Depends(get_db)) -> AbstractProfileRepository:
    return SqlAlchemyProfileRepository(db)
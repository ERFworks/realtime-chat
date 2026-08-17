from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from functools import lru_cache

from app.db.session import get_db
from app.core.security import decode_token
from app.models.user import User
from app.services.unit_of_work import AbstractUnitOfWork, SqlAlchemyUnitOfWork
from app.adapters.file_storage import AbstractFileStorage, MinioFileStorage
from app.services.token_store import AbstractTokenStore, RedisTokenStore

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")

@lru_cache
def get_token_store() -> AbstractTokenStore:
    return RedisTokenStore()

async def get_current_user(
        token: str = Depends(oauth2_scheme),
        db: AsyncSession = Depends(get_db),
        token_store: AbstractTokenStore = Depends(get_token_store),
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

        sub = payload.get("sub")
        if sub is None:
            raise credentials_exc
        user_id = int(sub)

    except (JWTError, KeyError, TypeError, ValueError):
        raise credentials_exc from None

    if await token_store.is_access_token_revoked(token):
        raise credentials_exc

    result = await db.execute(select(User).where(User.user_id == user_id))
    user = result.scalar_one_or_none()

    if user is None:
        raise credentials_exc

    return user

async def get_uow(db: AsyncSession = Depends(get_db)) -> AbstractUnitOfWork:
    return SqlAlchemyUnitOfWork(db)
    
@lru_cache
def get_file_storage() -> AbstractFileStorage:
    return MinioFileStorage()
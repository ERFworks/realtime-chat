from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Protocol

from app.models.user import User
from app.models.profile import Profile

class AbstractUserRepository(Protocol):
    async def get_user_by_id(self, user_id: int) -> User | None: ...
    async def search_users(self, query: str, exclude_user_id: int,limit: int = 20) -> list[tuple[User, str|None]]: ...
    async def get_user_by_username(self, username: str) -> User | None: ...
    async def create_user(self, username:str, password_hash: str, first_name: str, last_name:str | None) -> User: ...



class SqlAlchemyUserRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        

    async def get_user_by_id(self, user_id: int) -> User | None:
        result = await self.session.execute(select(User).where(User.user_id == user_id))
        return result.scalar_one_or_none()


    async def search_users(
        self,
        query: str,
        exclude_user_id: int,
        limit: int = 20,
    ) -> list[tuple[User, str|None]]:
        stmt = (
            select(User, Profile.profile_pic)
            .join(Profile, Profile.user_id == User.user_id, isouter=True)
            .where(
                User.username.ilike(f"%{query}%"),
                User.user_id != exclude_user_id
            )
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return list((row[0], row[1]) for row in result.all())


    async def get_user_by_username(self, username: str) -> User | None:
        result = await self.session.execute(
            select(User)
            .where(
                User.username == username
            )
        )
        return result.scalar_one_or_none()


    async def create_user(self, username, password_hash, first_name, last_name) -> User:
        user = User(
            username = username,
            password_hash = password_hash,
            first_name = first_name,
            last_name = last_name
        )
        self.session.add(user)
        await self.session.flush()
        return user
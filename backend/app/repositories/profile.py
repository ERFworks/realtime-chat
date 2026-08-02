from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Protocol

from app.models.profile import Profile


class AbstractProfileRepository(Protocol):
    async def create_profile(self, user_id: int) -> Profile: ...
    async def get_profile_by_user_id(self, user_id: int) -> Profile | None: ...


class SqlAlchemyProfileRepository:

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_profile(self, user_id: int) -> Profile:
        profile = Profile(
            user_id = user_id,
            biography = None,
            profile_pic = None,
        )

        self.session.add(profile)
        await self.session.flush()

        return profile


    async def get_profile_by_user_id(self, user_id: int) -> Profile | None:
        stmt = select(Profile).where(Profile.user_id == user_id)

        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()


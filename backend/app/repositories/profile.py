from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.profile import Profile

async def create_profile(db: AsyncSession, user_id: int) -> Profile:
    profile = Profile(
        user_id = user_id,
        biography = None,
        profile_pic = None,
    )

    db.add(profile)
    await db.flush()

    return profile


async def get_profile_by_user_id(db: AsyncSession, user_id: int) -> Profile | None:
    stmt = select(Profile).where(Profile.user_id == user_id)

    result = await db.execute(stmt)
    return result.scalar_one_or_none()


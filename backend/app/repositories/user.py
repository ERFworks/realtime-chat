from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.user import User
from app.models.profile import Profile

async def get_user_by_id(db: AsyncSession, user_id: int) -> User | None:
    result = await db.execute(select(User).where(User.user_id == user_id))
    return result.scalar_one_or_none()

async def search_users(
    db: AsyncSession,
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
    result = await db.execute(stmt)
    return list((row[0], row[1]) for row in result.all())
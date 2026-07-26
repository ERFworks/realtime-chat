from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_, and_

from app.models.user import User
from app.models.friendship import Friendship, FriendshipStatus

async def create_friend_request(
    db: AsyncSession, 
    requester_id: int, 
    addressee_id: int
) -> Friendship:

    friendship = Friendship(
        requester_id = requester_id,
        addressee_id = addressee_id,
    )

    db.add(friendship)
    await db.flush()

    return friendship

async def get_friendship_between(
    db: AsyncSession,
    user_a: int,
    user_b: int
) -> Friendship | None:

    stmt = select(Friendship).where(
        or_(
            and_(Friendship.requester_id == user_a, Friendship.addressee_id == user_b),
            and_(Friendship.requester_id == user_b, Friendship.addressee_id == user_a)
        )

    )

    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def list_friends(db: AsyncSession, user_id: int) -> list[User]:

    stmt = (
        select(User)
        .join(
            Friendship,
            or_(
                and_(
                    Friendship.requester_id == user_id,
                    Friendship.addressee_id == User.user_id
                ),
                and_(
                    Friendship.addressee_id == user_id,
                    Friendship.requester_id == User.user_id
                )
            )
        ).where(Friendship.status == FriendshipStatus.ACCEPTED)
    )

    result = await db.execute(stmt)
    return list(result.scalars().all())



async def list_pending_requests(db: AsyncSession, user_id: int):

    stmt = select(Friendship).where(
        Friendship.addressee_id == user_id,
        Friendship.status == FriendshipStatus.PENDING
    )

    result = await db.execute(stmt)
    return list(result.scalars().all())


async def update_friendship_status(
    db: AsyncSession, 
    friendship_id: int, 
    status: FriendshipStatus
) -> Friendship | None:

    stmt = select(Friendship).where(Friendship.friendship_id == friendship_id)
    result = await db.execute(stmt)
    friendship = result.scalar_one_or_none()

    if friendship is None:
        return None

    friendship.status = status
    await db.flush()

    return friendship


async def get_friendship_by_id(db: AsyncSession, friendship_id: int) -> Friendship | None:
    stmt = select(Friendship).where(Friendship.friendship_id == friendship_id)
    result = await db.execute(stmt)
    return result.scalar_one_or_none()
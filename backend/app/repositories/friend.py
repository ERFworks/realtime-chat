from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_, and_
from typing import Protocol

from app.models.user import User
from app.models.profile import Profile
from app.models.friendship import Friendship, FriendshipStatus

class AbstractFriendRepository(Protocol):
    async def create_friend_request(self, requester_id: int, addressee_id: int) -> Friendship: ...
    async def get_friendship_between(self, user_a: int, user_b: int) -> Friendship | None: ...
    async def get_friendship_by_id(self, friendship_id: int) -> Friendship | None: ...
    async def update_friendship_status(self, friendship_id: int, status: FriendshipStatus) -> Friendship | None: ...
    async def list_friends(self, user_id: int) -> list[tuple["User", str | None]]: ...
    async def list_pending_requests(self, user_id: int) -> list[Friendship]: ...


class SqlAlchemyFriendRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_friend_request(
        self,
        requester_id: int, 
        addressee_id: int
    ) -> Friendship:

        friendship = Friendship(
            requester_id = requester_id,
            addressee_id = addressee_id,
        )

        self.session.add(friendship)
        await self.session.flush()

        return friendship


    async def get_friendship_between(
        self,
        user_a: int,
        user_b: int
    ) -> Friendship | None:

        stmt = select(Friendship).where(
            or_(
                and_(Friendship.requester_id == user_a, Friendship.addressee_id == user_b),
                and_(Friendship.requester_id == user_b, Friendship.addressee_id == user_a)
            )

        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_friendship_by_id(self, friendship_id: int) -> Friendship | None:
        stmt = select(Friendship).where(Friendship.friendship_id == friendship_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()


    async def list_friends(self, user_id: int) -> list[tuple[User, str | None]]:
        stmt = (
            select(User, Profile.profile_pic)         
            .join(
                Friendship,
                or_(
                    and_(Friendship.requester_id == user_id, Friendship.addressee_id == User.user_id),
                    and_(Friendship.addressee_id == user_id, Friendship.requester_id == User.user_id),
                ),
            )
            .join(Profile, Profile.user_id == User.user_id, isouter=True)     
            .where(Friendship.status == FriendshipStatus.ACCEPTED)
        )
        
        result = await self.session.execute(stmt)
        return [(row[0], row[1]) for row in result.all()]


    async def list_pending_requests(self, user_id: int):

        stmt = select(Friendship).where(
            Friendship.addressee_id == user_id,
            Friendship.status == FriendshipStatus.PENDING
        )

        result = await self.session.execute(stmt)
        return list(result.scalars().all())


    async def update_friendship_status(
        self, 
        friendship_id: int, 
        status: FriendshipStatus
    ) -> Friendship | None:

        stmt = select(Friendship).where(Friendship.friendship_id == friendship_id)
        result = await self.session.execute(stmt)
        friendship = result.scalar_one_or_none()

        if friendship is None:
            return None

        friendship.status = status
        await self.session.flush()

        return friendship
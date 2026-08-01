from app.models.friendship import Friendship, FriendshipStatus
from app.models.user import User

class FakeFriendRepository:
    def __init__(self, friendships=None, users: dict[int, User] | None = None):
        self._friendships = list(friendships or [])
        self._users = users or {} 


    async def create_friend_request(self, requester_id: int, addressee_id: int) -> Friendship:

        friendship = Friendship(
            friendship_id = len(self._friendships) + 1,
            requester_id = requester_id,
            addressee_id = addressee_id,
            status=FriendshipStatus.PENDING
        )

        self._friendships.append(friendship)
        return friendship

    async def get_friendship_between(self, user_a, user_b):
        return next((f for f in self._friendships
                    if {f.requester_id, f.addressee_id} == {user_a, user_b}), None
        )

    async def get_friendship_by_id(self, friendship_id: int) -> Friendship | None:
        return next((f for f in self._friendships
                    if f.friendship_id == friendship_id), None
        )

    async def list_friends(self, user_id: int) -> list[User]:
        result: list[User] = []
        for f in self._friendships:
            if f.status != FriendshipStatus.ACCEPTED:
                continue
            if f.requester_id == user_id:
                other_id = f.addressee_id
            elif f.addressee_id == user_id:
                other_id = f.requester_id
            else:
                continue
            result.append(self._users[other_id])
        return result
    

    async def list_pending_requests(self, user_id: int):
        return [f for f in self._friendships
                    if (f.addressee_id == user_id) and f.status == FriendshipStatus.PENDING]

    async def update_friendship_status(self, friendship_id: int, status: FriendshipStatus) -> Friendship | None:
        friendship = await self.get_friendship_by_id(friendship_id)
        if friendship is None:
            return None
        

        friendship.status = status
        return friendship 


class FakeUserRepository:
    def __init__(self, users: dict[int, User] | None = None):
        self._users = users or {}

    async def get_user_by_id(self, user_id: int) ->  User | None:
        return self._users.get(user_id)

    async def search_users(self, query: str, exclude_user_id: int, limit: int = 20):
        return []
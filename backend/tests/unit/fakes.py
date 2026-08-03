from app.models.friendship import Friendship, FriendshipStatus
from app.models.user import User
from app.models.profile import Profile
from app.models.message import Message

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


class FakeProfileRepository:
    def __init__(self, profiles: dict[int, Profile] | None = None):
        self._profiles = profiles or {}

    async def create_profile(self, user_id: int) -> Profile:
        profile = Profile(
            user_id = len(self._profiles) + 1,
            biography = None,
            profile_pic = None,
        )
        self._profiles[user_id] = profile
        return profile

    async def get_profile_by_user_id(self, user_id: int) -> Profile | None:
        return self._profiles.get(user_id)


class FakeSession:
    async def commit(self):
        pass

    async def refresh(self, obj):
        pass



class FakeFileStorage:
    def __init__(self, url_prefix: str = "https://cdn.test/"):
        self.put_calls: list = []
        self.deleted: list = []
        self._prefix = url_prefix

    async def put(self, key, content, content_type) -> None:
        self.put_calls.append((key, content, content_type))


    async def delete(self, key) -> None:
        self.deleted.append(key)

    def url_for(self, key):
        return f"{self._prefix}{key}" if key else None  


class FakeUpload:
    def __init__(self, content: bytes = b"x", content_type: str = "image/png"):
        self._content = content
        self.content_type = content_type

    async def read(self) -> bytes:
        return self._content


class FakeMessageRepository:
    def __init__(
        self, 
        participants: set[tuple[int, int]] | None = None,
        messages: list[Message] | None = None
    ) -> None:
        self._participants = participants or set()
        self._messages = list(messages or [])


    async def is_participant(self, conversation_id: int, user_id: int) -> bool:
        return (conversation_id, user_id) in self._participants

        
    async def create_message(self, conversation_id: int, sender_id: int, body: str) -> Message:
        message = Message(
            message_id = len(self._messages) + 1,
            conversation_id = conversation_id,
            sender_id = sender_id,
            body = body
        )
        self._messages.append(message)
        return message


    async def list_messages(self, conversation_id: int, before_id = None, limit = 50) -> list[Message]:
        msgs = [m for m in self._messages if m.conversation_id == conversation_id]
        if before_id is not None:
            msgs = [m for m in msgs if m.message_id < before_id]

        msgs.sort(key=lambda m : m.message_id, reverse=True)
        return msgs[:limit]
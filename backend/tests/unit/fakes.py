from app.models.friendship import Friendship, FriendshipStatus
from app.models.user import User
from app.models.profile import Profile
from app.models.message import Message
from app.models.conversation import Conversation, ConversationType
from app.models.conversationparticipant import ConversationParticipant
from app.utils.time import utcnow
from app.services.unit_of_work import AbstractUnitOfWork

class FakeFriendRepository:
    def __init__(self, friendships=None, users: dict[int, User] | None = None):
        self._friendships = list(friendships or [])
        self._users = users or {} 


    async def create_friend_request(self, requester_id: int, addressee_id: int) -> Friendship:

        friendship = Friendship(
            friendship_id = len(self._friendships) + 1,
            requester_id = requester_id,
            addressee_id = addressee_id,
            status=FriendshipStatus.PENDING,
            created_at = utcnow()
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


    async def get_user_by_username(self, username: str) -> User | None:
        return next((u for u in self._users.values() if u.username == username), None)

    
    async def create_user(self, username, password_hash, first_name, last_name) -> User:
        new_id = max(self._users, default=0) + 1
        user = User(
            user_id = new_id,
            username=username,
            password_hash=password_hash,
            first_name=first_name,
            last_name=last_name
        )
        self._users[new_id] = user
        return user

    async def search_users(self, query: str, exclude_user_id: int, limit: int = 20):
        return [
            (u, None)
            for u in self._users.values()
            if u.user_id != exclude_user_id and query.lower() in u.username.lower()
        ][:limit]


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
            body = body,
            created_at = utcnow()
        )
        self._messages.append(message)
        return message


    async def list_messages(self, conversation_id: int, before_id = None, limit = 50) -> list[Message]:
        msgs = [m for m in self._messages if m.conversation_id == conversation_id]
        if before_id is not None:
            msgs = [m for m in msgs if m.message_id < before_id]

        msgs.sort(key=lambda m : m.message_id, reverse=True)
        return msgs[:limit]


class FakeConversationRepository:
    def __init__(
            self, 
            conversations: list[Conversation] | None = None, 
            participants: list[tuple[int, int]] | None = None,
            users: dict[int, User] | None = None,
            profile_pics: dict[int, str | None] | None = None
        ):
        self._conversations = list(conversations or [])
        self._participants = list(participants or [])
        self._users = users or {}
        self._profile_pics = profile_pics or {}

    
    async def get_private_conversation_id(self, user_a: int, user_b: int) -> int | None:
        convs_a = {cid for cid, uid in self._participants if uid == user_a}
        convs_b = {cid for cid, uid in self._participants if uid == user_b}
        shared = convs_a & convs_b

        for conv in self._conversations:
            if conv.conversation_id in shared and conv.conversation_type == ConversationType.PRIVATE:
                return conv.conversation_id

        return None


    async def get_conversation(self, conversation_id: int) -> Conversation | None:
        return next((c for c in self._conversations if c.conversation_id == conversation_id), None)

    
    async def create_private_conversation(self, user_ids: list[int]) -> Conversation:
        conv = Conversation(
            conversation_id = len(self._conversations) + 1,
            conversation_type = ConversationType.PRIVATE,
            created_at = utcnow(),
            updated_at = utcnow()
        )
        self._conversations.append(conv)

        for uid in user_ids:
            self._participants.append((conv.conversation_id, uid))

        return conv


    async def get_participants(self, conversation_id: int) -> list[User]:
        return [self._users[uid] for cid, uid in self._participants 
                   if cid == conversation_id and uid in self._users]


    async def get_participants_with_profiles(self, conversation_id: int) -> list[tuple[User, str | None]]:
        return [(self._users[uid], self._profile_pics.get(uid))
                for cid, uid in self._participants
                if cid == conversation_id and uid in self._users]


    async def list_user_conversations(self, user_id: int) -> list[Conversation]:
        ids = {cid for cid, uid in self._participants if uid == user_id}
        return [c for c in self._conversations if c.conversation_id in ids]



class FakeUnitOfWork(AbstractUnitOfWork):
    def __init__(self, users=None, friends=None, profiles=None, messages=None, conversations=None):
        self.users = users or FakeUserRepository()
        self.friends = friends or FakeFriendRepository()
        self.profiles = profiles or FakeProfileRepository()
        self.messages = messages or FakeMessageRepository()
        self.conversations = conversations or FakeConversationRepository()
        self.committed = False


    async def commit(self):
        self.committed = True


    async def rollback(self):
        pass
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Protocol

from app.models.conversation import ConversationType, Conversation
from app.models.conversationparticipant import ConversationParticipant
from app.models.user import User
from app.models.profile import Profile


class AbstractConversationRepository(Protocol):
    async def get_private_conversation_id(self, user_a: int, user_b: int) -> int | None: ...
    async def get_conversation(self, conversation_id: int) -> Conversation | None:...
    async def create_private_conversation(self, user_ids: list[int]) -> Conversation:...
    async def get_participants(self , conversation_id: int) -> list[User]:...
    async def get_participants_with_profiles(self, conversation_id: int) -> list[tuple[User, str|None]]: ...
    async def list_user_conversations(self , user_id: int) -> list[Conversation]:...

    
class SqlAlchemyConversationRepository:
    def __init__(self, session: AsyncSession):
        self.session = session


    async def get_private_conversation_id(
        self,
        user_a: int,
        user_b: int
    ) -> int | None:
        low, high = sorted((user_a, user_b))
        result = await self.session.execute(
            select(Conversation.conversation_id).where(
                Conversation.conversation_type == ConversationType.PRIVATE,
                Conversation.user_a_id == low,
                Conversation.user_b_id == high
            )
        )
        return result.scalar_one_or_none()



    async def get_conversation(self, conversation_id: int) -> Conversation | None:
        result = await self.session.execute(
            select(Conversation).where(Conversation.conversation_id == conversation_id)
        )
        return result.scalar_one_or_none()


    async def create_private_conversation(
        self,
        user_ids: list[int]
    ) -> Conversation:
        low, high = sorted(user_ids)
        conv = Conversation(
            conversation_type = ConversationType.PRIVATE,
            user_a_id = low,
            user_b_id = high
        )
        self.session.add(conv)
        await self.session.flush()
        self.session.add_all(
            [
                ConversationParticipant(conversation_id = conv.conversation_id, user_id= uid)
                for uid in user_ids
            ]
        )
        await self.session.flush()
        return conv


    async def get_participants(self, conversation_id: int) -> list[User]:
        result = await self.session.execute(
            select(User)
            .join(
                ConversationParticipant,
                ConversationParticipant.user_id == User.user_id
            )
            .where(ConversationParticipant.conversation_id == conversation_id)
        )
        return list(result.scalars().all())


    async def get_participants_with_profiles(
        self, 
        conversation_id: int
    ) -> list[tuple[User, str|None]]:
        result = await self.session.execute(
            select(User, Profile.profile_pic)
            .join(ConversationParticipant, ConversationParticipant.user_id == User.user_id)
            .join(Profile, Profile.user_id == User.user_id, isouter=True)
            .where(ConversationParticipant.conversation_id == conversation_id)
        )

        return [(row[0], row[1]) for row in result.all()]


    async def list_user_conversations(self, user_id: int) -> list[Conversation]:
        result = await self.session.execute(
            select(Conversation)
            .join(
                ConversationParticipant,
                ConversationParticipant.conversation_id == Conversation.conversation_id
            )
            .where(ConversationParticipant.user_id == user_id)
            .order_by(Conversation.updated_at.desc())
        )
        return list(result.scalars().all())
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Protocol

from app.models.conversationparticipant import ConversationParticipant
from app.models.message import Message


class AbstractMessageRepository(Protocol):
    async def is_participant(self, conversation_id: int, user_id: int) -> bool: ...
    async def create_message(self, conversation_id: int, sender_id: int, body: str) -> Message:...
    async def list_messages(self, conversation_id: int, before_id = None, limit = 50) -> list[Message]: ...


class SqlAlchemyMessageRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def is_participant(
        self, 
        conversation_id: int,
        user_id: int
    ) -> bool:
        stmt = select(ConversationParticipant.user_id).where(
            ConversationParticipant.conversation_id == conversation_id,
            ConversationParticipant.user_id == user_id
        )

        result = await self.session.execute(stmt)
        return result.first() is not None


    async def create_message(
        self,
        conversation_id: int,
        sender_id: int,
        body: str
    ) -> Message:
        message = Message(
            conversation_id = conversation_id,
            sender_id = sender_id,
            body = body
        )

        self.session.add(message)
        await self.session.flush()

        return message


    async def list_messages(
        self, 
        conversation_id: int, 
        before_id = None,
        limit = 50
    ) -> list[Message]:
        stmt = select(Message).where(Message.conversation_id == conversation_id)
        if before_id is not None:
            stmt = stmt.where(Message.message_id < before_id)

        stmt = stmt.order_by(Message.message_id.desc()).limit(limit)

        result = await self.session.execute(stmt)
        return list(result.scalars().all())



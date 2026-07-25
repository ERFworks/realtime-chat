from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.conversationparticipant import ConversationParticipant
from app.models.message import Message

async def is_participant(
    db: AsyncSession, 
    conversation_id: int,
    user_id: int
) -> bool:
    stmt = select(ConversationParticipant.user_id).where(
        ConversationParticipant.conversation_id == conversation_id,
        ConversationParticipant.user_id == user_id
    )

    result = await db.execute(stmt)
    return result.first() is not None



async def create_message(
    db: AsyncSession,
    conversation_id: int,
    sender_id: int,
    body: str
) -> Message:
    message = Message(
        conversation_id = conversation_id,
        sender_id = sender_id,
        body = body
    )

    db.add(message)
    await db.flush()

    return message


async def list_messages(
    db: AsyncSession, 
    conversation_id: int, 
    before_id = None,
    limit = 50
) -> list[Message]:
    stmt = select(Message).where(Message.conversation_id == conversation_id)
    if before_id is not None:
        stmt = stmt.where(Message.message_id < before_id)

    stmt = stmt.order_by(Message.message_id.desc()).limit(limit)

    result = await db.execute(stmt)
    return list(result.scalars().all())



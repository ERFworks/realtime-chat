from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.conversation import ConversationType, Conversation
from app.models.conversationparticipant import ConversationParticipant
from app.models.user import User

async def get_private_conversation_id(
    db: AsyncSession,
    user_a: int,
    user_b: int
) -> int | None:
    stmt = (
        select(ConversationParticipant.conversation_id)
        .join(
            Conversation,
            Conversation.conversation_id == ConversationParticipant.conversation_id
        )
        .where(
            Conversation.conversation_type == ConversationType.PRIVATE,
            ConversationParticipant.user_id.in_([user_a, user_b]),
        )
        .group_by(ConversationParticipant.conversation_id)
        .having(func.count(func.distinct(ConversationParticipant.user_id)) == 2)
    )
    result = await db.execute(stmt)
    return result.scalars().first()


async def get_conversation(db: AsyncSession, conversation_id: int) -> Conversation | None:
    result = await db.execute(
        select(Conversation).where(Conversation.conversation_id == conversation_id)
    )
    return result.scalar_one_or_none()


async def create_private_conversation(
    db: AsyncSession,
    user_ids: list[int]
) -> Conversation:
    conv = Conversation(conversation_type = ConversationType.PRIVATE)
    db.add(conv)
    await db.flush()
    db.add_all(
        [
            ConversationParticipant(conversation_id = conv.conversation_id, user_id= uid)
            for uid in user_ids
        ]
    )
    await db.flush()
    return conv


async def get_participants(db: AsyncSession, conversation_id: int) -> list[User]:
    result = await db.execute(
        select(User)
        .join(
            ConversationParticipant,
            ConversationParticipant.user_id == User.user_id
        )
        .where(ConversationParticipant.conversation_id == conversation_id)
    )
    return list(result.scalars().all())


async def list_user_conversations(db: AsyncSession, user_id: int) -> list[Conversation]:
    result = await db.execute(
        select(Conversation)
        .join(
            ConversationParticipant,
            ConversationParticipant.conversation_id == Conversation.conversation_id
        )
        .where(ConversationParticipant.user_id == user_id)
        .order_by(Conversation.updated_at.desc())
    )
    return list(result.scalars().all())
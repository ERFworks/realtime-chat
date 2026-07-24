from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.conversation import Conversation
from app.repositories import conversation as conv_repo
from app.repositories import user as user_repo
from app.schemas.conversation import ConversationOut, ParticipantOut


def _to_out(conv: Conversation, participants) -> ConversationOut:
    return ConversationOut(
        conversation_id = conv.conversation_id,
        conversation_type = conv.conversation_type,
        created_at = conv.created_at,
        updated_at = conv.updated_at,
        participants = [ParticipantOut.model_validate(u) for u in participants]
    )


async def get_or_create_private_conversation(
    db: AsyncSession,
    current_user_id: int,
    other_user_id: int
) -> ConversationOut:

    if current_user_id == other_user_id:
        raise HTTPException(
            status_code = status.HTTP_400_BAD_REQUEST,
            detail = "Cannot create a conversation with yourself"
        ) 

    if not await user_repo.get_user_by_id(db, other_user_id):
        raise HTTPException(
            status_code = status.HTTP_404_NOT_FOUND,
            detail = "User not found"
        )

    exiting_id = await conv_repo.get_private_conversation_id(
        db, 
        current_user_id, 
        other_user_id
    )

    if exiting_id is not None:
        conv = await conv_repo.get_conversation(db, exiting_id)
        participants = await conv_repo.get_participants(db, exiting_id)
        return _to_out(conv, participants)

    conv = await conv_repo.create_private_conversation(
        db, [current_user_id, other_user_id]
    )
    await db.commit()
    await db.refresh(conv)
    participants = await conv_repo.get_participants(db, conv.conversation_id)
    return _to_out(conv, participants)

async def list_conversations(db: AsyncSession, user_id: int) -> list[ConversationOut]:
    conversations = await conv_repo.list_user_conversations(db, user_id)
    result = []
    for conv in conversations:
        participants = await conv_repo.get_participants(db, conv.conversation_id)
        result.append(_to_out(conv, participants))

    return result

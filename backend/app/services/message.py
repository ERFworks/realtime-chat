from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.message import MessageOut
from app.repositories.message import AbstractMessageRepository
from app.repositories import conversation as conv_repo
from app.utils.time import utcnow

async def send_message(
    db: AsyncSession,
    msg_repo: AbstractMessageRepository, 
    conversation_id: int, 
    sender_id: int, 
    body: str
) -> MessageOut:
    if not await msg_repo.is_participant(conversation_id, sender_id):
        raise HTTPException(
            status_code = status.HTTP_403_FORBIDDEN,
            detail = "Not a participant"
        )

    msg = await msg_repo.create_message(conversation_id, sender_id, body)
    conv = await conv_repo.get_conversation(db, conversation_id)
    conv.updated_at = utcnow()
    await db.commit()
    await db.refresh(msg)

    return MessageOut.model_validate(msg)


async def get_messages(
    msg_repo: AbstractMessageRepository,
    conversation_id: int,
    user_id: int,
    before_id: int | None = None,
    limit: int = 50
) -> list[MessageOut]:

    if not await msg_repo.is_participant(conversation_id, user_id):
        raise HTTPException(
            status_code = status.HTTP_403_FORBIDDEN,
            detail = "Not a participant"
        )

    msgs = await msg_repo.list_messages(conversation_id, before_id, limit=limit)

    return [MessageOut.model_validate(m) for m in msgs]
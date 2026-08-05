from fastapi import HTTPException, status

from app.schemas.message import MessageOut
from app.services.unit_of_work import AbstractUnitOfWork
from app.utils.time import utcnow


async def send_message(
    uow: AbstractUnitOfWork,
    conversation_id: int, 
    sender_id: int, 
    body: str,
) -> MessageOut:
    async with uow:
        if not await uow.messages.is_participant(conversation_id, sender_id):
            raise HTTPException(
                status_code = status.HTTP_403_FORBIDDEN,
                detail = "Not a participant"
            )

        msg = await uow.messages.create_message(conversation_id, sender_id, body)
        conv = await uow.conversations.get_conversation(conversation_id)
        conv.updated_at = utcnow()
        await uow.commit()

        return MessageOut.model_validate(msg)


async def get_messages(
    uow: AbstractUnitOfWork,
    conversation_id: int,
    user_id: int,
    before_id: int | None = None,
    limit: int = 50
) -> list[MessageOut]:
    
    async with uow:
        if not await uow.messages.is_participant(conversation_id, user_id):
            raise HTTPException(
                status_code = status.HTTP_403_FORBIDDEN,
                detail = "Not a participant"
            )

        msgs = await uow.messages.list_messages(conversation_id, before_id, limit=limit)

        return [MessageOut.model_validate(m) for m in msgs]
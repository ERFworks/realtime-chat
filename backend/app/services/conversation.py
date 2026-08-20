from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError

from app.adapters.file_storage import AbstractFileStorage
from app.models.conversation import Conversation
from app.models.user import User
from app.schemas.conversation import ConversationOut, ParticipantOut
from app.services.unit_of_work import AbstractUnitOfWork


def _to_participant_out(user: User, profile_pic_key: str | None, storage: AbstractFileStorage) -> ParticipantOut:
    return ParticipantOut(
        user_id=user.user_id,
        username=user.username,
        first_name=user.first_name,
        last_name=user.last_name,
        profile_pic=storage.url_for(profile_pic_key)
    )


def _to_out(conv: Conversation, participants, storage: AbstractFileStorage) -> ConversationOut:
    return ConversationOut(
        conversation_id = conv.conversation_id,
        conversation_type = conv.conversation_type,
        created_at = conv.created_at,
        updated_at = conv.updated_at,
        participants = [_to_participant_out(user, key, storage) for user, key in participants]
    )


async def get_or_create_private_conversation(
    current_user_id: int,
    other_user_id: int,
    uow: AbstractUnitOfWork,
    storage: AbstractFileStorage
) -> ConversationOut:

    if current_user_id == other_user_id:
        raise HTTPException(
            status_code = status.HTTP_400_BAD_REQUEST,
            detail = "Cannot create a conversation with yourself"
        ) 
    
    async with uow:
        if not await uow.users.get_user_by_id(other_user_id):
            raise HTTPException(
                status_code = status.HTTP_404_NOT_FOUND,
                detail = "User not found"
            )

        exiting_id = await uow.conversations.get_private_conversation_id( 
            current_user_id, 
            other_user_id
        )

        if exiting_id is not None:
            conv = await uow.conversations.get_conversation(exiting_id)
            participants = await uow.conversations.get_participants_with_profiles(exiting_id) 
            return _to_out(conv, participants, storage)

        try:
            async with uow.savepoint():
                conv = await uow.conversations.create_private_conversation([current_user_id, other_user_id])
        except IntegrityError:
            existing_id = await uow.conversations.get_private_conversation_id(current_user_id, other_user_id)
            if existing_id is None:
                raise

            conv = await uow.conversations.get_conversation(existing_id)
            participants = await uow.conversations.get_participants_with_profiles(existing_id)
            return _to_out(conv, participants, storage)

        await uow.commit()
        participants = await uow.conversations.get_participants_with_profiles(conv.conversation_id)
        return _to_out(conv, participants, storage)


async def list_conversations(
    user_id: int,
    uow: AbstractUnitOfWork,
    storage: AbstractFileStorage
) -> list[ConversationOut]:
    async with uow:
        conversations = await uow.conversations.list_user_conversations(user_id)
        result = []
        for conv in conversations:
            participants = await uow.conversations.get_participants_with_profiles(conv.conversation_id)
            result.append(_to_out(conv, participants, storage))

        return result

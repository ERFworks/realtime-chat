import pytest
from fastapi import HTTPException

from app.models.conversation import Conversation, ConversationType
from app.models.message import Message
from app.services.message import get_messages, send_message
from app.utils.time import utcnow
from tests.unit.fakes import (
    FakeConversationRepository,
    FakeMessageRepository,
    FakeUnitOfWork,
)


def make_message(message_id=1, conversation_id=1, sender_id=1, body="salam") -> Message:
    return Message(
        message_id = message_id,
        conversation_id = conversation_id,
        sender_id = sender_id,
        body = body,
        created_at = utcnow()
    )

async def test_reject_non_participant():
    uow = FakeUnitOfWork()

    with pytest.raises(HTTPException) as exc:
        await send_message(uow, conversation_id=1, sender_id=1, body="salam")

    assert exc.value.status_code == 403
    assert uow.committed is False


async def test_get_messages_rejects_non_participant():
    uow = FakeUnitOfWork()

    with pytest.raises(HTTPException) as exc:
        await get_messages(uow, conversation_id=1, user_id=1)

    assert exc.value.status_code == 403
    assert uow.committed is False


async def test_get_messages_returns_messages_for_participant():
    uow = FakeUnitOfWork()
    uow.messages = FakeMessageRepository(
        participants={(1, 1)}, 
        messages=[
            make_message(message_id=1, body="hi"),
            make_message(message_id=2, sender_id=2, body="hello")
        ])
    
    result = await get_messages(uow, conversation_id=1, user_id=1)
    assert [m.message_id for m in result] == [2, 1]
    assert result[0].body == "hello"
    assert uow.committed is False


async def test_send_message_persists_and_commits():
    uow = FakeUnitOfWork()
    uow.messages = FakeMessageRepository(participants={(1, 1)})
    uow.conversations = FakeConversationRepository(
        conversations=[
            Conversation(
                conversation_id=1,
                conversation_type=ConversationType.PRIVATE,
                created_at=utcnow(),
                updated_at = utcnow()
            )
        ]
    )
    result = await send_message(uow, conversation_id=1, sender_id=1, body="salam")
    assert result.body == "salam"
    assert uow.committed is True
import pytest
from fastapi import HTTPException

from app.models.message import Message
from app.models.conversation import Conversation, ConversationType
from app.models.conversationparticipant import ConversationParticipant
from app.services.message import send_message, get_messages
from tests.unit.fakes import FakeMessageRepository, FakeSession, FakeConversationRepository
from app.utils.time import utcnow


def make_message(message_id=1, conversation_id=1, sender_id=1, body="salam") -> Message:
    return Message(
        message_id = message_id,
        conversation_id = conversation_id,
        sender_id = sender_id,
        body = body,
        created_at = utcnow()
    )

async def test_reject_non_participant():
    repo = FakeMessageRepository()

    with pytest.raises(HTTPException) as exc:
        await send_message(FakeSession(),repo, FakeConversationRepository(),conversation_id=1, sender_id=1, body="salam")

    assert exc.value.status_code == 403


async def test_get_messages_rejects_non_participant():
    repo = FakeMessageRepository()

    with pytest.raises(HTTPException) as exc:
        await get_messages(repo, conversation_id=1, user_id=1)

    assert exc.value.status_code == 403


async def test_get_messages_returns_messages_for_participant():
    repo = FakeMessageRepository(
        participants={(1, 1)}, 
        messages=[
            make_message(message_id=1, body="hi"),
            make_message(message_id=2, sender_id=2, body="hello")
        ])
    result = await get_messages(repo, conversation_id=1, user_id=1)
    assert [m.message_id for m in result] == [2, 1]
    assert result[0].body == "hello"

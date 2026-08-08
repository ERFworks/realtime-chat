import pytest
from fastapi import HTTPException

from app.models.user import User
from app.utils.time import utcnow
from app.models.conversation import ConversationType , Conversation
from app.services.conversation import(
    get_or_create_private_conversation,
    list_conversations
)
from tests.unit.fakes import (
    FakeFileStorage,
    FakeUnitOfWork,
    FakeConversationRepository,
    FakeUserRepository
) 


def make_conversation(conversation_id: int = 1) -> Conversation:
    return Conversation(
        conversation_id = conversation_id,
        conversation_type=ConversationType.PRIVATE,
        created_at = utcnow(),
        updated_at = utcnow()
    )


def two_users():
    return{
        1: User(user_id=1, username="mmd123", first_name="mmd"),
        2: User(user_id=2, username="erf87", first_name="erf")
    }


async def test_rejects_self_conversation():
    uow = FakeUnitOfWork()

    with pytest.raises(HTTPException) as exc:
        await get_or_create_private_conversation(
            current_user_id=1,
            other_user_id=1,
            uow=uow,
            storage=FakeFileStorage()
        )
    assert exc.value.status_code == 400
    assert uow.committed is False


async def test_rejects_unknown_user():
    uow = FakeUnitOfWork()
    
    with pytest.raises(HTTPException) as exc:
        await get_or_create_private_conversation(
            current_user_id=1,
            other_user_id=2,
            uow=uow,
            storage=FakeFileStorage()
        )

    assert exc.value.status_code == 404
    assert uow.committed is False


async def test_returns_existing_conversation():
    users = two_users()
    uow = FakeUnitOfWork()
    uow.users = FakeUserRepository(users=users)
    uow.conversations = FakeConversationRepository(
        conversations=[make_conversation(1)],
        participants=[(1,1), (1,2)],
        users=users
    )

    result = await get_or_create_private_conversation(
        current_user_id=1,
        other_user_id=2,
        uow=uow,
        storage=FakeFileStorage()
    )

    assert result.conversation_id == 1
    assert {p.user_id for p in result.participants} == {1,2}
    assert uow.committed is False


async def test_creates_new_coversations():
    users = two_users()
    uow = FakeUnitOfWork()
    uow.users = FakeUserRepository(users=users)
    uow.conversations = FakeConversationRepository(users=users)
    result = await get_or_create_private_conversation(
        current_user_id=1,
        other_user_id=2,
        uow=uow,
        storage=FakeFileStorage()
    )

    assert result.conversation_id == 1
    assert {p.user_id for p in result.participants} == {1, 2}
    assert uow.committed is True


async def test_list_conversations_returns_user_conversations():
    users = two_users()
    uow = FakeUnitOfWork()
    uow.users = FakeUserRepository(users=users)
    uow.conversations = FakeConversationRepository(
        conversations=[make_conversation(1)],
        participants=[(1, 1), (1, 2)],
        users=users
    )
    result = await list_conversations(
        user_id=1,
        uow=uow,
        storage=FakeFileStorage()
    )
    assert len(result) == 1
    assert result[0].conversation_id == 1



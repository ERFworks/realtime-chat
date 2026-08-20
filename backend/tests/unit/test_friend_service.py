import pytest
from fastapi import HTTPException

from app.models.friendship import Friendship, FriendshipStatus
from app.models.user import User
from app.services.friend import add_friend
from tests.unit.fakes import FakeFriendRepository, FakeUnitOfWork, FakeUserRepository


async def test_add_friend_rejects_self_request():
    uow = FakeUnitOfWork()

    with pytest.raises(HTTPException) as exc:
        await add_friend(uow, requester_id=1, addressee_id=1)

    assert exc.value.status_code == 400
    assert uow.committed is False


async def test_add_friend_rejects_existing_friendship():
    addressee = User(user_id=2, username="mmd")

    uow = FakeUnitOfWork()
    uow.users = FakeUserRepository(users={2: addressee})
    uow.friends = FakeFriendRepository(
        friendships=[
            Friendship(
                friendship_id=1,
                requester_id=1,
                addressee_id=2,
                status=FriendshipStatus.ACCEPTED,
            )
        ]
    )
    
    with pytest.raises(HTTPException) as exc:
        await add_friend(uow, requester_id=1, addressee_id=2)

    assert exc.value.status_code == 409
    assert uow.committed is False


async def test_add_friend_rejects_unknown_user():
    uow = FakeUnitOfWork()

    with pytest.raises(HTTPException) as exc:
        await add_friend(uow, requester_id=1, addressee_id=2)

    assert exc.value.status_code == 404
    assert uow.committed is False


async def test_add_friend_creates_pending_request():
    addresse = User(user_id=2, username="mmd")
    uow = FakeUnitOfWork()
    uow.users = FakeUserRepository(users={2: addresse})
    result = await add_friend(uow, requester_id=1, addressee_id=2)
    assert result.status == FriendshipStatus.PENDING
    assert uow.committed is True
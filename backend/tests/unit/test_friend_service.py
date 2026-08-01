import pytest
from fastapi import HTTPException

from app.models.user import User
from app.models.friendship import FriendshipStatus, Friendship
from app.services.friend import add_friend
from tests.unit.fakes import FakeFriendRepository, FakeUserRepository

async def test_add_friend_rejects_self_request():
    friend_repo = FakeFriendRepository
    user_repo = FakeFriendRepository

    with pytest.raises(HTTPException) as exc:
        await add_friend(db=None, friend_repo=friend_repo, user_repo=user_repo, requester_id=1, addressee_id=1)

    assert exc.value.status_code == 400

async def test_add_friend_rejects_existing_friendship():
    addressee = User(user_id=2, username="mmd")

    friend_repo = FakeFriendRepository(
        friendships = [Friendship(friendship_id=1, requester_id=1, addressee_id=2,
                        status = FriendshipStatus.ACCEPTED)]
    )
    user_repo = FakeUserRepository(users={2: addressee})

    with pytest.raises(HTTPException) as exc:
        await add_friend(db=None, friend_repo=friend_repo, user_repo=user_repo, requester_id=1, addressee_id=2)

    assert exc.value.status_code == 409

async def test_add_friend_rejects_unknown_user():
    friend_repo = FakeFriendRepository()
    user_repo = FakeUserRepository(users={})

    with pytest.raises(HTTPException) as exc:
        await add_friend(db=None, friend_repo=friend_repo, user_repo=user_repo, requester_id=1, addressee_id=2)

    assert exc.value.status_code == 404
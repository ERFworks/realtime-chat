import pytest
from fastapi import HTTPException

from app.models.user import User
from app.services.auth import register_user, authenticate_user, refresh_tokens
from app.core.security import hash_password, create_access_token, create_refresh_token
from tests.unit.fakes import FakeUnitOfWork, FakeUserRepository


def make_user(user_id: int=1, username: str = "erf", password: str = "password123") -> User:
    return User(
        user_id = user_id,
        username = username,
        password_hash = hash_password(password),
        first_name = "erfan"
    )


async def test_register_creates_user_and_profile():
    uow = FakeUnitOfWork()

    result = await register_user(uow, username="erf", password="password123", first_name="erfan")
    assert result.username == "erf"
    assert result.profile_pic is None
    assert uow.committed is True
    assert await uow.profiles.get_profile_by_user_id(result.user_id) is not None


async def test_register_duplicate_username_conflicts():
    existing = User(user_id=1, username="erf", password_hash="abc", first_name="erfan")
    uow = FakeUnitOfWork()
    uow.users = FakeUserRepository({1: existing})
    with pytest.raises(HTTPException) as exc :
        await register_user(uow, username="erf", password="password123", first_name="Erfan")

    assert exc.value.status_code == 409
    assert uow.committed is False


async def test_authenticate_user_success_returns_tokens():
    uow = FakeUnitOfWork()
    uow.users = FakeUserRepository(users={1: make_user()})
    result = await authenticate_user(uow, username="erf", password="password123")

    assert result.access_token
    assert result.refresh_token
    assert uow.committed is False



async def test_authenticate_user_normalizes_username():
    uow = FakeUnitOfWork()
    uow.users = FakeUserRepository(users={1: make_user()})
    result = await authenticate_user(uow, username="  ERF ", password="password123")

    assert result.access_token


async def test_authenticate_user_wrong_password():
    uow = FakeUnitOfWork()
    uow.users = FakeUserRepository(users={1: make_user()})
    with pytest.raises(HTTPException) as exc:
        await authenticate_user(uow, username="erf", password="wrong-password")

    assert exc.value.status_code == 401
    assert uow.committed is False


async def test_authenticate_user_unknown_user():
    uow = FakeUnitOfWork()
    with pytest.raises(HTTPException) as exc:
        await authenticate_user(uow, username="unknown-user", password="unknown-user-password")

    assert exc.value.status_code == 401
    assert uow.committed is False


async def test_refresh_tokens_success_returns_new_tokens():
    uow = FakeUnitOfWork()
    uow.users = FakeUserRepository({1: make_user()})
    token = create_refresh_token({"sub":"1"})
    result = await refresh_tokens(uow, token)

    assert result.access_token
    assert result.refresh_token
    assert uow.committed is False


async def test_refresh_tokens_rejects_access_token():
    uow = FakeUnitOfWork()
    uow.users = FakeUserRepository({1: make_user()})
    token = create_access_token({"sub":"1"})
    with pytest.raises(HTTPException) as exc:
        await refresh_tokens(uow, token)

    assert exc.value.status_code == 401

async def test_refersh_tokens_rejects_garbage_token():
    uow = FakeUnitOfWork()
    with pytest.raises(HTTPException) as exc:
        await refresh_tokens(uow, "not-a-real-jwt")

    assert exc.value.status_code == 401


async def test_refersh_tokens_rejects_deleted_user():
    uow = FakeUnitOfWork()
    token = create_refresh_token({"sub": "5"})
    with pytest.raises(HTTPException) as exc:
        await refresh_tokens(uow, token)

    assert exc.value.status_code == 401 


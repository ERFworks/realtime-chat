import pytest
from fastapi import HTTPException

from app.core.security import create_access_token, create_refresh_token, hash_password
from app.models.user import User
from app.services.auth import authenticate_user, logout, refresh_tokens, register_user
from tests.unit.fakes import FakeTokenStore, FakeUnitOfWork, FakeUserRepository


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
    token_store = FakeTokenStore()
    result = await authenticate_user(uow, token_store, username="erf", password="password123")

    assert result.access_token
    assert result.refresh_token
    assert await token_store.is_refresh_token_active(1, result.refresh_token)
    assert uow.committed is False



async def test_authenticate_user_normalizes_username():
    uow = FakeUnitOfWork()
    uow.users = FakeUserRepository(users={1: make_user()})
    token_store = FakeTokenStore()
    result = await authenticate_user(uow, token_store, username="  ERF ", password="password123")

    assert result.access_token


async def test_authenticate_user_wrong_password():
    uow = FakeUnitOfWork()
    uow.users = FakeUserRepository(users={1: make_user()})
    token_store = FakeTokenStore()
    with pytest.raises(HTTPException) as exc:
        await authenticate_user(uow, token_store, username="erf", password="wrong-password")

    assert exc.value.status_code == 401
    assert uow.committed is False


async def test_authenticate_user_unknown_user():
    uow = FakeUnitOfWork()
    token_store = FakeTokenStore()
    with pytest.raises(HTTPException) as exc:
        await authenticate_user(uow, token_store, username="unknown-user", password="unknown-user-password")

    assert exc.value.status_code == 401
    assert uow.committed is False


async def test_refresh_tokens_success_rotates_token():
    uow = FakeUnitOfWork()
    uow.users = FakeUserRepository({1: make_user()})
    token_store = FakeTokenStore()
    token = create_refresh_token({"sub":"1"}, family_id="family-1")
    await token_store.store_refresh_token(1, token, "family-1", 86400 * 7)
    result = await refresh_tokens(uow, token_store, token)

    assert result.access_token
    assert result.refresh_token
    assert result.refresh_token != token
    assert await token_store.is_refresh_token_active(1, result.refresh_token)
    assert not await token_store.is_refresh_token_active(1, token)


async def test_refresh_reuse_detection_revokes_family():
    uow = FakeUnitOfWork()
    uow.users = FakeUserRepository({1: make_user()})
    token_store = FakeTokenStore()
    token = create_refresh_token({"sub":"1"}, family_id="family-1")
    await token_store.store_refresh_token(1, token, "family-1", 86400 * 7)

    rotated = await refresh_tokens(uow, token_store, token)
    # replaying the old (already rotated) token is reuse -> family revoked
    with pytest.raises(HTTPException) as exc:
        await refresh_tokens(uow, token_store, token)

    assert exc.value.status_code == 401
    # the newest token of the family is dead too
    with pytest.raises(HTTPException) as exc:
        await refresh_tokens(uow, token_store, rotated.refresh_token)
    assert exc.value.status_code == 401
    assert not await token_store.is_refresh_token_active(1, rotated.refresh_token)


async def test_refresh_tokens_rejects_token_without_family_id():
    uow = FakeUnitOfWork()
    uow.users = FakeUserRepository({1: make_user()})
    token_store = FakeTokenStore()
    token = create_refresh_token({"sub":"1"})
    with pytest.raises(HTTPException) as exc:
        await refresh_tokens(uow, token_store, token)

    assert exc.value.status_code == 401


async def test_refresh_tokens_rejects_access_token():
    uow = FakeUnitOfWork()
    uow.users = FakeUserRepository({1: make_user()})
    token_store = FakeTokenStore()
    token = create_access_token({"sub":"1"})
    with pytest.raises(HTTPException) as exc:
        await refresh_tokens(uow, token_store, token)

    assert exc.value.status_code == 401

async def test_refersh_tokens_rejects_garbage_token():
    uow = FakeUnitOfWork()
    token_store = FakeTokenStore()
    with pytest.raises(HTTPException) as exc:
        await refresh_tokens(uow, token_store, "not-a-real-jwt")

    assert exc.value.status_code == 401


async def test_refersh_tokens_rejects_deleted_user():
    uow = FakeUnitOfWork()
    token_store = FakeTokenStore()
    token = create_refresh_token({"sub": "5"}, family_id="family-5")
    await token_store.store_refresh_token(5, token, "family-5", 86400 * 7)
    with pytest.raises(HTTPException) as exc:
        await refresh_tokens(uow, token_store, token)

    assert exc.value.status_code == 401 


async def test_logout_revokes_refresh_and_access_tokens():
    uow = FakeUnitOfWork()
    uow.users = FakeUserRepository({1: make_user()})
    token_store = FakeTokenStore()
    tokens = await authenticate_user(uow, token_store, username="erf", password="password123")

    await logout(token_store, 1, tokens.access_token, tokens.refresh_token)

    assert not await token_store.is_refresh_token_active(1, tokens.refresh_token)
    assert await token_store.is_access_token_revoked(tokens.access_token)


async def test_logout_rejects_other_users_refresh_token():
    uow = FakeUnitOfWork()
    uow.users = FakeUserRepository({1: make_user(), 2: make_user(user_id=2, username="mmd")})
    token_store = FakeTokenStore()
    tokens = await authenticate_user(uow, token_store, username="erf", password="password123")

    with pytest.raises(HTTPException) as exc:
        await logout(token_store, 2, tokens.access_token, tokens.refresh_token)

    assert exc.value.status_code == 401

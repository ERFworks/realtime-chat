import pytest
from fastapi import HTTPException
from app.models.user import User
from app.services.auth import register_user
from tests.unit.fakes import FakeUnitOfWork, FakeUserRepository


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
from app.models.user import User
from app.services.user import search_users
from tests.unit.fakes import FakeUserRepository, FakeUnitOfWork


async def test_search_excludes_self_and_filters():
    users = {
        1: User(user_id=1, username="erf", first_name="Erfan"),
        2: User(user_id=2, username="ali", first_name="Ali"),
        3: User(user_id=3, username="erfun", first_name="Erfan2"),
    }
    uow = FakeUnitOfWork()
    uow.users = FakeUserRepository(users)
    result = await search_users(uow, "erf", current_user_id=1)

    assert {u.username for u in result} == {"erfun"}
    assert all(u.profile_pic is None for u in result)
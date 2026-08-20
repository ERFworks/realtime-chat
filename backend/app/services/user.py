from app.adapters.file_storage import AbstractFileStorage
from app.schemas.auth import UserOut
from app.services.unit_of_work import AbstractUnitOfWork


async def search_users(
    uow: AbstractUnitOfWork,
    query: str,
    current_user_id: int,
    storage: AbstractFileStorage,
    limit: int = 20
) -> list[UserOut]:

    async with uow:
        rows = await uow.users.search_users(query, current_user_id, limit=limit)
        return [
            UserOut(
                user_id=user.user_id,
                username=user.username,
                first_name=user.first_name,
                last_name=user.last_name,
                profile_pic=storage.url_for(key)
            )
            for user, key in rows
        ]
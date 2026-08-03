from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.api.deps import get_current_user, get_user_repo
from app.models.user import User
from app.schemas.auth import UserOut
from app.repositories.user import AbstractUserRepository
from app.utils.file_storage import presigned_url

router = APIRouter(tags=["users"])


@router.get("/search", response_model=list[UserOut])
async def search_users(
    q: str = Query(min_length=1),
    db: AsyncSession = Depends(get_db),
    user_repo: AbstractUserRepository = Depends(get_user_repo),
    current_user: User = Depends(get_current_user),
):
    rows = await user_repo.search_users(q, current_user.user_id)
    return [
        UserOut(
            user_id=user.user_id,
            username=user.username,
            first_name=user.first_name,
            last_name=user.last_name,
            profile_pic=presigned_url(key)
        )
        for user, key in rows
    ]
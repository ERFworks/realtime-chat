from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.api.deps import get_current_user
from app.models.user import User
from app.schemas.auth import UserOut
from app.repositories import user as user_repo
from app.utils.file_storage import get_profile_picture_url 

router = APIRouter(tags=["users"])


@router.get("/search", response_model=list[UserOut])
async def search_users(
    q: str = Query(min_length=1),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    rows = await user_repo.search_users(db, q, current_user.user_id)
    return [
        UserOut(
            user_id=user.user_id,
            username=user.username,
            first_name=user.first_name,
            last_name=user.last_name,
            profile_pic=get_profile_picture_url(key)
        )
        for user, key in rows
    ]
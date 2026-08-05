from fastapi import APIRouter, Depends, Query

from app.api.deps import get_current_user, get_uow
from app.models.user import User
from app.schemas.auth import UserOut
from app.services.unit_of_work import AbstractUnitOfWork
from app.services import user as user_service

router = APIRouter(tags=["users"])


@router.get("/search", response_model=list[UserOut])
async def search_users(
    q: str = Query(min_length=1),
    uow: AbstractUnitOfWork = Depends(get_uow),
    current_user: User = Depends(get_current_user),
):
    return await user_service.search_users(uow, q, current_user.user_id)
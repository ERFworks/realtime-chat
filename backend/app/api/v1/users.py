from fastapi import APIRouter, Depends, Query

from app.adapters.file_storage import AbstractFileStorage
from app.api.deps import get_current_user, get_file_storage, get_uow
from app.models.user import User
from app.schemas.auth import UserOut
from app.services import user as user_service
from app.services.unit_of_work import AbstractUnitOfWork

router = APIRouter(tags=["users"])


@router.get("/search", response_model=list[UserOut])
async def search_users(
    q: str = Query(min_length=1),
    uow: AbstractUnitOfWork = Depends(get_uow),
    storage : AbstractFileStorage = Depends(get_file_storage),
    current_user: User = Depends(get_current_user),
):
    return await user_service.search_users(uow, q, current_user.user_id, storage)
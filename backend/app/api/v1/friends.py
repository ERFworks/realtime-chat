from fastapi import APIRouter, status, Depends

from app.db.session import get_db
from app.models.user import User
from app.api.deps import get_current_user, get_uow
from app.schemas.friend import FriendOut
from app.schemas.auth import UserOut
from app.services import friend as friend_service
from app.services.unit_of_work import AbstractUnitOfWork



router = APIRouter(tags=["friends"])

@router.post(
    "/requests/{user_id}", 
    response_model=FriendOut, 
    status_code = status.HTTP_201_CREATED)

async def send_request(
    user_id: int,
    current_user: User = Depends(get_current_user),
    uow: AbstractUnitOfWork = Depends(get_uow)
):
    return await friend_service.add_friend(uow, current_user.user_id, user_id)


@router.get("/requests", response_model= list[FriendOut])
async def pending_requests(
    current_user: User = Depends(get_current_user),
    uow: AbstractUnitOfWork = Depends(get_uow)
):
    return await friend_service.list_my_pending_requests(uow, current_user.user_id)


@router.post("/requests/{friendship_id}/respond", response_model=FriendOut)
async def respond_request(
    friendship_id: int,
    accept: bool,
    current_user: User = Depends(get_current_user),
    uow: AbstractUnitOfWork = Depends(get_uow)
):
    return await friend_service.respond_to_request(
        uow, current_user.user_id, friendship_id, accept
    )


@router.get("", response_model= list[UserOut])
async def get_accepted_friends(
    uow: AbstractUnitOfWork = Depends(get_uow),
    current_user: User = Depends(get_current_user)
):
    return await friend_service.list_my_friends(uow, current_user.user_id)
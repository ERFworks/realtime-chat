from fastapi import APIRouter, status, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.user import User
from app.api.deps import get_current_user, get_friend_repo, get_user_repo
from app.schemas.friend import FriendOut
from app.schemas.auth import UserOut
from app.services import friend as friend_service
from app.repositories.user import AbstractUserRepository
from app.repositories.friend import AbstractFriendRepository



router = APIRouter(tags=["friends"])

@router.post(
    "/requests/{user_id}", 
    response_model=FriendOut, 
    status_code = status.HTTP_201_CREATED)

async def send_request(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    friend_repo: AbstractFriendRepository = Depends(get_friend_repo),
    user_repo: AbstractUserRepository = Depends(get_user_repo)
):
    return await friend_service.add_friend(db, friend_repo, user_repo, current_user.user_id, user_id)


@router.get("/requests", response_model= list[FriendOut])
async def pending_requests(
    current_user: User = Depends(get_current_user),
    friend_repo: AbstractFriendRepository = Depends(get_friend_repo)
):
    return await friend_service.list_my_pending_requests(friend_repo, current_user.user_id)


@router.post("/requests/{friendship_id}/respond", response_model=FriendOut)
async def respond_request(
    friendship_id: int,
    accept: bool,
    friend_repo: AbstractFriendRepository = Depends(get_friend_repo),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return await friend_service.respond_to_request(
        db, friend_repo, current_user.user_id, friendship_id, accept
    )


@router.get("", response_model= list[UserOut])
async def get_accepted_friends(
    friend_repo: AbstractFriendRepository = Depends(get_friend_repo),
    current_user: User = Depends(get_current_user)
):
    return await friend_service.list_my_friends(friend_repo, current_user.user_id)
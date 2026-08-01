from fastapi import HTTPException , status
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.friend import AbstractFriendRepository
from app.repositories.user import AbstractUserRepository
from app.schemas.friend import FriendOut
from app.schemas.auth import UserOut
from app.models.friendship import FriendshipStatus
from app.utils.file_storage import get_profile_picture_url 


async def add_friend(
    db: AsyncSession,
    friend_repo: AbstractFriendRepository,
    user_repo: AbstractUserRepository, 
    requester_id: int, 
    addressee_id: int
) -> FriendOut:

    if requester_id == addressee_id:
        raise HTTPException(
            status_code = status.HTTP_400_BAD_REQUEST,
            detail="Cannot send a friend request to yourself"
        )

    if await user_repo.get_user_by_id(addressee_id) is None:
        raise HTTPException(
            status_code = status.HTTP_404_NOT_FOUND,
            detail = "User not found"
        )


    existing = await friend_repo.get_friendship_between(requester_id, addressee_id)
    if existing is not None:
        raise HTTPException(
            status_code = status.HTTP_409_CONFLICT,
            detail = "Friendship already exists" 
        )

    friendship = await friend_repo.create_friend_request(requester_id, addressee_id)

    await db.commit()
    await db.refresh(friendship)
    return FriendOut.model_validate(friendship)

    

async def respond_to_request(
    db: AsyncSession, 
    friend_repo: AbstractFriendRepository,
    user_id: int, 
    friendship_id: int, 
    accept: bool
) -> FriendOut:

    friendship = await friend_repo.get_friendship_by_id(friendship_id)

    if friendship is None:
        raise HTTPException(
            status_code = status.HTTP_404_NOT_FOUND,
            detail = "Friend request not found"
        )

    if friendship.addressee_id != user_id:
        raise HTTPException(
            status_code = status.HTTP_403_FORBIDDEN,
            detail = "You cannot respond to this request"
        )


    if friendship.status != FriendshipStatus.PENDING:
        raise HTTPException(
            status_code = status.HTTP_409_CONFLICT,
            detail = "Request already handled"
        )

    new_status = FriendshipStatus.ACCEPTED if accept else FriendshipStatus.REJECTED
    updated = await friend_repo.update_friendship_status(friendship_id, new_status)


    await db.commit()
    await db.refresh(updated)
    return FriendOut.model_validate(updated)


async def list_my_friends(
    friend_repo: AbstractFriendRepository,
    user_id: int
) -> list[UserOut]:

    friends = await friend_repo.list_friends(user_id)
    return [
        UserOut(
            user_id=user.user_id,
            username=user.username,
            first_name=user.first_name,
            last_name=user.last_name,
            profile_pic=get_profile_picture_url(key)
        )
        for user, key in friends
    ]


async def list_my_pending_requests(
    friend_repo: AbstractFriendRepository,
    user_id: int
) -> list[FriendOut]:

    pending_requests = await friend_repo.list_pending_requests(user_id)
    return [FriendOut.model_validate(p) for p in pending_requests]


        
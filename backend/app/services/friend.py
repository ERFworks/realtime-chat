from fastapi import HTTPException , status

from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories import friend as friend_repo
from app.repositories import user as user_repo

from app.schemas.friend import FriendOut
from app.schemas.auth import UserOut

from app.models.friendship import FriendshipStatus


async def add_friend(
    db: AsyncSession, 
    requester_id: int, 
    addressee_id: int
) -> FriendOut:

    if requester_id == addressee_id:
        raise HTTPException(
            status_code = status.HTTP_400_BAD_REQUEST,
            detail="Cannot send a friend request to yourself"
        )

    if await user_repo.get_user_by_id(db, addressee_id) is None:
        raise HTTPException(
            status_code = status.HTTP_404_NOT_FOUND,
            detail = "User not found"
        )


    existing = await friend_repo.get_friendship_between(db, requester_id, addressee_id)
    if existing is not None:
        raise HTTPException(
            status_code = status.HTTP_409_CONFLICT,
            detail = "Friendship already exists" 
        )

    friendship = await friend_repo.create_friend_request(db, requester_id, addressee_id)

    await db.commit()
    await db.refresh(friendship)
    return FriendOut.model_validate(friendship)

    

async def respond_to_request(
    db: AsyncSession, 
    user_id: int, 
    friendship_id: int, 
    accept: bool
) -> FriendOut:
    friendship = await friend_repo.get_friendship_by_id(db, friendship_id)

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
    updated = await friend_repo.update_friendship_status(db, friendship_id, new_status)


    await db.commit()
    await db.refresh(updated)
    return FriendOut.model_validate(updated)


async def list_my_friends(db: AsyncSession, user_id: int) -> list[UserOut]:

    friends = await friend_repo.list_friends(db, user_id)
    return [UserOut.model_validate(f) for f in friends]


async def list_my_pending_requests(db: AsyncSession, user_id: int) -> list[FriendOut]:

    pending_requests = await friend_repo.list_pending_requests(db, user_id)
    return [FriendOut.model_validate(p) for p in pending_requests]


        
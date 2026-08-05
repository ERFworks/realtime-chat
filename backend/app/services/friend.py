from fastapi import HTTPException , status

from app.schemas.friend import FriendOut
from app.schemas.auth import UserOut
from app.models.friendship import FriendshipStatus
from app.utils.file_storage import presigned_url
from app.services.unit_of_work import AbstractUnitOfWork


async def add_friend(
    uow: AbstractUnitOfWork,
    requester_id: int, 
    addressee_id: int
) -> FriendOut:

    if requester_id == addressee_id:
        raise HTTPException(
            status_code = status.HTTP_400_BAD_REQUEST,
            detail="Cannot send a friend request to yourself"
        )
    async with uow:
        if await uow.users.get_user_by_id(addressee_id) is None:
            raise HTTPException(
                status_code = status.HTTP_404_NOT_FOUND,
                detail = "User not found"
            )

        existing = await uow.friends.get_friendship_between(requester_id, addressee_id)
        if existing is not None:
            raise HTTPException(
                status_code = status.HTTP_409_CONFLICT,
                detail = "Friendship already exists" 
            )

        friendship = await uow.friends.create_friend_request(requester_id, addressee_id)

        await uow.commit()
        return FriendOut.model_validate(friendship)

    

async def respond_to_request(
    uow: AbstractUnitOfWork,
    user_id: int, 
    friendship_id: int, 
    accept: bool
) -> FriendOut:
    
    async with uow:
        friendship = await uow.friends.get_friendship_by_id(friendship_id)

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
        updated = await uow.friends.update_friendship_status(friendship_id, new_status)


        await uow.commit()
        return FriendOut.model_validate(updated)


async def list_my_friends(
    uow: AbstractUnitOfWork,
    user_id: int
) -> list[UserOut]:

    async with uow:
        friends = await uow.friends.list_friends(user_id)

        return [
            UserOut(
                user_id=user.user_id,
                username=user.username,
                first_name=user.first_name,
                last_name=user.last_name,
                profile_pic=presigned_url(user.profile.profile_pic if user.profile else None)
            )
            for user in friends
        ]


async def list_my_pending_requests(
    uow: AbstractUnitOfWork,
    user_id: int
) -> list[FriendOut]:
    async with uow:
        pending_requests = await uow.friends.list_pending_requests(user_id)

        return [FriendOut.model_validate(p) for p in pending_requests]


        
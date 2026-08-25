from fastapi import HTTPException, status

from app.adapters.file_storage import AbstractFileStorage
from app.models.friendship import FriendshipStatus
from app.schemas.auth import UserOut
from app.schemas.friend import (
    FriendOut,
    FriendRequesterInfo,
    FriendRequestOut,
)
from app.services.unit_of_work import AbstractUnitOfWork
from app.utils.time import utcnow
from app.websocket.manager import manager


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
            if existing.status == FriendshipStatus.ACCEPTED:
                raise HTTPException(
                    status_code = status.HTTP_409_CONFLICT,
                    detail = "You are already friends"
                )

            if existing.status == FriendshipStatus.PENDING:
                raise HTTPException(
                    status_code = status.HTTP_409_CONFLICT,
                    detail = "A friend request already exists"
                )

            # REJECTED or BLOCKED → allow a fresh request.
            existing.requester_id = requester_id
            existing.addressee_id = addressee_id
            existing.status = FriendshipStatus.PENDING
            existing.created_at = utcnow()
            await uow.commit()
            return FriendOut.model_validate(existing)

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

        if accept:
            try:
                payload = {
                    "type": "friend_accepted",
                    "data": {
                        "friendship_id": friendship_id,
                        "user_id": friendship.requester_id,
                        "friend_id": friendship.addressee_id,
                    },
                }
                # Notify both users so they can refresh their friends lists
                await manager.send_to_user(friendship.requester_id, payload)
                await manager.send_to_user(friendship.addressee_id, payload)
            except Exception:
                pass  # best-effort delivery — don't fail the request

        return FriendOut.model_validate(updated)


async def list_my_friends(
    uow: AbstractUnitOfWork,
    user_id: int,
    storage: AbstractFileStorage
) -> list[UserOut]:

    async with uow:
        friends = await uow.friends.list_friends(user_id)

        return [
            UserOut(
                user_id=user.user_id,
                username=user.username,
                first_name=user.first_name,
                last_name=user.last_name,
                profile_pic=storage.url_for(user.profile.profile_pic if user.profile else None)
            )
            for user in friends
        ]


async def list_my_pending_requests(
    uow: AbstractUnitOfWork,
    user_id: int,
    storage: AbstractFileStorage
) -> list[FriendRequestOut]:
    async with uow:
        pending_requests = await uow.friends.list_pending_requests(user_id)

        result = []
        for p in pending_requests:
            requester = p.requester
            profile_pic = (
                requester.profile.profile_pic if requester.profile else None
            )
            result.append(
                FriendRequestOut(
                    friendship_id=p.friendship_id,
                    requester_id=p.requester_id,
                    addressee_id=p.addressee_id,
                    status=p.status,
                    created_at=p.created_at,
                    requester=FriendRequesterInfo(
                        user_id=requester.user_id,
                        username=requester.username,
                        first_name=requester.first_name,
                        last_name=requester.last_name,
                        profile_pic=storage.url_for(profile_pic),
                    ),
                )
            )

        return result


        
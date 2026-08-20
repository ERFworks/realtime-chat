from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models.friendship import FriendshipStatus


class FriendRequestCreate(BaseModel):
    other_user_id: int

class FriendOut(BaseModel):
    friendship_id: int
    requester_id: int
    addressee_id: int
    status: FriendshipStatus 
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)

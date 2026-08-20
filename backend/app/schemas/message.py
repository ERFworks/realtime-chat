from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class MessageCreate(BaseModel):
    body: str = Field(min_length=1, max_length=4000)

class MessageOut(BaseModel):
    message_id: int
    conversation_id: int
    sender_id: int | None
    body: str
    created_at: datetime
    edited_at: datetime | None
    deleted_at: datetime | None
    model_config = ConfigDict(from_attributes=True)
from datetime import datetime
from pydantic import BaseModel, ConfigDict
from app.models.conversation import ConversationType


class ConversationCreate(BaseModel):
    other_user_id: int

class ParticipantOut(BaseModel):
    user_id: int
    username: str
    first_name: str
    last_name: str | None = None
    model_config = ConfigDict(from_attributes=True)

class ConversationOut(BaseModel):
    conversation_id: int
    conversation_type: ConversationType
    created_at: datetime
    updated_at: datetime
    participants: list[ParticipantOut]
    model_config = ConfigDict(from_attributes=True)




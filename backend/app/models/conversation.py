import enum

from app.utils.time import utcnow
from app.db.base_class import Base
from datetime import datetime
from sqlalchemy import DateTime, Enum
from sqlalchemy.orm import Mapped ,mapped_column


class ConversationType(str, enum.Enum):
    PRIVATE = "private"

class Conversation(Base):
    __tablename__ = "conversations"

    conversation_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    
    conversation_type: Mapped[ConversationType] = mapped_column(
        Enum(ConversationType, name= "conversation_type"),
        default = ConversationType.PRIVATE,
        nullable = False
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), 
        default = utcnow
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), 
        default = utcnow, 
        onupdate=utcnow
    )
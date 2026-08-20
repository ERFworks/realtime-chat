import enum
from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, Enum, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base_class import Base
from app.utils.time import utcnow


class ConversationType(str, enum.Enum):
    PRIVATE = "private"

class Conversation(Base):
    __tablename__ = "conversations"

    __table_args__ = (
        UniqueConstraint("user_a_id", "user_b_id", name="uq_conversations_private_pair"),
        CheckConstraint(
            "user_a_id IS NULL OR user_a_id < user_b_id",
            name="ck_conversations_pair_order"
        )
    )

    conversation_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    
    conversation_type: Mapped[ConversationType] = mapped_column(
        Enum(ConversationType, name= "conversation_type"),
        default = ConversationType.PRIVATE,
        nullable = False
    )

    user_a_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.user_id", ondelete="CASCADE"),
        nullable=True
    )

    user_b_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.user_id", ondelete="CASCADE"),
        nullable=True
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
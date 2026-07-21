from app.utils.time import utcnow
from app.db.base_class import Base
from datetime import datetime
from sqlalchemy import DateTime, ForeignKey, Text, Index
from sqlalchemy.orm import Mapped ,mapped_column


class Message(Base):
    __tablename__ = "messages"

    __table_args__ = (
        Index("ix_messages_conversation_created", "conversation_id", "created_at"),
    )

    message_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    
    conversation_id: Mapped[int] = mapped_column(
        ForeignKey("conversations.conversation_id", ondelete="CASCADE"),
        nullable = False
    )

    sender_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.user_id", ondelete="SET NULL"),
        nullable = True
    )

    body: Mapped[str] = mapped_column(
        Text,
        nullable=False
    )


    created_at : Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default = utcnow,
        nullable=False
    )

    edited_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), 
        nullable = True,
        default = None
    )

    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), 
        nullable = True,
        default = None
    )



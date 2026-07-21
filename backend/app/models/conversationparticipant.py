from app.utils.time import utcnow
from app.db.base_class import Base
from datetime import datetime
from sqlalchemy import DateTime, ForeignKey
from sqlalchemy.orm import Mapped ,mapped_column


class ConversationParticipant(Base):
    __tablename__ = "conversation_participants"

    conversation_id: Mapped[int] = mapped_column(
        ForeignKey("conversations.conversation_id", ondelete="CASCADE"),
        primary_key = True
    )

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.user_id", ondelete="CASCADE"),
        primary_key = True,
        index = True,
    )

    joined_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default = utcnow,
        nullable = False
    )


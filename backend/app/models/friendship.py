import enum

from app.models.user import utcnow 
from app.db.base_class import Base
from datetime import datetime
from sqlalchemy import ForeignKey, DateTime, Enum, UniqueConstraint, CheckConstraint
from sqlalchemy.orm import Mapped ,mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID


class FriendshipStatus(str, enum.Enum):
    PENDING = "pending"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    BLOCKED = "blocked"

class Friendship(Base):
    __tablename__ = "friendships"

    __table_args__ = (
        UniqueConstraint("requester_id", "addressee_id", name = "uq_friendship_pair"),
        CheckConstraint("requester_id <> addressee_id", name="ck_friendship_no_self")
    )

    friendship_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    requester_id: Mapped[int] = mapped_column(
        ForeignKey("users.user_id", ondelete = "CASCADE"),
        index = True,
        nullable = False
    )

    addressee_id: Mapped[int] = mapped_column(
        ForeignKey("users.user_id", ondelete = "CASCADE"),
        index = True,
        nullable = False
    )

    status: Mapped[FriendshipStatus] = mapped_column(
        Enum(FriendshipStatus, name = "friendship_status"),
        default = FriendshipStatus.PENDING,
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

    requester: Mapped["User"] = relationship(
        foreign_keys = [requester_id],
        back_populates = "sent_friend_requests"
    )

    addressee: Mapped["User"] = relationship(
        foreign_keys = [addressee_id],
        back_populates = "received_friend_requests"
    )


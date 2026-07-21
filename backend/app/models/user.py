import uuid

from app.db.base_class import Base
from datetime import datetime, timezone
from sqlalchemy import String, Integer, DateTime
from sqlalchemy.orm import Mapped ,mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID


def utcnow() -> datetime:
    return datetime.now(timezone.utc)

class User(Base):
    __tablename__ = "users"

    user_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    guid: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), 
        default=uuid.uuid4, 
        unique=True, 
        nullable=False, 
        index=True
    )

    profile: Mapped["Profile"] = relationship(
        back_populates="user",
        uselist=False,
        cascade="all, delete-orphan"
    )

    username: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    first_name: Mapped[str] = mapped_column(String, nullable=False)
    last_name: Mapped[str | None] = mapped_column(String, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), 
        default = utcnow
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), 
        default = utcnow, 
        onupdate=utcnow
    )
import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class ConfigEntry(Base):
    __tablename__ = "configs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    description: Mapped[str] = mapped_column(String(256), default="", nullable=False)
    author_username: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    author_xuid: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    script_build: Mapped[str] = mapped_column(String(16), default="", nullable=False)
    cfg_version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    snapshot: Mapped[str] = mapped_column(Text, nullable=False)
    visibility: Mapped[str] = mapped_column(String(16), default="public", nullable=False)
    downloads: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False
    )

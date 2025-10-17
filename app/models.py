from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, func, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .db import Base


class UrlMap(Base):
    __tablename__ = "url_map"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    code: Mapped[str] = mapped_column(String(12), unique=True, index=True)
    target: Mapped[str] = mapped_column(String(2048))
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), default=None)
    disabled: Mapped[bool] = mapped_column(Boolean, default=False, server_default="0")
    visits: Mapped[list["Visit"]] = relationship(
        "Visit", back_populates="url", cascade="all, delete-orphan"
    )


class Visit(Base):
    __tablename__ = "visit"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    url_id: Mapped[int] = mapped_column(ForeignKey("url_map.id", ondelete="CASCADE"))
    ts: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    ip: Mapped[str] = mapped_column(String(64))
    ua: Mapped[str] = mapped_column(String(512), default="")
    ref: Mapped[str] = mapped_column(String(512), default="")

    url: Mapped[UrlMap] = relationship("UrlMap", back_populates="visits")


# Composite index for visit lookups by URL and recency
Index("ix_visit_url_ts", Visit.url_id, Visit.ts.desc())

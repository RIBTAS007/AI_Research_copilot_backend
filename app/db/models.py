"""ORM models: sessions, workflow events, chat messages, and a generic cache."""
import datetime
import uuid

from sqlalchemy import DateTime, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.database import Base


def _uuid() -> str:
    return str(uuid.uuid4())


def _now() -> datetime.datetime:
    return datetime.datetime.now(datetime.timezone.utc)


class Session(Base):
    __tablename__ = "sessions"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    company_name: Mapped[str] = mapped_column(String, nullable=False)
    website: Mapped[str] = mapped_column(String, default="")
    objective: Mapped[str] = mapped_column(Text, default="")
    # created | running | completed | failed
    status: Mapped[str] = mapped_column(String, default="created", index=True)
    report: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    # provider/model/prompt-version used for this run (reproducibility)
    run_meta: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime, default=_now)
    updated_at: Mapped[datetime.datetime] = mapped_column(
        DateTime, default=_now, onupdate=_now
    )

    events: Mapped[list["WorkflowEvent"]] = relationship(
        back_populates="session",
        cascade="all, delete-orphan",
        order_by="WorkflowEvent.created_at",
    )
    messages: Mapped[list["Message"]] = relationship(
        back_populates="session",
        cascade="all, delete-orphan",
        order_by="Message.created_at",
    )


class WorkflowEvent(Base):
    __tablename__ = "workflow_events"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    session_id: Mapped[str] = mapped_column(ForeignKey("sessions.id"), index=True)
    node: Mapped[str] = mapped_column(String)
    status: Mapped[str] = mapped_column(String, default="success")  # success|degraded|failed
    message: Mapped[str] = mapped_column(Text, default="")
    duration_ms: Mapped[int] = mapped_column(Integer, default=0)
    tokens: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime, default=_now)

    session: Mapped["Session"] = relationship(back_populates="events")


class Message(Base):
    __tablename__ = "messages"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    session_id: Mapped[str] = mapped_column(ForeignKey("sessions.id"), index=True)
    role: Mapped[str] = mapped_column(String)  # user | assistant
    content: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime, default=_now)

    session: Mapped["Session"] = relationship(back_populates="messages")


class CacheEntry(Base):
    """Generic key/value cache for Tavily search results and report drafts."""

    __tablename__ = "cache"

    key: Mapped[str] = mapped_column(String, primary_key=True)
    value: Mapped[dict] = mapped_column(JSON)
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime, default=_now)

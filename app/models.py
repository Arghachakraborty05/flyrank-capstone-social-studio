from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base

def utc_now():
    return datetime.now(timezone.utc)

class Post(Base):
    __tablename__ = "posts"

    id: Mapped[int] = mapped_column(
        Integer, 
        primary_key=True, 
        index=True
    )

    source_type: Mapped[str] = mapped_column(
        String(20), 
        nullable=False
    )

    source_url: Mapped[str | None] = mapped_column(
        String(1000), 
        nullable=True
    )

    title: Mapped[str | None] = mapped_column(
        String(300), 
        nullable=True
    )

    content: Mapped[str] = mapped_column(
        Text, 
        nullable=False
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), 
        default=utc_now, 
        nullable=False
    )

    variants: Mapped[list["Variant"]] = relationship(
        back_populates="post", 
        cascade="all, delete-orphan"
    )

class Variant(Base):
    __tablename__ = "variants"

    id: Mapped[int] = mapped_column(
        Integer, 
        primary_key=True, 
        index=True
    )

    post_id: Mapped[int] = mapped_column(
        ForeignKey("posts.id"), 
        nullable=False, 
        index=True
    )

    platform: Mapped[str] = mapped_column(
        String(50), 
        nullable=False
    )

    content: Mapped[str] = mapped_column(
        Text, 
        nullable=False
    )

    status: Mapped[str] = mapped_column(
        String(20), 
        default="draft", 
        nullable=False
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), 
        default=utc_now, 
        nullable=False
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), 
        default=utc_now, 
        onupdate=utc_now, 
        nullable=False
    )

    post: Mapped["Post"] = relationship(
        back_populates="variants"
    )

    schedule_slots: Mapped[list["ScheduleSlot"]] = relationship(
        back_populates="variant", 
        cascade="all, delete-orphan"
    )

    publish_attempts: Mapped[list["PublishAttempt"]] = relationship(
        back_populates="variant"
    )

class ScheduleSlot(Base):
    __tablename__ = "schedule_slots"

    id: Mapped[int] = mapped_column(
        Integer, 
        primary_key=True, 
        index=True
    )

    variant_id: Mapped[int] = mapped_column(
        ForeignKey("variants.id"), 
        nullable=False, 
        index=True
    )

    scheduled_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), 
        nullable=False
    )

    idempotency_key: Mapped[str] = mapped_column(
        String(255), 
        unique=True, 
        nullable=False, 
        index=True
    )

    status: Mapped[str] = mapped_column(
        String(20), 
        default="scheduled", 
        nullable=False
    )

    variant: Mapped["Variant"] = relationship(
        back_populates="schedule_slots"
    )

    publish_attempts: Mapped[list["PublishAttempt"]] = relationship(
        back_populates="schedule_slot", 
        cascade="all, delete-orphan"
    )

class PublishAttempt(Base):
    __tablename__ = "publish_attempts"

    id: Mapped[int] = mapped_column(
        Integer, 
        primary_key=True, 
        index=True
    )

    variant_id: Mapped[int] = mapped_column(
        ForeignKey("variants.id"), 
        nullable=False, 
        index=True
    )

    schedule_slot_id: Mapped[int] = mapped_column(
        ForeignKey("schedule_slots.id"), 
        nullable=False, 
        index=True
    )

    platform: Mapped[str] = mapped_column(
        String(50), 
        nullable=False
    )

    idempotency_key: Mapped[str] = mapped_column(
        String(255), 
        nullable=False, 
        index=True  
    )

    attempted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), 
        default=utc_now, 
        nullable=False
    )

    status: Mapped[str] = mapped_column(
        String(20), 
        nullable=False
    )

    external_id: Mapped[str | None] = mapped_column(
        String(255), 
        nullable=True
    )

    error_message: Mapped[str | None] = mapped_column(
        Text, 
        nullable=True
    )

    variant: Mapped["Variant"] = relationship(
        back_populates="publish_attempts"
    )

    schedule_slot: Mapped["ScheduleSlot"] = relationship(
        back_populates="publish_attempts"
    )
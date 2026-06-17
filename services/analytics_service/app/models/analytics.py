import uuid
from datetime import datetime
from sqlalchemy import String, Integer, Text, DateTime
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base


class CoursePublishFact(Base):
    """One row per published course. course_id is unique for idempotency."""

    __tablename__ = "course_publish_facts"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    course_id: Mapped[str] = mapped_column(String(36), nullable=False, unique=True, index=True)
    title: Mapped[str] = mapped_column(String(512), nullable=False)
    instructor_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    published_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class EnrollmentFact(Base):
    """One row per enrollment. enrollment_id is unique for idempotency."""

    __tablename__ = "enrollment_facts"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    enrollment_id: Mapped[str] = mapped_column(String(36), nullable=False, unique=True, index=True)
    student_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    course_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    enrolled_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class ProgressFact(Base):
    """Latest progress snapshot per enrollment. Upserted on each progress.updated event."""

    __tablename__ = "progress_facts"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    enrollment_id: Mapped[str] = mapped_column(String(36), nullable=False, unique=True, index=True)
    student_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    course_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    completed_modules: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    total_modules: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class FailedEvent(Base):
    """Records events that could not be processed, for monitoring."""

    __tablename__ = "failed_events"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    event_type: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    raw_payload: Mapped[str] = mapped_column(Text, nullable=False)
    error_message: Mapped[str] = mapped_column(Text, nullable=False)
    failed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

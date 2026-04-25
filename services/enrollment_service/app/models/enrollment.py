import uuid
from sqlalchemy import String, Integer, Float, ForeignKey, Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base, TimestampMixin

class Enrollment(Base, TimestampMixin):
    __tablename__ = "enrollments"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default = lambda: str(uuid.uuid4())
    )
    student_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    course_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    status: Mapped[str] = mapped_column(
        SAEnum("active", "dropped", "completed", name="enrollment_status_enum"),
        nullable=False,
        default="active",
    )

    progress: Mapped["Progress"] = relationship(
        "Progress", back_populates="enrollment", uselist=False, cascade="all, delete-orphan"
    )

class Progress(Base, TimestampMixin):
    __tablename__ = "progress"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    enrollment_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("enrollments.id"), nullable=False, unique=True, index=True
    )
    completed_modules: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    total_modules: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    completion_percentage: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)

    enrollment: Mapped["Enrollment"] = relationship("Enrollment", back_populates="progress")
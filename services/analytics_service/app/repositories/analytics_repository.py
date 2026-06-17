from datetime import datetime, timezone
from sqlalchemy import select, func, case
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.analytics import (
    CoursePublishFact,
    EnrollmentFact,
    ProgressFact,
    FailedEvent,
)

async def upsert_course_publish(
    db: AsyncSession,
    course_id: str,
    title: str,
    instructor_id: str,
    published_at: datetime,
) -> bool:
    """Insert a CoursePublishFact if course_id not already recorded. Returns True if inserted."""
    existing = await db.scalar(
        select(CoursePublishFact).where(CoursePublishFact.course_id == course_id)
    )
    if existing:
        return False
    db.add(CoursePublishFact(
        course_id=course_id,
        title=title,
        instructor_id=instructor_id,
        published_at=published_at,
    ))
    await db.flush()
    return True


async def upsert_enrollment(
    db: AsyncSession,
    enrollment_id: str,
    student_id: str,
    course_id: str,
    enrolled_at: datetime,
) -> bool:
    """Insert an EnrollmentFact if enrollment_id not already recorded. Returns True if inserted."""
    existing = await db.scalar(
        select(EnrollmentFact).where(EnrollmentFact.enrollment_id == enrollment_id)
    )
    if existing:
        return False
    db.add(EnrollmentFact(
        enrollment_id=enrollment_id,
        student_id=student_id,
        course_id=course_id,
        enrolled_at=enrolled_at,
    ))
    await db.flush()
    return True


async def upsert_progress(
    db: AsyncSession,
    enrollment_id: str,
    student_id: str,
    course_id: str,
    completed_modules: int,
    total_modules: int,
    updated_at: datetime,
) -> None:
    """Upsert the latest progress snapshot and mark enrollment complete when finished."""
    existing = await db.scalar(
        select(ProgressFact).where(ProgressFact.enrollment_id == enrollment_id)
    )
    if existing:
        existing.completed_modules = completed_modules
        existing.total_modules = total_modules
        existing.updated_at = updated_at
    else:
        db.add(ProgressFact(
            enrollment_id=enrollment_id,
            student_id=student_id,
            course_id=course_id,
            completed_modules=completed_modules,
            total_modules=total_modules,
            updated_at=updated_at,
        ))

    # Mark enrollment complete when all modules done
    if total_modules > 0 and completed_modules >= total_modules:
        enrollment = await db.scalar(
            select(EnrollmentFact).where(EnrollmentFact.enrollment_id == enrollment_id)
        )
        if enrollment and enrollment.completed_at is None:
            enrollment.completed_at = updated_at

    await db.flush()


async def record_failed_event(
    db: AsyncSession,
    event_type: str,
    raw_payload: str,
    error_message: str,
) -> None:
    db.add(FailedEvent(
        event_type=event_type,
        raw_payload=raw_payload,
        error_message=error_message,
        failed_at=datetime.now(timezone.utc),
    ))
    await db.flush()


# ─── Readers ──────────────────────────────────────────────────────────────────

async def count_distinct_students(db: AsyncSession) -> int:
    result = await db.scalar(
        select(func.count(func.distinct(EnrollmentFact.student_id)))
    )
    return result or 0


async def count_distinct_instructors(db: AsyncSession) -> int:
    result = await db.scalar(
        select(func.count(func.distinct(CoursePublishFact.instructor_id)))
    )
    return result or 0


async def count_courses_published(db: AsyncSession) -> int:
    result = await db.scalar(select(func.count(CoursePublishFact.id)))
    return result or 0


async def enrollments_over_time(db: AsyncSession) -> list[dict]:
    """Returns daily enrollment counts."""
    rows = await db.execute(
        select(
            func.date(EnrollmentFact.enrolled_at).label("date"),
            func.count(EnrollmentFact.id).label("count"),
        )
        .group_by(func.date(EnrollmentFact.enrolled_at))
        .order_by(func.date(EnrollmentFact.enrolled_at))
    )
    return [{"date": str(row.date), "count": row.count} for row in rows]


async def completion_rate_per_course(db: AsyncSession) -> list[dict]:
    """Returns completion rate per course."""
    rows = await db.execute(
        select(
            EnrollmentFact.course_id,
            func.count(EnrollmentFact.id).label("total"),
            func.sum(
                case((EnrollmentFact.completed_at.is_not(None), 1), else_=0)
            ).label("completed"),
        )
        .group_by(EnrollmentFact.course_id)
    )
    return [
        {
            "course_id": row.course_id,
            "total_enrollments": row.total,
            "completed_enrollments": row.completed,
            "completion_rate": round(row.completed / row.total, 4) if row.total else 0.0,
        }
        for row in rows
    ]


async def avg_seconds_to_complete(db: AsyncSession) -> float | None:
    """Returns average seconds from enrollment to completion across all completed enrollments."""
    rows = await db.execute(
        select(EnrollmentFact.enrolled_at, EnrollmentFact.completed_at)
        .where(EnrollmentFact.completed_at.is_not(None))
    )
    durations = [
        (row.completed_at - row.enrolled_at).total_seconds()
        for row in rows
        if row.completed_at and row.enrolled_at
    ]
    if not durations:
        return None
    return round(sum(durations) / len(durations), 2)


async def most_popular_courses(db: AsyncSession, limit: int = 10) -> list[dict]:
    rows = await db.execute(
        select(
            EnrollmentFact.course_id,
            func.count(EnrollmentFact.id).label("enrollment_count"),
        )
        .group_by(EnrollmentFact.course_id)
        .order_by(func.count(EnrollmentFact.id).desc())
        .limit(limit)
    )
    return [{"course_id": row.course_id, "enrollment_count": row.enrollment_count} for row in rows]


async def avg_courses_per_student(db: AsyncSession) -> float:
    total = await db.scalar(select(func.count(EnrollmentFact.id))) or 0
    students = await db.scalar(
        select(func.count(func.distinct(EnrollmentFact.student_id)))
    ) or 0
    if students == 0:
        return 0.0
    return round(total / students, 2)


async def count_failed_events(db: AsyncSession) -> int:
    result = await db.scalar(select(func.count(FailedEvent.id)))
    return result or 0


async def recent_failed_events(db: AsyncSession, limit: int = 20) -> list[dict]:
    rows = await db.execute(
        select(FailedEvent)
        .order_by(FailedEvent.failed_at.desc())
        .limit(limit)
    )
    return [
        {
            "id": r.id,
            "event_type": r.event_type,
            "error_message": r.error_message,
            "failed_at": r.failed_at.isoformat(),
        }
        for r in rows.scalars()
    ]

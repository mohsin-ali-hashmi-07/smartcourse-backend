from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.models.enrollment import Enrollment, Progress

async def get_enrollment_by_id(
    db: AsyncSession, enrollment_id: str
) -> Enrollment | None:
    result = await db.execute(
        select(Enrollment)
        .where(Enrollment.id == enrollment_id)
        .options(selectinload(Enrollment.progress))
    )
    return result.scalar_one_or_none()


async def get_enrollment_by_student_and_course(
    db: AsyncSession, student_id: str, course_id: str
) -> Enrollment | None:
    result = await db.execute(
        select(Enrollment)
        .where(Enrollment.student_id == student_id)
        .where(Enrollment.course_id == course_id)
        .options(selectinload(Enrollment.progress))
    )
    return result.scalar_one_or_none()

async def get_enrollments_by_student(
    db: AsyncSession, student_id: str
) -> list[Enrollment]:
    result = await db.execute(
        select(Enrollment)
        .where(Enrollment.student_id == student_id)
        .options(selectinload(Enrollment.progress))
    )
    return list(result.scalars().all())


async def get_enrollments_by_course(
    db: AsyncSession, course_id: str
) -> list[Enrollment]:
    result = await db.execute(
        select(Enrollment)
        .where(Enrollment.course_id == course_id)
        .options(selectinload(Enrollment.progress))
    )
    return list(result.scalars().all())

async def create_enrollment(
    db: AsyncSession, enrollment: Enrollment
) -> Enrollment:
    db.add(enrollment)
    await db.flush()
    await db.refresh(enrollment, ["progress"])
    return enrollment


async def update_enrollment(
    db: AsyncSession, enrollment: Enrollment, updates: dict
) -> Enrollment:
    for field, value in updates.items():
        setattr(enrollment, field, value)
    await db.flush()
    await db.refresh(enrollment)
    return enrollment

async def get_progress_by_enrollment(
    db: AsyncSession, enrollment_id: str
) -> Progress | None:
    result = await db.execute(
        select(Progress).where(Progress.enrollment_id == enrollment_id)
    )
    return result.scalar_one_or_none()


async def create_progress(db: AsyncSession, progress: Progress) -> Progress:
    db.add(progress)
    await db.flush()
    await db.refresh(progress)
    return progress


async def update_progress(
    db: AsyncSession, progress: Progress, updates: dict
) -> Progress:
    for field, value in updates.items():
        setattr(progress, field, value)
    await db.flush()
    await db.refresh(progress)
    return progress
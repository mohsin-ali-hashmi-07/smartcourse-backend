import uuid
import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enrollment import Enrollment, Progress
from app.schemas.enrollment import EnrollmentCreate, EnrollmentUpdate
from app.repositories import enrollment_repository
from app.core.settings import settings
from app.core.kafka_producer import get_producer

async def enroll_student(db: AsyncSession, data: EnrollmentCreate) -> Enrollment:
    """
    Creates only the enrollment DB record.
    Verification, progress init, and Kafka are handled by enrollment_orchestrator.
    """
    existing = await enrollment_repository.get_enrollment_by_student_and_course(
        db, data.student_id, data.course_id
    )
    if existing:
        return existing

    enrollment = Enrollment(
        id=str(uuid.uuid4()),
        student_id=data.student_id,
        course_id=data.course_id,
        status="active",
    )
    return await enrollment_repository.create_enrollment(db, enrollment)


async def enroll_student_atomic(
    db: AsyncSession, student_id: str, course_id: str, total_modules: int
) -> Enrollment:
    """
    Atomically creates Enrollment + Progress in a single DB transaction.
    Idempotent: if the (student_id, course_id) pair already exists, returns
    the existing record without re-inserting anything.
    """
    existing = await enrollment_repository.get_enrollment_by_student_and_course(
        db, student_id, course_id
    )
    if existing:
        return existing

    enrollment_id = str(uuid.uuid4())
    enrollment = Enrollment(
        id=enrollment_id,
        student_id=student_id,
        course_id=course_id,
        status="active",
    )
    progress = Progress(
        id=str(uuid.uuid4()),
        enrollment_id=enrollment_id,
        completed_modules=0,
        total_modules=total_modules,
    )
    return await enrollment_repository.create_enrollment_with_progress(db, enrollment, progress)


async def init_progress(
    db: AsyncSession, enrollment_id: str, total_modules: int
) -> Progress:
    """
    Initializes a progress record for an existing enrollment.
    Called by enrollment_orchestrator after create_enrollment succeeds.
    """
    enrollment = await enrollment_repository.get_enrollment_by_id(db, enrollment_id)
    if not enrollment:
        raise ValueError(f"enrollment not found: {enrollment_id}")

    existing = await enrollment_repository.get_progress_by_enrollment(db, enrollment_id)
    if existing:
        return existing  # idempotent — already initialized

    progress = Progress(
        id=str(uuid.uuid4()),
        enrollment_id=enrollment_id,
        completed_modules=0,
        total_modules=total_modules,
    )
    return await enrollment_repository.create_progress(db, progress)


async def hard_delete_enrollment(db: AsyncSession, enrollment_id: str) -> None:
    """
    SAGA COMPENSATION — permanently deletes an enrollment record.
    Called by enrollment_orchestrator when init_progress fails,
    to roll back the create_enrollment step.
    """
    enrollment = await enrollment_repository.get_enrollment_by_id(db, enrollment_id)
    if not enrollment:
        return  # already gone — idempotent
    await enrollment_repository.delete_enrollment(db, enrollment)

async def get_enrollment(db: AsyncSession, enrollment_id: str) -> Enrollment:
    enrollment = await enrollment_repository.get_enrollment_by_id(db, enrollment_id)
    if not enrollment:
        raise ValueError(f"enrollment not found: {enrollment_id}")
    return enrollment


async def list_enrollments_by_student(
    db: AsyncSession, student_id: str
) -> list[Enrollment]:
    return await enrollment_repository.get_enrollments_by_student(db, student_id)


async def list_enrollments_by_course(
    db: AsyncSession, course_id: str
) -> list[Enrollment]:
    return await enrollment_repository.get_enrollments_by_course(db, course_id)

async def drop_enrollment(db: AsyncSession, enrollment_id: str) -> Enrollment:
    enrollment = await enrollment_repository.get_enrollment_by_id(db, enrollment_id)
    if not enrollment:
        raise ValueError(f"enrollment not found: {enrollment_id}")
    if enrollment.status == "dropped":
        raise ValueError("enrollment is already dropped")
    return await enrollment_repository.update_enrollment(
        db, enrollment, {"status": "dropped"}
    )

async def complete_module(
    db: AsyncSession, enrollment_id: str
) -> Progress:
    enrollment = await enrollment_repository.get_enrollment_by_id(db, enrollment_id)
    if not enrollment:
        raise ValueError(f"enrollment not found: {enrollment_id}")
    if enrollment.status != "active":
        raise ValueError("can only update progress on an active enrollment")

    progress = await enrollment_repository.get_progress_by_enrollment(db, enrollment_id)
    if not progress:
        raise ValueError(f"progress not found for enrollment: {enrollment_id}")

    if progress.completed_modules >= progress.total_modules:
        raise ValueError("all modules are already completed")

    new_completed = progress.completed_modules + 1

    updated_progress = await enrollment_repository.update_progress(
        db, progress, {
            "completed_modules": new_completed,
        }
    )

    # Mark enrollment as completed if all modules done
    if new_completed >= progress.total_modules:
        await enrollment_repository.update_enrollment(
            db, enrollment, {"status": "completed"}
        )

    producer = get_producer()
    if producer:
        await producer.send(
            "progress.updated",
            {
                "event":"progress.updated",
                "enrollment_id": enrollment_id,
                "student_id": enrollment.student_id,
                "course_id": enrollment.course_id,
                "completed_modules": new_completed,
                "total_modules": progress.total_modules,
            }
        )

    return updated_progress

async def _verify_course_published(course_id: str) -> None:
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(
                f"{settings.course_service_url}/api/v1/courses/{course_id}",
                timeout=5.0,
            )
        except httpx.ConnectError:
            raise ValueError("course_service is unreachable")

    if response.status_code == 404:
        raise ValueError(f"course not found: {course_id}")
    if response.status_code != 200:
        raise ValueError(f"could not verify course: {course_id}")

    course = response.json()
    if course["status"] != "published":
        raise ValueError(f"course is not published: {course_id}")


async def _get_course_module_count(course_id: str) -> int:
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(
                f"{settings.course_service_url}/api/v1/courses/{course_id}",
                timeout=5.0,
            )
        except httpx.ConnectError:
            return 0

    if response.status_code != 200:
        return 0

    course = response.json()
    return len(course.get("modules", []))
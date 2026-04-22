import uuid
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.course import Course, Module
from app.schemas.course import CourseCreate, CourseUpdate, ModuleCreate, ModuleUpdate
from app.repositories import course_repository
from app.constants.course_status import COURSE_STATUS

async def create_course(db: AsyncSession, data: CourseCreate) -> Course:
    course = Course(
        id=str(uuid.uuid4()),
        title=data.title,
        description=data.description,
        instructor_id=data.instructor_id,
        status="draft",
    )
    return await course_repository.create_course(db, course.__dict__ | {})


async def get_course(db: AsyncSession, course_id: str) -> Course:
    course = await course_repository.get_course_by_id(db, course_id)
    if not course:
        raise ValueError(f"course not found: {course_id}")
    return course


async def list_courses(db: AsyncSession) -> list[Course]:
    return await course_repository.get_all_courses(db)

async def list_courses_by_instructor(
    db: AsyncSession, instructor_id: str
) -> list[Course]:
    return await course_repository.get_courses_by_instructor(db, instructor_id)

async def update_course(
    db: AsyncSession, course_id: str, data: CourseUpdate
) -> Course:
    course = await course_repository.get_course_by_id(db, course_id)
    if not course:
        raise ValueError(f"course not found: {course_id}")

    updates = data.model_dump(exclude_unset=True)

    if "status" in updates:
        _validate_status_transition(course.status, updates["status"])

    return await course_repository.update_course(db, course, updates)

async def delete_course(db: AsyncSession, course_id: str) -> None:
    course = await course_repository.get_course_by_id(db, course_id)
    if not course:
        raise ValueError(f"course not found: {course_id}")

    if course.status == "published":
        raise ValueError("cannot delete a published course")

    await course_repository.delete_course(db, course)

async def create_module(
    db: AsyncSession, course_id: str, data: ModuleCreate
) -> Module:
    course = await course_repository.get_course_by_id(db, course_id)
    if not course:
        raise ValueError(f"course not found: {course_id}")

    module = Module(
        id=str(uuid.uuid4()),
        course_id=course_id,
        title=data.title,
        description=data.description,
        order_index=data.order_index,
    )
    return await course_repository.create_module(db, module.__dict__ | {})

async def get_module(db: AsyncSession, module_id: str) -> Module:
    module = await course_repository.get_module_by_id(db, module_id)
    if not module:
        raise ValueError(f"module not found: {module_id}")
    return module


async def list_modules(db: AsyncSession, course_id: str) -> list[Module]:
    course = await course_repository.get_course_by_id(db, course_id)
    if not course:
        raise ValueError(f"course not found: {course_id}")
    return await course_repository.get_modules_by_course(db, course_id)

async def update_module(
    db: AsyncSession, module_id: str, data: ModuleUpdate
) -> Module:
    module = await course_repository.get_module_by_id(db, module_id)
    if not module:
        raise ValueError(f"module not found: {module_id}")

    updates = data.model_dump(exclude_unset=True)
    return await course_repository.update_module(db, module, updates)

async def delete_module(db: AsyncSession, module_id: str) -> None:
    module = await course_repository.get_module_by_id(db, module_id)
    if not module:
        raise ValueError(f"module not found: {module_id}")
    await course_repository.delete_module(db, module)

def _validate_status_transition(current: str, new: str) -> None:
    allowed_transitions: dict[str, list[str]] = {
        "draft":     ["published"],
        "published": ["archived"],
        "archived":  [],
    }
    if new not in allowed_transitions[current]:
        raise ValueError(
            f"invalid status transition: '{current}' → '{new}'. "
            f"Allowed: {allowed_transitions[current]}"
        )
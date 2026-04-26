import uuid
import json
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.course import Course, Module
from app.schemas.course import CourseCreate, CourseUpdate, ModuleCreate, ModuleUpdate
from app.repositories import course_repository
from app.constants.course_status import COURSE_STATUS
from app.core.redis_client import get_redis

CACHE_TTL = 300

def _cache_key(course_id: str) -> str:
    return f"course:{course_id}"

async def _set_course_cache(course: Course) -> None:
    redis = get_redis()
    if not redis:
        return
    data = {
        "id": course.id,
        "title": course.title,
        "description": course.description,
        "instructor_id": course.instructor_id,
        "status": course.status,
        "modules": [
            {
                "id": m.id,
                "course_id": m.course_id,
                "title": m.title,
                "description": m.description,
                "order_index": m.order_index,
            }
            for m in (course.modules or [])
        ],
    }
    await redis.set(_cache_key(course.id), json.dumps(data), ex=CACHE_TTL)

async def _delete_course_cache(course_id: str) -> None:
    redis = get_redis()
    if not redis:
        return
    await redis.delete(_cache_key(course_id))

async def create_course(db: AsyncSession, data: CourseCreate) -> Course:
    course = Course(
        id=str(uuid.uuid4()),
        title=data.title,
        description=data.description,
        instructor_id=data.instructor_id,
        status="draft",
    )
    course = await course_repository.create_course(db, course)
    await _set_course_cache(course)
    return course


async def get_course(db: AsyncSession, course_id: str) -> Course:
    redis = get_redis()
    if redis:
        cached = await redis.get(_cache_key(course_id))
        if cached:
            return json.loads(cached)
    course = await course_repository.get_course_by_id(db, course_id)
    if not course:
        raise ValueError(f"course not found: {course_id}")
    await _set_course_cache(course)
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

    course = await course_repository.update_course(db, course, updates)
    await _set_course_cache(course)
    return course

async def delete_course(db: AsyncSession, course_id: str) -> None:
    course = await course_repository.get_course_by_id(db, course_id)
    if not course:
        raise ValueError(f"course not found: {course_id}")

    if course.status == "published":
        raise ValueError("cannot delete a published course")

    await course_repository.delete_course(db, course)
    await _delete_course_cache(course_id)

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
    module = await course_repository.create_module(db, module)
    await _delete_course_cache(course_id)
    return module

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
    module = await course_repository.update_module(db, module, updates)
    await _delete_course_cache(module.course_id)
    return module

async def delete_module(db: AsyncSession, module_id: str) -> None:
    module = await course_repository.get_module_by_id(db, module_id)
    if not module:
        raise ValueError(f"module not found: {module_id}")
    course_id = module.course_id
    await course_repository.delete_module(db, module)
    await _delete_course_cache(course_id)

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
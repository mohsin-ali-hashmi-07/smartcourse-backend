from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.models.course import Course, Module

async def get_course_by_id(db: AsyncSession, course_id: str) -> Course | None:
    result = await db.execute(
        select(Course)
        .where(Course.id == course_id)
        .options(selectinload(Course.modules))
    )
    return result.scalar_one_or_none()

async def get_all_courses(db: AsyncSession) -> list[Course]:
    result = await db.execute(
        select(Course).options(selectinload(Course.modules))
    )
    return list(result.scalars().all())


async def get_courses_by_instructor(
    db: AsyncSession, instructor_id: str
) -> list[Course]:
    result = await db.execute(
        select(Course)
        .where(Course.instructor_id == instructor_id)
        .options(selectinload(Course.modules))
    )
    return list(result.scalars().all())

async def create_course(db: AsyncSession, data: dict) -> Course:
    course = Course(**data)
    db.add(course)
    await db.flush()
    await db.refresh(course)
    return course


async def update_course(db: AsyncSession, course: Course, updates: dict) -> Course:
    for field, value in updates.items():
        setattr(course, field, value)
    await db.flush()
    await db.refresh(course)
    return course


async def delete_course(db: AsyncSession, course: Course) -> None:
    await db.delete(course)
    await db.flush()

async def get_module_by_id(db: AsyncSession, module_id: str) -> Module | None:
    result = await db.execute(
        select(Module).where(Module.id == module_id)
    )
    return result.scalar_one_or_none()


async def get_modules_by_course(
    db: AsyncSession, course_id: str
) -> list[Module]:
    result = await db.execute(
        select(Module)
        .where(Module.course_id == course_id)
        .order_by(Module.order_index)
    )
    return list(result.scalars().all())

async def create_module(db: AsyncSession, data: dict) -> Module:
    module = Module(**data)
    db.add(module)
    await db.flush()
    await db.refresh(module)
    return module


async def update_module(
    db: AsyncSession, module: Module, updates: dict
) -> Module:
    for field, value in updates.items():
        setattr(module, field, value)
    await db.flush()
    await db.refresh(module)
    return module

async def delete_module(db: AsyncSession, module: Module) -> None:
    await db.delete(module)
    await db.flush()
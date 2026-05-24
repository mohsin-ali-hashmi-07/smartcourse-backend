from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from app.models.rbac import UserRole

async def get_user_roles(db: AsyncSession, user_id: str) -> list[UserRole]:
    result = await db.execute(
        select(UserRole).where(UserRole.user_id == user_id)
    )
    return list(result.scalars().all())


async def has_role(db: AsyncSession, user_id: str, role: str) -> bool:
    result = await db.execute(
        select(UserRole).where(
            UserRole.user_id == user_id,
            UserRole.role == role,
        )
    )
    return result.scalar_one_or_none() is not None

async def assign_role(
    db: AsyncSession, user_id: str, role: str, permissions: list[str]
) -> UserRole:
    user_role = UserRole(user_id=user_id, role=role, permissions=permissions)
    db.add(user_role)
    await db.flush()
    await db.refresh(user_role)
    return user_role


async def remove_role(db: AsyncSession, user_id: str, role: str) -> None:
    await db.execute(
        delete(UserRole).where(
            UserRole.user_id == user_id,
            UserRole.role == role,
        )
    )
    await db.flush()
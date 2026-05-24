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


async def replace_role(
    db: AsyncSession, user_id: str, role: str, permissions: list[str]
) -> None:
    """Delete all existing role rows for this user then insert the new one."""
    await db.execute(delete(UserRole).where(UserRole.user_id == user_id))
    await db.flush()
    db.add(UserRole(user_id=user_id, role=role, permissions=permissions))
    await db.flush()

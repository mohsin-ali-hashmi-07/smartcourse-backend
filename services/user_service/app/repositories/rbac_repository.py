from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from app.models.rbac import Role, UserRole


async def get_role_by_name(db: AsyncSession, name: str) -> Role | None:
    result = await db.execute(select(Role).where(Role.name == name))
    return result.scalar_one_or_none()


async def get_user_roles(db: AsyncSession, user_id: str) -> list[str]:
    """Return a list of role name strings for the given user."""
    result = await db.execute(
        select(Role.name)
        .join(UserRole, UserRole.role_id == Role.id)
        .where(UserRole.user_id == user_id)
    )
    return list(result.scalars().all())


async def has_role(db: AsyncSession, user_id: str, role: str) -> bool:
    result = await db.execute(
        select(UserRole)
        .join(Role, Role.id == UserRole.role_id)
        .where(UserRole.user_id == user_id, Role.name == role)
    )
    return result.scalar_one_or_none() is not None


async def replace_role(db: AsyncSession, user_id: str, role_name: str) -> None:
    """Remove all existing roles for the user and assign a single new one.
    Used only at registration."""
    role = await get_role_by_name(db, role_name)
    if not role:
        raise ValueError(f"role '{role_name}' does not exist in the roles table")
    await db.execute(delete(UserRole).where(UserRole.user_id == user_id))
    await db.flush()
    db.add(UserRole(user_id=user_id, role_id=role.id))
    await db.flush()


async def add_role(db: AsyncSession, user_id: str, role_name: str) -> None:
    """Add a role to the user without removing existing ones. Idempotent."""
    role = await get_role_by_name(db, role_name)
    if not role:
        raise ValueError(f"role '{role_name}' does not exist in the roles table")
    exists = await has_role(db, user_id, role_name)
    if not exists:
        db.add(UserRole(user_id=user_id, role_id=role.id))
        await db.flush()


async def remove_role(db: AsyncSession, user_id: str, role_name: str) -> None:
    """Remove a specific role from the user."""
    role = await get_role_by_name(db, role_name)
    if not role:
        raise ValueError(f"role '{role_name}' does not exist in the roles table")
    await db.execute(
        delete(UserRole).where(
            UserRole.user_id == user_id, UserRole.role_id == role.id
        )
    )
    await db.flush()

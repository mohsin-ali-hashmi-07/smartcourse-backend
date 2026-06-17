import uuid
import bcrypt
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timezone, timedelta
import jwt

from app.models.user import User
from app.schemas.user import UserCreate
from app.repositories import user_repository, rbac_repository
from app.constants.roles import USER_ROLES
from app.core.settings import settings


def hash_password(plain_password: str) -> str:
    return bcrypt.hashpw(plain_password.encode(), bcrypt.gensalt()).decode()


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return bcrypt.checkpw(plain_password.encode(), hashed_password.encode())

PERMISSIONS_MAP = {
    "student": ["courses:read", "enrollments:write"],
    "instructor": ["courses:write", "courses:read"],
    "admin": ["users:manage", "courses:write", "courses:read", "enrollments:read"],
}


async def register_user(db: AsyncSession, data: UserCreate) -> User:
    existing = await user_repository.get_user_by_email(db, data.email)
    if existing:
        raise ValueError(f"email already registered: {data.email}")

    user = User(
        id=str(uuid.uuid4()),
        email=data.email,
        hashed_password=hash_password(data.password),
        full_name=data.full_name,
        is_active=True,
    )
    user = await user_repository.create_user(db, user)

    await rbac_repository.replace_role(db, user.id, data.role)
    user.roles = [data.role]
    return user

async def get_user(db: AsyncSession, user_id: str) -> User:
    user = await user_repository.get_user_by_id(db, user_id)
    if not user:
        raise ValueError(f"user not found: {user_id}")
    user.roles = await rbac_repository.get_user_roles(db, user_id)
    return user

async def list_users(db: AsyncSession) -> list[User]:
    users = await user_repository.get_all_users(db)
    for u in users:
        u.roles = await rbac_repository.get_user_roles(db, u.id)
    return users


async def assign_role(db: AsyncSession, user_id: str, role: str) -> User:
    if role not in USER_ROLES:
        raise ValueError(f"invalid role: {role}. Must be one of {USER_ROLES}")

    user = await user_repository.get_user_by_id(db, user_id)
    if not user:
        raise ValueError(f"user not found: {user_id}")

    await rbac_repository.add_role(db, user_id, role)
    user.roles = await rbac_repository.get_user_roles(db, user_id)
    return user


async def revoke_role(db: AsyncSession, user_id: str, role: str) -> User:
    if role not in USER_ROLES:
        raise ValueError(f"invalid role: {role}. Must be one of {USER_ROLES}")

    user = await user_repository.get_user_by_id(db, user_id)
    if not user:
        raise ValueError(f"user not found: {user_id}")

    await rbac_repository.remove_role(db, user_id, role)
    user.roles = await rbac_repository.get_user_roles(db, user_id)
    return user

async def deactivate_user(db: AsyncSession, user_id: str) -> User:
    user = await user_repository.get_user_by_id(db, user_id)
    if not user:
        raise ValueError(f"user not found: {user_id}")

    user = await user_repository.deactivate_user(db, user)
    user.roles = await rbac_repository.get_user_roles(db, user_id)
    return user


def _create_access_token(user_id: str, roles: list[str]) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.jwt_expire_minutes)
    payload = {
        "sub": user_id,
        "roles": roles,
        "exp": expire,
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm="HS256")

async def login(db: AsyncSession, email: str, password: str) -> dict:
    user = await user_repository.get_user_by_email(db, email)
    if not user or not verify_password(password, user.hashed_password):
        raise ValueError("invalid email or password")
    if not user.is_active:
        raise ValueError("account is deactivated")

    roles = await rbac_repository.get_user_roles(db, user.id)
    if not roles:
        raise ValueError("user has no assigned role")

    token = _create_access_token(user.id, roles)
    return {
        "access_token": token,
        "token_type": "bearer",
        "user_id": user.id,
        "roles": roles,
    }
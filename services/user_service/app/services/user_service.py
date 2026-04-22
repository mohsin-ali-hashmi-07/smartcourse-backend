import uuid
import bcrypt
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.schemas.user import UserCreate
from app.repositories import user_repository
from app.constants.roles import USER_ROLES


def hash_password(plain_password: str) -> str:
    return bcrypt.hashpw(plain_password.encode(), bcrypt.gensalt()).decode()


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return bcrypt.checkpw(plain_password.encode(), hashed_password.encode())

async def register_user(db: AsyncSession, data: UserCreate) -> User:
    existing = await user_repository.get_user_by_email(db, data.email)
    if existing:
        raise ValueError(f"email already registered: {data.email}")
    
    user = User(
        id=str(uuid.uuid4()),
        email=data.email,
        hashed_password=hash_password(data.password),
        full_name=data.full_name,
        role=data.role,
        is_active=True
    )
    return await user_repository.create_user(db, user)

async def get_user(db: AsyncSession, user_id:str) -> User:
    user= await user_repository.get_user_by_id(db, user_id)
    if not user:
        raise ValueError(f"user not found: {user_id}")
    return user

async def list_users(db: AsyncSession) -> list[User]:
    return await user_repository.get_all_users(db)


async def assign_role(db: AsyncSession, user_id: str, role: str) -> User:
    if role not in USER_ROLES:
        raise ValueError(f"invalid role: {role}. Must be one of {USER_ROLES}")

    user = await user_repository.get_user_by_id(db, user_id)
    if not user:
        raise ValueError(f"user not found: {user_id}")

    return await user_repository.update_user_role(db, user, role)

async def deactivate_user(db: AsyncSession, user_id: str) -> User:
    user = await user_repository.get_user_by_id(db, user_id)
    if not user:
        raise ValueError(f"user not found: {user_id}")

    return await user_repository.deactivate_user(db, user)
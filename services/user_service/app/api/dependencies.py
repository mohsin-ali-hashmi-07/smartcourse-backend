import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../")))

from typing import AsyncGenerator
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import AsyncSessionLocal
from app.core.settings import settings
from app.repositories import rbac_repository
from shared.utils.auth import verify_token, TokenData

bearer_scheme = HTTPBearer()


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
) -> TokenData:
    return verify_token(settings.jwt_secret, credentials.credentials)


async def require_admin(
    current_user: TokenData = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> TokenData:
    if not await rbac_repository.has_role(db, current_user.user_id, "admin"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="only admins can perform this action",
        )
    return current_user


async def require_instructor(
    current_user: TokenData = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> TokenData:
    is_instructor = await rbac_repository.has_role(db, current_user.user_id, "instructor")
    is_admin = await rbac_repository.has_role(db, current_user.user_id, "admin")
    if not (is_instructor or is_admin):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="only instructors can perform this action",
        )
    return current_user


async def require_student(
    current_user: TokenData = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> TokenData:
    if not await rbac_repository.has_role(db, current_user.user_id, "student"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="only students can perform this action",
        )
    return current_user
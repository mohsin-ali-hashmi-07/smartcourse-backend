from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_db, require_admin
from app.repositories import rbac_repository
from app.schemas.user import UserResponse, UserRoleUpdate
from app.services import user_service
from shared.utils.auth import TokenData

router = APIRouter(prefix="/rbac", tags=["rbac"])


@router.patch("/users/{user_id}/role", response_model=UserResponse)
async def assign_role(
    user_id: str,
    data: UserRoleUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: TokenData = Depends(require_admin),
):
    try:
        user = await user_service.assign_role(db, user_id, data.role)
        return UserResponse.model_validate(user)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("/users/{user_id}/roles")
async def get_user_roles(
    user_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: TokenData = Depends(require_admin),
):
    roles = await rbac_repository.get_user_roles(db, user_id)
    return [{"role": r.role, "permissions": r.permissions} for r in roles]

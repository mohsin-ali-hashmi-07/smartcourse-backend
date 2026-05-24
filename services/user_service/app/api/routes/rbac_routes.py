from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel

from app.api.dependencies import get_db, require_admin
from app.repositories import rbac_repository
from shared.utils.auth import TokenData

router = APIRouter(prefix="/rbac", tags=["rbac"])

class AssignRoleRequest(BaseModel):
    user_id: str
    role: str
    permissions: list[str] = []


class RemoveRoleRequest(BaseModel):
    user_id: str
    role: str

@router.post("/assign", status_code=status.HTTP_201_CREATED)
async def assign_role(
    data: AssignRoleRequest,
    db: AsyncSession = Depends(get_db),
    current_user: TokenData = Depends(require_admin),
):
    try:
        user_role = await rbac_repository.assign_role(
            db, data.user_id, data.role, data.permissions
        )
        return {"user_id": user_role.user_id, "role": user_role.role, "permissions": user_role.permissions}
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="user already has this role",
        )

@router.delete("/remove", status_code=status.HTTP_204_NO_CONTENT)
async def remove_role(
    data: RemoveRoleRequest,
    db: AsyncSession = Depends(get_db),
    current_user: TokenData = Depends(require_admin),
):
    await rbac_repository.remove_role(db, data.user_id, data.role)

@router.get("/users/{user_id}/roles")
async def get_user_roles(
    user_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: TokenData = Depends(require_admin),
):
    roles = await rbac_repository.get_user_roles(db, user_id)
    return [{"role": r.role, "permissions": r.permissions} for r in roles]
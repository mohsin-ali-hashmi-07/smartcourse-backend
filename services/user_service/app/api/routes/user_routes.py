from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_db
from app.schemas.user import UserCreate, UserResponse, UserRoleUpdate
from app.services import user_service

router = APIRouter(prefix="/users", tags=["users"])

@router.post("/", response_model= UserResponse, status_code= status.HTTP_201_CREATED)
async def register_user(
    data: UserCreate,
    db: AsyncSession = Depends(get_db),
):
    try:
        user = await user_service.register_user(db, data)
        return UserResponse.model_validate(user)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))
    
@router.get("/", response_model=list[UserResponse])
async def list_users(db: AsyncSession = Depends(get_db)):
    users = await user_service.list_users(db)
    return [UserResponse.model_validate(u) for u in users]

@router.get("/{user_id}", response_model=UserResponse)
async def get_user(user_id: str, db: AsyncSession = Depends(get_db)):
    try:
        user = await user_service.get_user(db, user_id)
        return UserResponse.model_validate(user)
    except ValueError as e:
        raise HTTPException(status_code= status.HTTP_404_NOT_FOUND, detail=str(e))
    
@router.patch("/{user_id}/role", response_model=UserResponse)
async def assign_role(
    user_id: str,
    data: UserRoleUpdate,
    db: AsyncSession = Depends(get_db),
):
    try:
        user = await user_service.assign_role(db, user_id, data.role)
        return UserResponse.model_validate(user)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    
@router.delete("/{user_id}", response_model=UserResponse)
async def deactivate_user(user_id: str, db: AsyncSession = Depends(get_db)):
    try:
        user = await user_service.deactivate_user(db, user_id)
        return UserResponse.model_validate(user)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail = str(e))
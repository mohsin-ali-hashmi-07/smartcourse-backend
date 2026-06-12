from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_db, get_current_user, require_admin
from app.schemas.user import UserCreate, UserResponse
from shared.utils.auth import TokenData
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
    
@router.get("/admin", response_model=list[UserResponse])
async def list_users(db: AsyncSession = Depends(get_db), current_user: TokenData = Depends(require_admin),):
    users = await user_service.list_users(db)
    return [UserResponse.model_validate(u) for u in users]

@router.get("/me", response_model=UserResponse)
async def get_me(db: AsyncSession = Depends(get_db), current_user: TokenData = Depends(get_current_user)):
    try:
        user = await user_service.get_user(db, current_user.user_id)
        return UserResponse.model_validate(user)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))

@router.get("/admin/{user_id}", response_model=UserResponse)
async def get_user_by_id(user_id: str, db: AsyncSession = Depends(get_db), current_user: TokenData = Depends(require_admin)):
    try:
        user = await user_service.get_user(db, user_id)
        return UserResponse.model_validate(user)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))

@router.delete("/admin/{user_id}", response_model=UserResponse)
async def deactivate_user(user_id: str, db: AsyncSession = Depends(get_db), current_user: TokenData = Depends(require_admin)):
    try:
        user = await user_service.deactivate_user(db, user_id)
        return UserResponse.model_validate(user)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
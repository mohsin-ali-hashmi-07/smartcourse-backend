from datetime import datetime
from typing import Optional
from pydantic import BaseModel, EmailStr, field_validator
from app.constants.roles import USER_ROLES

class UserCreate(BaseModel):
    email: EmailStr
    password: str
    full_name: Optional[str] = None
    role: str = "student"

    @field_validator("role")
    @classmethod
    def validate_role(cls, value: str) -> str:
        if value not in USER_ROLES:
            raise ValueError(f"role must be one of {USER_ROLES}")
        return value
    
    @field_validator("password")
    @classmethod
    def validate_password(cls,value:str) -> str:
        if len(value) < 8:
            raise ValueError(f"passwod should be greater then 8 characters")
        return value
    
class UserRoleUpdate(BaseModel):
    role: str

    @field_validator("role")
    @classmethod
    def validate_role(cls, value:str) -> str:
        if value not in USER_ROLES:
            raise ValueError(f"role must be one of {USER_ROLES}")
        return value
    
class UserResponse(BaseModel):
    id: str
    email: str
    full_name: Optional[str]
    role: str
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
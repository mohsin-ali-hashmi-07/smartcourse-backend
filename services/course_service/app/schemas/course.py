from datetime import datetime
from pydantic import BaseModel, ConfigDict, field_validator

from app.constants.course_status import COURSE_STATUS

class ModuleBase(BaseModel):
    title: str
    description: str | None = None
    order_index: int = 0


class ModuleCreate(ModuleBase):
    @field_validator("title")
    @classmethod
    def validate_title(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("title must not be blank")
        return value


class ModuleUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
    order_index: int | None = None


class ModuleResponse(ModuleBase):
    model_config = ConfigDict(from_attributes=True)

    id: str
    course_id: str
    created_at: datetime
    updated_at: datetime


class CourseBase(BaseModel):
    title: str
    description: str | None = None
    instructor_id: str


class CourseCreate(CourseBase):
    @field_validator("title")
    @classmethod
    def validate_title(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("title must not be blank")
        return value


class CourseUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
    status: str | None = None

    @field_validator("status")
    @classmethod
    def validate_status(cls, value: str | None) -> str | None:
        if value is not None and value not in COURSE_STATUS:
            raise ValueError(f"status must be one of {COURSE_STATUS}")
        return value


class CourseResponse(CourseBase):
    model_config = ConfigDict(from_attributes=True)

    id: str
    status: str
    modules: list[ModuleResponse] = []
    created_at: datetime
    updated_at: datetime
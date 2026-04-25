from datetime import datetime
from pydantic import BaseModel, ConfigDict, field_validator

from app.constants.enrollment_status import ENROLLMENT_STATUSES

class ProgressResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    enrollment_id: str
    completed_modules: int
    total_modules: int
    completion_percentage: float
    created_at: datetime
    updated_at: datetime

class EnrollmentBase(BaseModel):
    student_id: str
    course_id: str

class EnrollmentCreate(EnrollmentBase):
    pass

class EnrollmentUpdate(BaseModel):
    status: str | None = None

    @field_validator("status")
    @classmethod
    def validate_status(cls, value: str | None) -> str | None:
        if value is not None and value not in ENROLLMENT_STATUSES:
            raise ValueError(f"status must be one of {ENROLLMENT_STATUSES}")
        return value

class EnrollmentResponse(EnrollmentBase):
    model_config = ConfigDict(from_attributes=True)

    id: str
    status: str
    progress: ProgressResponse | None = None
    created_at: datetime
    updated_at: datetime
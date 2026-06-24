from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from temporalio.client import Client as TemporalClient
from temporalio.service import RPCError
import uuid

from app.api.dependencies import get_db, get_current_user, require_student, require_admin
from app.schemas.enrollment import (
    EnrollmentCreate, CourseEnrollRequest, AtomicEnrollRequest,
    ProgressCreate, EnrollmentResponse, ProgressResponse
)
from shared.utils.auth import TokenData
from app.services import enrollment_service
from app.core.settings import settings

router = APIRouter(prefix="/enrollments", tags=["enrollments"])

@router.post("/", status_code=status.HTTP_202_ACCEPTED)
async def enroll_student(
    data: CourseEnrollRequest,
    db: AsyncSession = Depends(get_db),
    current_user: TokenData = Depends(require_student),
):
    """
    Start enrollment via Temporal workflow.
    DB is the source of truth for idempotency — if an active/completed enrollment
    already exists the workflow is not started and the existing record is returned.
    A unique workflow ID is generated per attempt so a cancelled/terminated
    workflow can always be retried without hitting Temporal ID conflicts.
    """
    student_id = current_user.user_id

    existing = await enrollment_service.get_existing_enrollment(db, student_id, data.course_id)
    if existing:
        return {
            "workflow_id": None,
            "status": existing.status,
            "message": "already enrolled",
            "enrollment_id": existing.id,
        }

    try:
        client = await TemporalClient.connect(settings.temporal_host)
        workflow_id = f"enrollment-{student_id}-{data.course_id}-{uuid.uuid4()}"
        handle = await client.start_workflow(
            "EnrollmentWorkflow",
            args=[student_id, data.course_id],
            id=workflow_id,
            task_queue=settings.temporal_task_queue,
            execution_timeout=timedelta(seconds=settings.temporal_workflow_timeout),
        )
        return {
            "workflow_id": handle.id,
            "status": "started",
            "message": "enrollment workflow initiated",
        }
    except RPCError as e:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


# ── Internal endpoints (called by orchestrator, no JWT auth) ────────────────────

@router.post("/internal/create", response_model=EnrollmentResponse, status_code=status.HTTP_201_CREATED)
async def internal_create_enrollment(
    data: EnrollmentCreate,
    db: AsyncSession = Depends(get_db),
):
    """Internal — called by enrollment_orchestrator to create the DB record."""
    try:
        enrollment = await enrollment_service.enroll_student(db, data)
        return EnrollmentResponse.model_validate(enrollment)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/internal/enroll", response_model=EnrollmentResponse, status_code=status.HTTP_201_CREATED)
async def internal_enroll_atomic(
    data: AtomicEnrollRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Internal — called by enrollment_orchestrator.
    Creates Enrollment + Progress atomically in one DB transaction.
    Idempotent: safe for Temporal retries.
    """
    try:
        enrollment = await enrollment_service.enroll_student_atomic(
            db, data.student_id, data.course_id, data.total_modules
        )
        return EnrollmentResponse.model_validate(enrollment)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("/{enrollment_id}", response_model=EnrollmentResponse)
async def get_enrollment(
    enrollment_id: str,
    db: AsyncSession = Depends(get_db),
):
    try:
        enrollment = await enrollment_service.get_enrollment(db, enrollment_id)
        return EnrollmentResponse.model_validate(enrollment)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))

@router.get("/my-enrollments", response_model=list[EnrollmentResponse])
async def list_my_enrollments(
    db: AsyncSession = Depends(get_db),
    current_user: TokenData = Depends(require_student),
):
    enrollments = await enrollment_service.list_enrollments_by_student(db, current_user.user_id)
    return [EnrollmentResponse.model_validate(e) for e in enrollments]


@router.get("/admin/student/{student_id}", response_model=list[EnrollmentResponse])
async def list_by_student(
    student_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: TokenData = Depends(require_admin),
):
    enrollments = await enrollment_service.list_enrollments_by_student(db, student_id)
    return [EnrollmentResponse.model_validate(e) for e in enrollments]


@router.get("/admin/course/{course_id}", response_model=list[EnrollmentResponse])
async def list_by_course(
    course_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: TokenData = Depends(require_admin),
):
    enrollments = await enrollment_service.list_enrollments_by_course(db, course_id)
    return [EnrollmentResponse.model_validate(e) for e in enrollments]

@router.post(
    "/{enrollment_id}/progress",
    response_model=ProgressResponse,
    status_code=status.HTTP_201_CREATED,
)
async def init_progress(
    enrollment_id: str,
    data: ProgressCreate,
    db: AsyncSession = Depends(get_db),
):
    try:
        progress = await enrollment_service.init_progress(db, enrollment_id, data.total_modules)
        return ProgressResponse.model_validate(progress)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.delete("/{enrollment_id}", status_code=status.HTTP_204_NO_CONTENT)
async def hard_delete_enrollment(
    enrollment_id: str,
    db: AsyncSession = Depends(get_db),
):
    await enrollment_service.hard_delete_enrollment(db, enrollment_id)


@router.patch("/{enrollment_id}/drop", response_model=EnrollmentResponse)
async def drop_enrollment(
    enrollment_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: TokenData = Depends(require_student),
):
    try:
        enrollment = await enrollment_service.get_enrollment(db, enrollment_id)
        if enrollment.student_id != current_user.user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="you can only drop your own enrollment",
            )
        enrollment = await enrollment_service.drop_enrollment(db, enrollment_id)
        return EnrollmentResponse.model_validate(enrollment)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

@router.post(
    "/{enrollment_id}/progress/complete-module",
    response_model=ProgressResponse,
)
async def complete_module(
    enrollment_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: TokenData = Depends(require_student),
):
    try:
        progress = await enrollment_service.complete_module(db, enrollment_id)
        return ProgressResponse.model_validate(progress)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

@router.get(
    "/{enrollment_id}/progress",
    response_model=ProgressResponse,
)
async def get_progress(
    enrollment_id: str,
    db: AsyncSession = Depends(get_db),
):
    try:
        enrollment = await enrollment_service.get_enrollment(db, enrollment_id)
        if not enrollment.progress:
            raise ValueError(f"progress not found for enrollment: {enrollment_id}")
        return ProgressResponse.model_validate(enrollment.progress)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
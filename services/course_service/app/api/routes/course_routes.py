from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from temporalio.client import Client as TemporalClient
from temporalio.service import RPCError
import uuid

from app.api.dependencies import get_db, get_current_user, require_instructor, get_temporal_client
from app.schemas.course import (
    CourseCreate, CourseUpdate, CourseResponse,
    ModuleCreate, ModuleUpdate, ModuleResponse,
)
from shared.utils.auth import TokenData
from app.services import course_service
from app.core import minio_client
from app.core.settings import settings

bearer_scheme = HTTPBearer()

router = APIRouter(prefix="/courses", tags=["courses"])

@router.post("/", response_model=CourseResponse, status_code=status.HTTP_201_CREATED)
async def create_course(
    data: CourseCreate,
    db: AsyncSession = Depends(get_db),
    current_user: TokenData = Depends(require_instructor),
):
    try:
        course = await course_service.create_course(db, data)
        return CourseResponse.model_validate(course)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("/", response_model=list[CourseResponse])
async def list_courses(db: AsyncSession = Depends(get_db)):
    courses = await course_service.list_courses(db)
    return [CourseResponse.model_validate(c) for c in courses]

@router.get("/my-courses", response_model=list[CourseResponse])
async def list_my_courses(
    db: AsyncSession = Depends(get_db),
    current_user: TokenData = Depends(require_instructor),
):
    courses = await course_service.list_courses_by_instructor(db, current_user.user_id)
    return [CourseResponse.model_validate(c) for c in courses]


@router.get("/{course_id}", response_model=CourseResponse)
async def get_course(course_id: str, db: AsyncSession = Depends(get_db)):
    try:
        course = await course_service.get_course(db, course_id)
        return CourseResponse.model_validate(course)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))

@router.patch("/{course_id}", response_model=CourseResponse)
async def update_course(
    course_id: str,
    data: CourseUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: TokenData = Depends(require_instructor),
):
    try:
        course = await course_service.update_course(db, course_id, data)
        return CourseResponse.model_validate(course)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/{course_id}/publish", status_code=status.HTTP_202_ACCEPTED)
async def publish_course(
    course_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: TokenData = Depends(require_instructor),
    temporal_client: TemporalClient = Depends(get_temporal_client),
):
    try:
        course = await course_service.get_course(db, course_id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))

    course_status = course.get("status") if isinstance(course, dict) else course.status
    if course_status == "published":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="course is already published",
        )

    workflow_id = f"publish-course-{course_id}-{uuid.uuid4()}"
    try:
        handle = await temporal_client.start_workflow(
            "CoursePublishWorkflow",
            args=[course_id],
            id=workflow_id,
            task_queue=settings.temporal_task_queue,
            execution_timeout=timedelta(seconds=settings.temporal_workflow_timeout),
        )
        from app.schemas.course import CourseUpdate
        await course_service.update_course(db, course_id, CourseUpdate(status="publishing"))
        return {
            "workflow_id": handle.id,
            "status": "publishing",
            "message": "course publish workflow initiated",
        }
    except RPCError as e:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.delete("/{course_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_course(
    course_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: TokenData = Depends(require_instructor),
):
    try:
        await course_service.delete_course(db, course_id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

@router.post(
    "/{course_id}/modules",
    response_model=ModuleResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_module(
    course_id: str,
    data: ModuleCreate,
    db: AsyncSession = Depends(get_db),
    current_user: TokenData = Depends(require_instructor),
):
    try:
        module = await course_service.create_module(db, course_id, data)
        return ModuleResponse.model_validate(module)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))

@router.get("/{course_id}/modules", response_model=list[ModuleResponse])
async def list_modules(course_id: str, db: AsyncSession = Depends(get_db)):
    try:
        modules = await course_service.list_modules(db, course_id)
        return [ModuleResponse.model_validate(m) for m in modules]
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.get("/{course_id}/modules/{module_id}", response_model=ModuleResponse)
async def get_module(
    course_id: str,
    module_id: str,
    db: AsyncSession = Depends(get_db),
):
    try:
        module = await course_service.get_module(db, module_id)
        return ModuleResponse.model_validate(module)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))

@router.patch("/{course_id}/modules/{module_id}", response_model=ModuleResponse)
async def update_module(
    course_id: str,
    module_id: str,
    data: ModuleUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: TokenData = Depends(require_instructor),
):
    try:
        module = await course_service.update_module(db, module_id, data)
        return ModuleResponse.model_validate(module)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

@router.delete(
    "/{course_id}/modules/{module_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_module(
    course_id: str,
    module_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: TokenData = Depends(require_instructor),
):
    try:
        await course_service.delete_module(db, module_id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


# ── MinIO file upload ──────────────────────────────────────────────────────────

ALLOWED_CONTENT_TYPES = {
    "application/pdf",
    "video/mp4",
    "video/webm",
    "image/png",
    "image/jpeg",
}

@router.post(
    "/{course_id}/modules/{module_id}/upload",
    status_code=status.HTTP_200_OK,
)
async def upload_module_material(
    course_id: str,
    module_id: str,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: TokenData = Depends(require_instructor),
):
    if file.content_type not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=f"unsupported file type: {file.content_type}. Allowed: pdf, mp4, webm, png, jpeg",
        )

    try:
        data = await file.read()
        object_key = f"modules/{module_id}/{file.filename}"
        await minio_client.upload_file(object_key, data, file.content_type)
        module = await course_service.set_module_material(db, module_id, object_key)
        url = await minio_client.get_presigned_url(object_key)
        return {
            "module_id": module.id,
            "object_key": object_key,
            "url": url,
            "expires_in": 3600,
        }
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.get(
    "/{course_id}/modules/{module_id}/material",
    status_code=status.HTTP_200_OK,
)
async def get_module_material(
    course_id: str,
    module_id: str,
    db: AsyncSession = Depends(get_db),
):
    try:
        module = await course_service.get_module(db, module_id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))

    if not module.material_url:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="no material uploaded for this module",
        )

    url = await minio_client.get_presigned_url(module.material_url)
    return {"url": url, "expires_in": 3600}


# ── Internal endpoints (called by orchestrator, no JWT auth) ────────────────────

@router.patch("/internal/{course_id}/publish", response_model=CourseResponse)
async def internal_publish_course(
    course_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Internal — called by course_orchestrator to flip publishing → published."""
    try:
        from app.schemas.course import CourseUpdate
        course = await course_service.update_course(
            db, course_id, CourseUpdate(status="published")
        )
        return CourseResponse.model_validate(course)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.patch("/internal/{course_id}/revert-to-draft", response_model=CourseResponse)
async def internal_revert_to_draft(
    course_id: str,
    db: AsyncSession = Depends(get_db),
):
    """
    Internal — called by course_orchestrator Saga to rollback on workflow failure.
    Idempotent — if course is already 'draft', returns it unchanged.
    """
    try:
        course = await course_service.get_course(db, course_id)
        # Idempotent: already reverted
        if isinstance(course, dict):
            current_status = course.get("status")
        else:
            current_status = course.status
        if current_status == "draft":
            return CourseResponse.model_validate(course)

        from app.schemas.course import CourseUpdate
        course = await course_service.update_course(
            db, course_id, CourseUpdate(status="draft")
        )
        return CourseResponse.model_validate(course)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
import json
import httpx
from temporalio import activity
from temporalio.exceptions import ApplicationError
from aiokafka import AIOKafkaProducer
from app.core.settings import settings


@activity.defn
async def verify_course_published(course_id: str) -> dict:
    """
    Call course_service to confirm the course exists and is published.
    Validation failures are non-retryable — they will not succeed on retry.
    Returns the course dict so the workflow can use module count etc.
    """
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{settings.course_service_url}/api/v1/courses/{course_id}",
            timeout=10.0,
        )

    if response.status_code == 404:
        raise ApplicationError(
            f"course not found: {course_id}", non_retryable=True
        )
    if response.status_code != 200:
        # Transient — let Temporal retry
        raise RuntimeError(f"course_service error: {response.status_code}")

    course = response.json()
    if course["status"] != "published":
        raise ApplicationError(
            f"course is not published: {course_id}", non_retryable=True
        )

    return course


@activity.defn
async def create_enrollment(student_id: str, course_id: str) -> dict:
    """
    Create a new enrollment record via enrollment_service API.
    The service generates the enrollment ID — we read it back from the response.
    Returns the full enrollment dict (including 'id') for the workflow to use.
    """
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{settings.enrollment_service_url}/api/v1/enrollments/internal/create",
            json={
                "student_id": student_id,
                "course_id": course_id,
            },
            timeout=10.0,
        )

    if response.status_code == 409:
        # Already enrolled — idempotent, treat as success
        return response.json()
    if response.status_code != 201:
        raise ValueError(
            f"failed to create enrollment: {response.text}"
        )

    return response.json()


@activity.defn
async def create_progress(enrollment_id: str, total_modules: int) -> dict:
    """
    Initialize a progress record for the enrollment via enrollment_service.
    Sends total_modules so the service knows how many modules exist.
    Called after enrollment is created successfully.
    """
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{settings.enrollment_service_url}/api/v1/enrollments/{enrollment_id}/progress",
            json={"total_modules": total_modules},
            timeout=10.0,
        )

    if response.status_code not in (200, 201):
        raise ValueError(
            f"failed to create progress for enrollment {enrollment_id}: {response.text}"
        )

    return response.json()


@activity.defn
async def delete_enrollment(enrollment_id: str) -> None:
    """
    COMPENSATING ACTIVITY — runs if any step after create_enrollment fails.
    Permanently deletes the enrollment so the system stays consistent.
    This is the Saga rollback step.
    """
    async with httpx.AsyncClient() as client:
        response = await client.delete(
            f"{settings.enrollment_service_url}/api/v1/enrollments/{enrollment_id}",
            timeout=10.0,
        )

    # 404 means already gone — that's fine for a compensating activity
    if response.status_code not in (200, 204, 404):
        raise ValueError(
            f"failed to delete enrollment {enrollment_id}: {response.text}"
        )


@activity.defn
async def emit_enrollment_created_event(
    enrollment_id: str, student_id: str, course_id: str
) -> None:
    """
    Emit enrollment.created event to Kafka after all steps succeed.
    Emitting last ensures the event only fires if enrollment + progress
    were both created successfully.
    """
    producer = AIOKafkaProducer(
        bootstrap_servers=settings.kafka_bootstrap_servers,
        value_serializer=lambda v: json.dumps(v).encode("utf-8"),
    )
    await producer.start()
    try:
        await producer.send(
            "enrollment.created",
            {
                "event": "enrollment.created",
                "enrollment_id": enrollment_id,
                "student_id": student_id,
                "course_id": course_id,
            },
        )
    finally:
        await producer.stop()

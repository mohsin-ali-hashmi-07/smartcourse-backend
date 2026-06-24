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
            timeout=settings.temporal_http_timeout,
        )

    if response.status_code == 404:
        raise ApplicationError(
            f"course not found: {course_id}", non_retryable=True
        )
    if response.status_code != 200:
        raise RuntimeError(f"course_service error: {response.status_code}")

    course = response.json()
    if course["status"] != "published":
        raise ApplicationError(
            f"course is not published: {course_id}", non_retryable=True
        )

    return course


@activity.defn
async def create_enrollment_with_progress(
    student_id: str, course_id: str, total_modules: int
) -> dict:
    """
    Atomically create Enrollment + Progress via the enrollment_service API.
    One HTTP call → one DB transaction → both records or neither.
    Idempotent: the service returns the existing record if already enrolled.
    """
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{settings.enrollment_service_url}/api/v1/enrollments/internal/enroll",
            json={
                "student_id": student_id,
                "course_id": course_id,
                "total_modules": total_modules,
            },
            timeout=settings.temporal_http_timeout,
        )

    if response.status_code in (200, 201):
        return response.json()

    raise ValueError(
        f"failed to create enrollment+progress: {response.status_code} {response.text}"
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


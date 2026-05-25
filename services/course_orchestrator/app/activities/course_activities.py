import json
import httpx
from temporalio import activity
from aiokafka import AIOKafkaProducer
from app.core.settings import settings

@activity.defn
async def validate_course(course_id: str) -> dict:
    """Fetch course from course_service and verify it has modules."""
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{settings.course_service_url}/api/v1/courses/{course_id}",
            timeout=10.0
        )
    if response.status_code == 404:
        raise ValueError(f"course not found: {course_id}")
    if response.status_code != 200:
        raise ValueError(f"course_service error: {response.status_code}")
    course = response.json()
    if not course.get("modules"):
        raise ValueError(f"course {course_id} has no modules — cannot publish")
    return course

@activity.defn
async def publish_course(course_id: str, instructor_token: str) -> dict:
    """Update course status to published via course_service API."""
    async with httpx.AsyncClient() as client:
        response = await client.patch(
            f"{settings.course_service_url}/api/v1/courses/{course_id}",
            json={"status": "published"},
            headers={"Authorization": f"Bearer {instructor_token}"},
            timeout=10.0,
        )
    if response.status_code != 200:
        raise ValueError(
            f"failed to publish course {course_id}: {response.text}"
        )
    return response.json()

@activity.defn
async def revert_course_to_draft(course_id: str) -> None:
    """Saga compensation — revert course status back to draft on workflow failure."""
    async with httpx.AsyncClient() as client:
        response = await client.patch(
            f"{settings.course_service_url}/api/v1/courses/internal/{course_id}/revert-to-draft",
            timeout=10.0,
        )
    if response.status_code != 200:
        raise ValueError(
            f"failed to revert course {course_id} to draft: {response.text}"
        )

@activity.defn
async def emit_course_published_event(
    course_id: str, title: str, instructor_id: str
) -> None:
    """Emit course.published event to Kafka."""
    producer = AIOKafkaProducer(
        bootstrap_servers=settings.kafka_bootstrap_servers,
        value_serializer=lambda v: json.dumps(v).encode("utf-8"),
    )
    await producer.start()
    try:
        await producer.send(
            "course.published",
            {
                "event": "course.published",
                "course_id": course_id,
                "title": title,
                "instructor_id": instructor_id,
            },
        )
    finally:
        await producer.stop()
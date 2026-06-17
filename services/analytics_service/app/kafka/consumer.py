import json
import asyncio
from datetime import datetime, timezone
from aiokafka import AIOKafkaConsumer
from app.core.settings import settings
from app.db.session import AsyncSessionLocal
from app.repositories import analytics_repository as repo

TOPICS = ["course.published", "enrollment.created", "progress.updated"]

_consumer_task: asyncio.Task | None = None


async def _handle_course_published(event: dict) -> None:
    published_at = datetime.now(timezone.utc)
    async with AsyncSessionLocal() as db:
        await repo.upsert_course_publish(
            db,
            course_id=event.get("course_id", ""),
            title=event.get("title", ""),
            instructor_id=event.get("instructor_id", ""),
            published_at=published_at,
        )
        await db.commit()


async def _handle_enrollment_created(event: dict) -> None:
    enrolled_at = datetime.now(timezone.utc)
    async with AsyncSessionLocal() as db:
        await repo.upsert_enrollment(
            db,
            enrollment_id=event.get("enrollment_id", ""),
            student_id=event.get("student_id", ""),
            course_id=event.get("course_id", ""),
            enrolled_at=enrolled_at,
        )
        await db.commit()


async def _handle_progress_updated(event: dict) -> None:
    updated_at = datetime.now(timezone.utc)
    async with AsyncSessionLocal() as db:
        await repo.upsert_progress(
            db,
            enrollment_id=event.get("enrollment_id", ""),
            student_id=event.get("student_id", ""),
            course_id=event.get("course_id", ""),
            completed_modules=event.get("completed_modules", 0),
            total_modules=event.get("total_modules", 0),
            updated_at=updated_at,
        )
        await db.commit()


async def _consume_loop() -> None:
    consumer = AIOKafkaConsumer(
        *TOPICS,
        bootstrap_servers=settings.kafka_bootstrap_servers,
        group_id=settings.kafka_consumer_group,
        value_deserializer=lambda v: json.loads(v.decode("utf-8")),
        auto_offset_reset="earliest",
    )
    await consumer.start()
    try:
        async for msg in consumer:
            event = msg.value
            event_type = event.get("event")
            try:
                if event_type == "course.published":
                    await _handle_course_published(event)
                elif event_type == "enrollment.created":
                    await _handle_enrollment_created(event)
                elif event_type == "progress.updated":
                    await _handle_progress_updated(event)
            except Exception as exc:
                async with AsyncSessionLocal() as db:
                    await repo.record_failed_event(
                        db,
                        event_type=event_type or "unknown",
                        raw_payload=json.dumps(event),
                        error_message=str(exc),
                    )
                    await db.commit()
    finally:
        await consumer.stop()


async def start_consumer() -> None:
    global _consumer_task
    _consumer_task = asyncio.create_task(_consume_loop())


async def stop_consumer() -> None:
    global _consumer_task
    if _consumer_task:
        _consumer_task.cancel()
        try:
            await _consumer_task
        except asyncio.CancelledError:
            pass
        _consumer_task = None

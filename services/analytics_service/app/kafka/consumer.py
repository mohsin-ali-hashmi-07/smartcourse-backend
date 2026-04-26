import json
import asyncio
from aiokafka import AIOKafkaConsumer
from app.core.settings import settings
from app.services import analytics_service

TOPICS = ["course.published", "enrollment.created", "progress.updated"]

_consumer_task: asyncio.Task | None = None

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
            if event_type == "course.published":
                analytics_service.handle_course_published(event)
            elif event_type == "enrollment.created":
                analytics_service.handle_enrollment_created(event)
            elif event_type == "progress.updated":
                analytics_service.handle_progress_updated(event)
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
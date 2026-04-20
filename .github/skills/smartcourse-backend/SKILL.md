---
name: smartcourse-backend
description: "SmartCourse backend development patterns. Use when: adding models, schemas, routes, Kafka producers/consumers, Temporal workflows, Redis caching, RAG pipelines, or OpenTelemetry instrumentation to any SmartCourse microservice."
---

# SmartCourse Backend Skill

## When to Use
Adding or modifying: SQLAlchemy models, Pydantic schemas, FastAPI routes, service logic,
Kafka events, Temporal workflows, Redis cache, GenAI/RAG pipelines, observability wiring.

## Standard Service Directory Layout
```
services/<name>_service/app/
├── main.py              # FastAPI app factory + middleware
├── api/
│   ├── dependencies.py  # get_db_session(), get_current_user()
│   └── routes/          # one file per resource
├── constants/           # Enums, string constants
├── core/settings.py     # pydantic_settings.BaseSettings
├── db/
│   ├── base.py          # Base, TimestampMixin
│   └── session.py       # async_sessionmaker factory
├── models/              # SQLAlchemy ORM models
├── schemas/             # Pydantic v2 schemas
├── services/            # Business logic (no HTTPException here)
├── workflows/           # Temporal @workflow.defn classes
├── activities/          # Temporal @activity.defn functions
└── tests/
```

## Model Template
```python
import uuid
from sqlalchemy import String, Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base, TimestampMixin

class MyModel(Base, TimestampMixin):
    __tablename__ = "my_table"
    id: Mapped[uuid.UUID] = mapped_column(default=uuid.uuid4, primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
```

## Schema Template
```python
import uuid
from pydantic import BaseModel, ConfigDict

class MyModelBase(BaseModel):
    name: str

class MyModelCreate(MyModelBase):
    pass

class MyModelUpdate(BaseModel):
    name: str | None = None

class MyModelResponse(MyModelBase):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
```

## Service Layer Template
```python
import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.my_model import MyModel

async def get_by_id(session: AsyncSession, record_id: uuid.UUID) -> MyModel | None:
    result = await session.execute(select(MyModel).where(MyModel.id == record_id))
    return result.scalar_one_or_none()

async def create(session: AsyncSession, data: dict) -> MyModel:
    record = MyModel(**data)
    session.add(record)
    await session.commit()
    await session.refresh(record)
    return record
```

## Kafka Event Template
```python
import json
import uuid
from datetime import datetime, timezone

# Producer
event = {
    "event_type": "enrollment.created",
    "event_id": str(uuid.uuid4()),
    "timestamp": datetime.now(timezone.utc).isoformat(),
    "service_origin": "enrollment_service",
    "payload": {"enrollment_id": str(enrollment.id), "student_id": str(student_id)},
}
await producer.send_and_wait("enrollment.created", json.dumps(event).encode())

# Consumer rule: always check event_id against a seen-events store before processing
```

## Temporal Saga Workflow Template
```python
# workflows/course_publish.py
from datetime import timedelta
from temporalio import workflow
from app.activities.course_activities import (
    validate_content,
    generate_embeddings,
    mark_published,
)

@workflow.defn
class CoursePublishWorkflow:
    @workflow.run
    async def run(self, course_id: str) -> None:
        await workflow.execute_activity(
            validate_content, course_id,
            schedule_to_close_timeout=timedelta(minutes=5),
        )
        await workflow.execute_activity(
            generate_embeddings, course_id,
            schedule_to_close_timeout=timedelta(minutes=10),
        )
        await workflow.execute_activity(
            mark_published, course_id,
            schedule_to_close_timeout=timedelta(minutes=2),
        )
```

## Redis Cache Template (Write-Through)
```python
import json

COURSE_TTL = 300  # seconds

async def get_course_cached(redis, db, course_id: str):
    raw = await redis.get(f"course:{course_id}")
    if raw:
        return json.loads(raw)
    course = await db_fetch_course(db, course_id)
    await redis.set(f"course:{course_id}", course.model_dump_json(), ex=COURSE_TTL)
    return course

async def update_course_cached(redis, db, course_id: str, data: dict):
    updated = await db_update_course(db, course_id, data)
    await redis.set(f"course:{course_id}", updated.model_dump_json(), ex=COURSE_TTL)
    return updated
```

## GenAI RAG Pipeline Steps
1. Embed the user's question using the configured embedding model
2. Query the vector DB (top-k similarity search over course content chunks)
3. Build prompt: system instructions + retrieved chunks (with source metadata) + user question
4. Stream LLM response via `StreamingResponse` using SSE
5. Include `citations: [{chunk_id, lesson_id, relevance_score}]` in the streamed final message

## Domain Events Reference
| Event Topic          | Producer           | Consumers                        |
|----------------------|--------------------|----------------------------------|
| `course.published`   | course_service     | analytics_service, genai_service |
| `enrollment.created` | enrollment_service | analytics_service                |
| `progress.updated`   | enrollment_service | analytics_service                |
| `ai.interaction`     | genai_service      | analytics_service                |

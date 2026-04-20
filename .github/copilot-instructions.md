# SmartCourse Backend — Copilot Instructions

## Project Overview
SmartCourse is a microservices backend for an intelligent course delivery platform.
Stack: Python, FastAPI, PostgreSQL, Redis, Kafka, Temporal, OpenTelemetry, LangChain/LangGraph.

## Service Map

| Service                 | Port | Role                          | DB                      |
|-------------------------|------|-------------------------------|-------------------------|
| user_service            | 8001 | Users, auth, roles            | userdb (PostgreSQL)     |
| course_service          | 8002 | Courses, modules              | coursedb (PostgreSQL)   |
| enrollment_service      | 8003 | Enrollments, progress         | enrollmentdb (PostgreSQL)|
| analytics_service       | 8004 | Event consumption, metrics    | analyticsdb (PostgreSQL)|
| genai_service           | 8005 | RAG pipeline, embeddings, Q&A | Vector DB (Qdrant)      |
| temporal_orchestrator   | 8006 | Workflows + activities ONLY   | None                    |

## Core Rules
- **Never import across service boundaries** — services communicate via HTTP or Kafka only
- **Never query another service's database** — each service owns its data exclusively
- **Never block the event loop** — all I/O must use `async`/`await`
- **Never return ORM objects from routes** — always serialize to Pydantic response schemas
- **Never hardcode credentials** — all config comes from environment variables via `pydantic_settings`

## temporal_orchestrator Rules
- Contains ONLY `app/workflows/` and `app/activities/` — no DB, no models, no schemas, no HTTP routes
- Activities are thin HTTP wrappers that call other service APIs — zero business logic
- Services have zero knowledge that Temporal or the orchestrator exists
- Workflow IDs must be deterministic — e.g., `f"publish-course-{course_id}"`
- Use Saga pattern: every state-mutating activity must have a defined compensating activity

## SQLAlchemy 2.x Conventions
- All models inherit from `Base` and `TimestampMixin` from `app.db.base`
- Use `Mapped` / `mapped_column` declarative style (NOT the legacy `Column` style)
- Primary keys: `id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))`
- Enums: define as `SAEnum("val1", "val2", name="enum_name")` directly in `mapped_column`
- Use `AsyncSession` with `asyncpg` driver — never use sync sessions
- Database URL format: `postgresql+asyncpg://user:pass@host:port/dbname`

## Pydantic v2 Schema Pattern
For every resource, create schemas in order:
1. `MyModelBase` — shared fields
2. `MyModelCreate(MyModelBase)` — creation fields + `@field_validator` for validation
3. `MyModelUpdate(BaseModel)` — all fields optional (`field: type | None = None`)
4. `MyModelResponse(MyModelBase)` — includes `id`, `created_at`, `updated_at`
   uses `model_config = ConfigDict(from_attributes=True)`
- Never include `password` or `hashed_password` in any response schema

## FastAPI Conventions
- All route handlers must be `async def`
- Inject `AsyncSession` via `Depends(get_db)` from `app/api/dependencies.py`
- Creation endpoints use `status_code=201`
- Business logic belongs in `app/services/`, not in route handlers
- Repository queries belong in `app/repositories/`, not in service functions
- Raise `HTTPException` only in the API layer — never in service or repository layers

## Layer Responsibilities
- `routes/`       → HTTP only: parse request, call service, return response
- `services/`     → business logic only: validation, orchestration, decisions
- `repositories/` → database only: all SQLAlchemy queries live here

## Service Layer Conventions
- All functions in `app/services/<name>_service.py`
- Accept `AsyncSession` as the first argument
- Never create sessions inside service functions
- Check for existing records before insert to enforce idempotency

## Repository Layer Conventions
- All functions in `app/repositories/<name>_repository.py`
- Accept `AsyncSession` as the first argument
- Return model objects or `None` — never raise HTTP exceptions
- Use `select()`, `scalars()`, `scalar_one_or_none()` patterns

## Settings
- `app/core/settings.py` uses `pydantic_settings.BaseSettings` with `SettingsConfigDict`
- All required settings have type annotations and no default value
- Use `extra="ignore"` in all `SettingsConfigDict` instances

## Kafka Event Conventions
- Topics: `<domain>.<event>` — e.g., `course.published`, `enrollment.created`, `progress.updated`
- Every payload must include: `event_type`, `timestamp` (ISO 8601), `service_origin`, `payload: dict`
- Consumers must be idempotent — deduplicate by `event_id` before processing

## Temporal Workflow Conventions
- All workflows in `temporal_orchestrator/app/workflows/`
- All activities in `temporal_orchestrator/app/activities/`
- Activities make HTTP calls to service APIs — no direct DB access ever
- All activities decorated with `@activity.defn`; all workflows with `@workflow.defn`

## Redis Caching
- Course reads: **write-through** cache; key = `course:{course_id}`; TTL = 300s
- Enrollment/progress: **cache-aside**; invalidate on update
- Never cache authentication tokens server-side

## Observability
- Every service `main.py` must wire OpenTelemetry middleware (tracing to Jaeger)
- Every service must expose `/metrics` for Prometheus scraping
- Use structured JSON logging with `correlation_id` on every log record
- Propagate trace context through Kafka message headers

## Testing
- Framework: `pytest` + `pytest-asyncio`
- API tests: use `httpx.AsyncClient` with `ASGITransport`
- Mock Kafka and Redis in unit tests — no real network calls in unit tests
- Test critical paths: enrollment idempotency, course publishing state machine, auth middleware
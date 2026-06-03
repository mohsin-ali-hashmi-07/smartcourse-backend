# Smart Course Backend

A microservices-based e-learning platform built with FastAPI, Temporal, Kafka, PostgreSQL, Redis, and MinIO.

---

## Table of Contents

- [Architecture Overview](#architecture-overview)
- [Prerequisites](#prerequisites)
- [First-Time Setup](#first-time-setup)
- [Starting Infrastructure (Docker)](#starting-infrastructure-docker)
- [Running Database Migrations](#running-database-migrations)
- [Starting the Services](#starting-the-services)
- [Starting the Orchestrators](#starting-the-orchestrators)
- [Viewing & Monitoring](#viewing--monitoring)
- [Environment Variables](#environment-variables)

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────┐
│                    Client / API Gateway                  │
└────────────┬──────────┬────────────┬────────────────────┘
             │          │            │
    ┌────────▼──┐  ┌────▼──────┐  ┌─▼──────────────┐
    │user_service│  │course_    │  │enrollment_     │
    │  :8001    │  │service:8002│  │service :8003   │
    └────────────┘  └────┬──────┘  └──────┬─────────┘
                         │                │
              ┌──────────▼────────────────▼──────────┐
              │              Temporal                 │
              │  course_orchestrator (worker)         │
              │  enrollment_orchestrator (worker)     │
              └───────────────────────────────────────┘
                         │
           ┌─────────────▼──────────────┐
           │           Kafka             │
           └─────────────┬──────────────┘
                         │
              ┌──────────▼──────────┐
              │  analytics_service  │
              │      :8004          │
              └─────────────────────┘
```

**Services (FastAPI HTTP APIs):**

| Service | Port | Description |
|---|---|---|
| `user_service` | 8001 | Auth, users, RBAC |
| `course_service` | 8002 | Courses, modules, file uploads (MinIO) |
| `enrollment_service` | 8003 | Enrollments and progress tracking |
| `analytics_service` | 8004 | Kafka-driven analytics aggregation |
| `genai_service` | 8005 | AI content generation _(in progress)_ |

**Orchestrators (Temporal workers — no HTTP port):**

| Orchestrator | Task Queue | Description |
|---|---|---|
| `course_orchestrator` | `course-task-queue` | Course publish workflow |
| `enrollment_orchestrator` | `enrollment-task-queue` | Enrollment workflow |

**Infrastructure:**

| Service | Port | Description |
|---|---|---|
| PostgreSQL | 5432 | Primary database |
| Redis | 6379 | Caching layer |
| Kafka | 9092 | Event streaming |
| Temporal | 7233 | Workflow orchestration engine |
| Temporal UI | 8080 | Workflow browser UI |
| MinIO API | 9000 | Object storage (S3-compatible) |
| MinIO Console | 9001 | MinIO browser UI |
| Prometheus | 9090 | Metrics collection |
| Grafana | 3000 | Metrics dashboards |

---

## Prerequisites

- [Docker Desktop](https://www.docker.com/products/docker-desktop/) (v24+)
- Python 3.11+
- `pip` or a virtual environment manager (e.g. `venv`)

---

## First-Time Setup

### 1. Clone the repository

```bash
git clone <repo-url>
cd smartcourse-backend
```

### 2. Create virtual environments for each service

Run this once per service you want to develop locally. Example for `user_service`:

```bash
cd services/user_service
python -m venv venv

# Windows
venv\Scripts\activate

# macOS / Linux
source venv/bin/activate

pip install -r requirements.txt
```

Repeat for every service you intend to run:
- `services/course_service`
- `services/enrollment_service`
- `services/analytics_service`
- `services/course_orchestrator`
- `services/enrollment_orchestrator`

---

## Starting Infrastructure (Docker)

All infrastructure dependencies (Postgres, Redis, Kafka, Temporal, MinIO, Prometheus, Grafana) are managed by a single Docker Compose file.

```bash
# From the repo root
docker compose up -d
```

This starts all infrastructure containers in the background. Wait ~15-30 seconds for everything to be healthy before starting services.

**Verify everything is up:**

```bash
docker compose ps
```

**Stop infrastructure:**

```bash
docker compose down
```

**Stop and remove all volumes (full reset):**

```bash
docker compose down -v
```

---

## Running Database Migrations

Each service that owns a database must have its Alembic migrations applied before the service can start. The PostgreSQL `init-db.sql` script automatically creates the three databases (`userdb`, `coursedb`, `enrollmentdb`) when the container first starts.

Run migrations once after starting Docker:

```bash
# user_service
cd services/user_service
alembic upgrade head

# course_service
cd ../course_service
alembic upgrade head

# enrollment_service
cd ../enrollment_service
alembic upgrade head
```

---

## Starting the Services

Each service is a FastAPI app run with `uvicorn`. Open a separate terminal for each.

Make sure the service's virtual environment is activated and you are inside the service directory before running.

### user_service (port 8001)

```bash
cd services/user_service
# activate venv first
uvicorn app.main:app --reload --port 8001
```

### course_service (port 8002)

```bash
cd services/course_service
# activate venv first
uvicorn app.main:app --reload --port 8002
```

### enrollment_service (port 8003)

```bash
cd services/enrollment_service
# activate venv first
uvicorn app.main:app --reload --port 8003
```

### analytics_service (port 8004)

```bash
cd services/analytics_service
# activate venv first
uvicorn app.main:app --reload --port 8004
```

**Health check:** once a service is running, visit `http://localhost:<port>/health` to confirm it's up.

**Interactive API docs (Swagger UI):** `http://localhost:<port>/docs`

---

## Starting the Orchestrators

Orchestrators are Temporal workers — they do **not** expose an HTTP port. They connect to the Temporal server running in Docker and listen on their task queues.

Start each orchestrator in its own terminal after the Temporal container is healthy.

### course_orchestrator

```bash
cd services/course_orchestrator
# activate venv first
python -m app.main
```

You should see:
```
course-orchestrator worker started on 'course-task-queue'
```

### enrollment_orchestrator

```bash
cd services/enrollment_orchestrator
# activate venv first
python -m app.main
```

You should see:
```
enrollment-orchestrator worker started on 'enrollment-task-queue'
```

---

## Viewing & Monitoring

| UI | URL | Credentials |
|---|---|---|
| **Temporal UI** — browse & debug workflows | http://localhost:8080 | _(none)_ |
| **MinIO Console** — manage uploaded files | http://localhost:9001 | `minioadmin` / `minioadmin` |
| **Grafana** — service metrics dashboards | http://localhost:3000 | `admin` / `admin` |
| **Prometheus** — raw metrics explorer | http://localhost:9090 | _(none)_ |
| **Swagger UI** — user_service | http://localhost:8001/docs | _(JWT bearer)_ |
| **Swagger UI** — course_service | http://localhost:8002/docs | _(JWT bearer)_ |
| **Swagger UI** — enrollment_service | http://localhost:8003/docs | _(JWT bearer)_ |
| **Swagger UI** — analytics_service | http://localhost:8004/docs | _(none)_ |

---

## Environment Variables

Each service reads its configuration from a `.env` file in its own directory. The defaults in the provided `.env` files match the Docker Compose infrastructure, so no changes are needed for local development.

### user_service

| Variable | Default | Description |
|---|---|---|
| `DATABASE_URL` | `postgresql+asyncpg://postgres:password@localhost:5432/userdb` | Postgres connection string |
| `JWT_SECRET` | `supersecretkey1234567890changeinprod` | **Change in production** |
| `JWT_EXPIRE_MINUTES` | `60` | Token expiry |

### course_service

| Variable | Default | Description |
|---|---|---|
| `DATABASE_URL` | `postgresql+asyncpg://postgres:password@localhost:5432/coursedb` | Postgres connection string |
| `REDIS_URL` | `redis://localhost:6379` | Redis connection |
| `KAFKA_BOOTSTRAP_SERVERS` | `127.0.0.1:9092` | Kafka broker |
| `JWT_SECRET` | `supersecretkey1234567890changeinprod` | **Change in production** |

### enrollment_service

| Variable | Default | Description |
|---|---|---|
| `DATABASE_URL` | `postgresql+asyncpg://postgres:password@localhost:5432/enrollmentdb` | Postgres connection string |
| `COURSE_SERVICE_URL` | `http://localhost:8002` | Internal service URL |
| `KAFKA_BOOTSTRAP_SERVERS` | `127.0.0.1:9092` | Kafka broker |
| `JWT_SECRET` | `supersecretkey1234567890changeinprod` | **Change in production** |

### analytics_service

| Variable | Default | Description |
|---|---|---|
| `KAFKA_BOOTSTRAP_SERVERS` | `127.0.0.1:9092` | Kafka broker |
| `KAFKA_CONSUMER_GROUP` | `analytics-group` | Consumer group ID |

### course_orchestrator

| Variable | Default | Description |
|---|---|---|
| `TEMPORAL_HOST` | `localhost:7233` | Temporal server address |
| `COURSE_SERVICE_URL` | `http://localhost:8002` | course_service for activities |
| `KAFKA_BOOTSTRAP_SERVERS` | `127.0.0.1:9092` | Kafka broker |

### enrollment_orchestrator

| Variable | Default | Description |
|---|---|---|
| `TEMPORAL_HOST` | `localhost:7233` | Temporal server address |
| `COURSE_SERVICE_URL` | `http://localhost:8002` | course_service for activities |
| `ENROLLMENT_SERVICE_URL` | `http://localhost:8003` | enrollment_service for activities |
| `KAFKA_BOOTSTRAP_SERVERS` | `127.0.0.1:9092` | Kafka broker |

> **Security note:** The default `JWT_SECRET` is for local development only. Always replace it with a strong random secret in any deployed environment.
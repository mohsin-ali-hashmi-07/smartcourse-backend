from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.models.analytics import EnrollmentFact
from app.repositories import analytics_repository as repo
from app.schemas.analytics import (
    AnalyticsSummaryResponse,
    EnrollmentsOverTimeResponse,
    CompletionRatesResponse,
    PopularCoursesResponse,
    FailedEventsResponse,
)


async def get_summary(db: AsyncSession) -> AnalyticsSummaryResponse:
    total_students = await repo.count_distinct_students(db)
    total_instructors = await repo.count_distinct_instructors(db)
    total_courses_published = await repo.count_courses_published(db)
    total_enrollments = await db.scalar(select(func.count(EnrollmentFact.id))) or 0
    total_completions = await db.scalar(
        select(func.count(EnrollmentFact.id)).where(EnrollmentFact.completed_at.is_not(None))
    ) or 0
    avg_courses_per_student = await repo.avg_courses_per_student(db)
    avg_seconds_to_complete = await repo.avg_seconds_to_complete(db)
    failed_event_count = await repo.count_failed_events(db)

    return AnalyticsSummaryResponse(
        total_students=total_students,
        total_instructors=total_instructors,
        total_courses_published=total_courses_published,
        total_enrollments=total_enrollments,
        total_completions=total_completions,
        avg_courses_per_student=avg_courses_per_student,
        avg_seconds_to_complete=avg_seconds_to_complete,
        failed_event_count=failed_event_count,
    )


async def get_enrollments_over_time(db: AsyncSession) -> EnrollmentsOverTimeResponse:
    data = await repo.enrollments_over_time(db)
    return EnrollmentsOverTimeResponse(data=data)


async def get_completion_rates(db: AsyncSession) -> CompletionRatesResponse:
    data = await repo.completion_rate_per_course(db)
    return CompletionRatesResponse(data=data)


async def get_popular_courses(db: AsyncSession, limit: int = 10) -> PopularCoursesResponse:
    data = await repo.most_popular_courses(db, limit=limit)
    return PopularCoursesResponse(data=data)


async def get_failed_events(db: AsyncSession) -> FailedEventsResponse:
    count = await repo.count_failed_events(db)
    recent = await repo.recent_failed_events(db)
    return FailedEventsResponse(count=count, recent=recent)

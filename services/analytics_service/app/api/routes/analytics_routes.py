from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_db
from app.services import analytics_service
from app.schemas.analytics import (
    AnalyticsSummaryResponse,
    EnrollmentsOverTimeResponse,
    CompletionRatesResponse,
    PopularCoursesResponse,
    FailedEventsResponse,
)

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("/summary", response_model=AnalyticsSummaryResponse)
async def get_summary(db: AsyncSession = Depends(get_db)):
    return await analytics_service.get_summary(db)


@router.get("/enrollments-over-time", response_model=EnrollmentsOverTimeResponse)
async def get_enrollments_over_time(db: AsyncSession = Depends(get_db)):
    return await analytics_service.get_enrollments_over_time(db)


@router.get("/completion-rates", response_model=CompletionRatesResponse)
async def get_completion_rates(db: AsyncSession = Depends(get_db)):
    return await analytics_service.get_completion_rates(db)


@router.get("/popular-courses", response_model=PopularCoursesResponse)
async def get_popular_courses(
    limit: int = Query(default=10, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    return await analytics_service.get_popular_courses(db, limit=limit)


@router.get("/failed-events", response_model=FailedEventsResponse)
async def get_failed_events(db: AsyncSession = Depends(get_db)):
    return await analytics_service.get_failed_events(db)
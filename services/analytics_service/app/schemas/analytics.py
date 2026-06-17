from pydantic import BaseModel


class EnrollmentOverTimeItem(BaseModel):
    date: str
    count: int


class CourseCompletionRate(BaseModel):
    course_id: str
    total_enrollments: int
    completed_enrollments: int
    completion_rate: float


class PopularCourse(BaseModel):
    course_id: str
    enrollment_count: int


class FailedEventItem(BaseModel):
    id: str
    event_type: str
    error_message: str
    failed_at: str


class AnalyticsSummaryResponse(BaseModel):
    total_students: int
    total_instructors: int
    total_courses_published: int
    total_enrollments: int
    total_completions: int
    avg_courses_per_student: float
    avg_seconds_to_complete: float | None
    failed_event_count: int


class EnrollmentsOverTimeResponse(BaseModel):
    data: list[EnrollmentOverTimeItem]


class CompletionRatesResponse(BaseModel):
    data: list[CourseCompletionRate]


class PopularCoursesResponse(BaseModel):
    data: list[PopularCourse]


class FailedEventsResponse(BaseModel):
    count: int
    recent: list[FailedEventItem]

from datetime import timedelta
from temporalio import workflow
from temporalio.common import RetryPolicy

with workflow.unsafe.imports_passed_through():
    from app.activities.enrollment_activities import (
        verify_course_published,
        create_enrollment_with_progress,
        emit_enrollment_created_event,
    )
    from app.core.settings import settings


@workflow.defn
class EnrollmentWorkflow:
    """
    Enrollment workflow — atomic DB path.

    Steps:
      1. verify_course_published       — read-only, non-retryable on 404/unpublished
      2. create_enrollment_with_progress — single atomic DB transaction:
                                           Enrollment + Progress created together or not at all.
                                           Idempotent — safe for Temporal retries.
      3. emit_enrollment_created_event — Kafka event, best-effort after DB is consistent.

    No Saga compensation needed: if step 2 fails the DB rolls back automatically.
    """

    @workflow.run
    async def run(self, student_id: str, course_id: str) -> dict:
        retry_policy = RetryPolicy(
            maximum_attempts=settings.temporal_max_retries,
            initial_interval=timedelta(seconds=settings.temporal_initial_retry_interval),
            maximum_interval=timedelta(seconds=settings.temporal_max_retry_interval),
        )
        activity_timeout = timedelta(seconds=settings.temporal_activity_timeout)

        # ── Step 1: Verify course is published ────────────────────────────────
        course = await workflow.execute_activity(
            verify_course_published,
            course_id,
            start_to_close_timeout=activity_timeout,
            retry_policy=retry_policy,
        )

        total_modules = len(course.get("modules", []))

        # ── Step 2: Atomic enrollment + progress ──────────────────────────────
        enrollment = await workflow.execute_activity(
            create_enrollment_with_progress,
            args=[student_id, course_id, total_modules],
            start_to_close_timeout=activity_timeout,
            retry_policy=retry_policy,
        )

        # ── Step 3: Emit Kafka event ───────────────────────────────────────────
        await workflow.execute_activity(
            emit_enrollment_created_event,
            args=[enrollment["id"], student_id, course_id],
            start_to_close_timeout=activity_timeout,
            retry_policy=retry_policy,
        )

        return enrollment

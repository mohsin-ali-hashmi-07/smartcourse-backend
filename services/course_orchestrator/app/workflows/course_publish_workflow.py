from datetime import timedelta
from temporalio import workflow
from temporalio.common import RetryPolicy

with workflow.unsafe.imports_passed_through():
    from app.activities.course_activities import (
        validate_course,
        publish_course,
        revert_course_to_draft,
        emit_course_published_event,
    )
    from app.core.settings import settings


@workflow.defn
class CoursePublishWorkflow:
    """
    Saga pattern workflow for course publishing.

    Steps:
      1. validate_course             — verifies course exists and has modules
      2. publish_course              — sets status from 'publishing' → 'published'
      3. emit_course_published_event — Kafka event after DB is consistent

    Compensation:
      ANY failure in the workflow (validation, publish, or Kafka) triggers
      revert_course_to_draft to roll the course back from 'publishing' (or
      'published') to 'draft'. The revert endpoint is idempotent.

    The route sets status='publishing' BEFORE starting this workflow,
    so even validation failures need compensation to free the course up.
    """

    @workflow.run
    async def run(self, course_id: str) -> dict:
        retry_policy = RetryPolicy(
            maximum_attempts=settings.temporal_max_retries,
            initial_interval=timedelta(seconds=settings.temporal_initial_retry_interval),
            maximum_interval=timedelta(seconds=settings.temporal_max_retry_interval),
        )
        compensation_retry = RetryPolicy(
            maximum_attempts=settings.temporal_compensation_max_retries
        )
        activity_timeout = timedelta(seconds=settings.temporal_activity_timeout)

        try:
            # Step 1: Validate
            course = await workflow.execute_activity(
                validate_course,
                course_id,
                start_to_close_timeout=activity_timeout,
                retry_policy=retry_policy,
            )

            # Step 2: Mark course as published
            updated_course = await workflow.execute_activity(
                publish_course,
                course_id,
                start_to_close_timeout=activity_timeout,
                retry_policy=retry_policy,
            )

            # Step 3: Emit Kafka event
            await workflow.execute_activity(
                emit_course_published_event,
                args=[
                    course_id,
                    updated_course["title"],
                    updated_course["instructor_id"],
                ],
                start_to_close_timeout=activity_timeout,
                retry_policy=retry_policy,
            )

            return updated_course

        except Exception:
            # Saga compensation — revert to draft regardless of which step failed.
            # revert_course_to_draft is idempotent, safe to call from any state.
            await workflow.execute_activity(
                revert_course_to_draft,
                course_id,
                start_to_close_timeout=activity_timeout,
                retry_policy=compensation_retry,
            )
            raise  # bubble up so Temporal marks workflow as failed
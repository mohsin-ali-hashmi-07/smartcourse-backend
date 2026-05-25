from datetime import timedelta
from temporalio import workflow
from temporalio.common import RetryPolicy
from temporalio.exceptions import ActivityError

with workflow.unsafe.imports_passed_through():
    from app.activities.course_activities import (
        validate_course,
        publish_course,
        revert_course_to_draft,
        emit_course_published_event,
    )


@workflow.defn
class CoursePublishWorkflow:
    """
    Saga pattern workflow for course publishing.

    Steps:
      1. validate_course             — read-only check, no compensation needed
      2. publish_course              — sets status to 'published', compensation = revert to 'draft'
      3. emit_course_published_event — Kafka event, best-effort after DB is consistent

    Compensation:
      If step 3 fails after retries → revert_course_to_draft (Saga rollback)
    """

    @workflow.run
    async def run(self, course_id: str, instructor_token: str):
        retry_policy = RetryPolicy(
            maximum_attempts=3,
            initial_interval=timedelta(seconds=2),
        )

        # Step 1: Validate course exists and has modules
        course = await workflow.execute_activity(
            validate_course,
            course_id,
            start_to_close_timeout=timedelta(seconds=30),
            retry_policy=retry_policy,
        )

        # Step 2: Set status to 'published'
        try:
            updated_course = await workflow.execute_activity(
                publish_course,
                args=[course_id, instructor_token],
                start_to_close_timeout=timedelta(seconds=30),
                retry_policy=retry_policy,
            )
        except ActivityError:
            # publish failed — course is still in 'publishing' state, revert to draft
            await workflow.execute_activity(
                revert_course_to_draft,
                course_id,
                start_to_close_timeout=timedelta(seconds=30),
                retry_policy=RetryPolicy(maximum_attempts=5),
            )
            raise

        # Step 3: Emit Kafka event
        try:
            await workflow.execute_activity(
                emit_course_published_event,
                args=[
                    course_id,
                    updated_course["title"],
                    updated_course["instructor_id"],
                ],
                start_to_close_timeout=timedelta(seconds=30),
                retry_policy=retry_policy,
            )
        except ActivityError:
            # Kafka emit failed — revert course back to draft
            await workflow.execute_activity(
                revert_course_to_draft,
                course_id,
                start_to_close_timeout=timedelta(seconds=30),
                retry_policy=RetryPolicy(maximum_attempts=5),
            )
            raise

        return updated_course
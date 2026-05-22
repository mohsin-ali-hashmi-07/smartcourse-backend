from datetime import timedelta
from temporalio import workflow
from temporalio.common import RetryPolicy
from temporalio.exceptions import ActivityError

with workflow.unsafe.imports_passed_through():
    from app.activities.enrollment_activities import (
        verify_course_published,
        create_enrollment,
        create_progress,
        delete_enrollment,
        emit_enrollment_created_event,
    )


@workflow.defn
class EnrollmentWorkflow:
    """
    Saga pattern workflow for student enrollment.

    Steps:
      1. verify_course_published  — read-only check, no compensation needed
      2. create_enrollment        — state mutation, MUST compensate on failure
      3. create_progress          — state mutation, compensation = delete_enrollment
      4. emit_enrollment_created_event — fire Kafka event only after all DB steps succeed

    Compensation logic:
      If step 3 (create_progress) fails → run delete_enrollment (Saga rollback)
      If step 4 (Kafka emit) fails → enrollment + progress exist (acceptable),
        Kafka is best-effort after DB consistency is guaranteed.
    """

    @workflow.run
    async def run(self, student_id: str, course_id: str) -> dict:
        retry_policy = RetryPolicy(
            maximum_attempts=3,
            initial_interval=timedelta(seconds=2),
        )

        course = await workflow.execute_activity(
            verify_course_published,
            course_id,
            start_to_close_timeout=timedelta(seconds=30),
            retry_policy=retry_policy,
        )

        total_modules = len(course.get("modules", []))

        # ── Step 2: Create enrollment ──────────────────────────────────────────
        # The service generates the enrollment ID — we read it from the response.
        enrollment = await workflow.execute_activity(
            create_enrollment,
            args=[student_id, course_id],
            start_to_close_timeout=timedelta(seconds=30),
            retry_policy=retry_policy,
        )

        # Extract the real enrollment_id so Saga compensation and later steps use it.
        enrollment_id = enrollment["id"]

        try:
            await workflow.execute_activity(
                create_progress,
                args=[enrollment_id, total_modules],
                start_to_close_timeout=timedelta(seconds=30),
                retry_policy=retry_policy,
            )
        except ActivityError:
            await workflow.execute_activity(
                delete_enrollment,
                enrollment_id,
                start_to_close_timeout=timedelta(seconds=30),
                retry_policy=RetryPolicy(maximum_attempts=5),
            )
            raise  # re-raise so Temporal marks workflow as failed

        await workflow.execute_activity(
            emit_enrollment_created_event,
            args=[enrollment_id, student_id, course_id],
            start_to_close_timeout=timedelta(seconds=30),
            retry_policy=retry_policy,
        )

        return enrollment

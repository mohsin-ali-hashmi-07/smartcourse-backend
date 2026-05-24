from datetime import timedelta
from temporalio import workflow
from temporalio.common import RetryPolicy

with workflow.unsafe.imports_passed_through():
    from app.activities.course_activities import (
        validate_course,
        publish_course,
        emit_course_published_event,
    )

@workflow.defn
class CoursePublishWorkflow:
    @workflow.run
    async def run(self, course_id: str, instructor_token: str):
        retry_policy = RetryPolicy(
            maximum_attempts=3,
            initial_interval=timedelta(seconds=2)
        )

        course = await workflow.execute_activity(
            validate_course,
            course_id,
            start_to_close_timeout=timedelta(seconds=30),
            retry_policy=retry_policy,
        )

        updated_course = await workflow.execute_activity(
            publish_course,
            args=[course_id, instructor_token],
            start_to_close_timeout=timedelta(seconds=30),
            retry_policy=retry_policy,
        )

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

        return updated_course
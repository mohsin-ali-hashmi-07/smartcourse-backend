import asyncio
from temporalio.client import Client
from temporalio.worker import Worker
from app.core.settings import settings
from app.workflows.course_publish_workflow import CoursePublishWorkflow
from app.activities.course_activities import (
    validate_course,
    publish_course,
    revert_course_to_draft,
    emit_course_published_event,
)

async def main():
    client = await Client.connect(settings.temporal_host)

    worker = Worker(
        client,
        task_queue="course-task-queue",
        workflows=[CoursePublishWorkflow],
        activities=[
            validate_course,
            publish_course,
            revert_course_to_draft,
            emit_course_published_event,
        ],
    )

    print("course-orchestrator worker started on 'course-task-queue'")
    await worker.run()


if __name__ == "__main__":
    asyncio.run(main())
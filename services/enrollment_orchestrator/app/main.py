import asyncio
from temporalio.client import Client
from temporalio.worker import Worker
from app.core.settings import settings
from app.workflows.enrollment_workflow import EnrollmentWorkflow
from app.activities.enrollment_activities import (
    verify_course_published,
    create_enrollment_with_progress,
    emit_enrollment_created_event,
)


async def main():
    client = await Client.connect(settings.temporal_host)

    worker = Worker(
        client,
        task_queue=settings.temporal_task_queue,
        workflows=[EnrollmentWorkflow],
        activities=[
            verify_course_published,
            create_enrollment_with_progress,
            emit_enrollment_created_event,
        ],
    )

    print("enrollment-orchestrator worker started on 'enrollment-task-queue'")
    await worker.run()


if __name__ == "__main__":
    asyncio.run(main())

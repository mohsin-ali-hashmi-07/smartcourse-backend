from collections import defaultdict

_total_courses_published: int = 0
_total_enrollments: int = 0
_total_completions: int = 0
_enrollments_per_course: dict[str, int] = defaultdict(int)
_completions_per_course: dict[str, int] = defaultdict(int)

def handle_course_published(event: dict) -> None:
    global _total_courses_published
    _total_courses_published += 1


def handle_enrollment_created(event: dict) -> None:
    global _total_enrollments
    course_id = event.get("course_id", "unknown")
    _total_enrollments += 1
    _enrollments_per_course[course_id] += 1

def handle_progress_updated(event: dict) -> None:
    global _total_completions
    completion = event.get("completion_percentage", 0)
    if completion >= 100:
        course_id = event.get("course_id", "unknown")
        _total_completions += 1
        _completions_per_course[course_id] += 1

def get_summary() -> dict:
    return {
        "total_courses_published": _total_courses_published,
        "total_enrollments": _total_enrollments,
        "total_completions": _total_completions,
        "enrollments_per_course": dict(_enrollments_per_course),
        "completions_per_course": dict(_completions_per_course),
    }
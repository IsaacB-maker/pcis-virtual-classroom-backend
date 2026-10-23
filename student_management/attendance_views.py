
from rest_framework import status
from rest_framework.decorators import (
    api_view,
    permission_classes,
)
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .attendance import (
    get_eligible_student,
    record_student_join,
    record_student_leave,
)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def student_join_lesson(request):
    """
    POST /api/students/attendance/join/
    Body: {"lesson_id": 123}
    """
    lesson_id = request.data.get("lesson_id")

    if lesson_id is None:
        return Response(
            {"error": "lesson_id is required."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        attendance = record_student_join(
            request.user,
            lesson_id,
        )
    except Exception as exc:
        from rest_framework.exceptions import APIException

        if isinstance(exc, APIException):
            return Response(
                {"error": str(exc.detail)},
                status=exc.status_code,
            )
        raise

    return Response(
        {
            "message": "Attendance recorded.",
            "attendance": {
                "id": attendance.pk,
                "lesson_id": attendance.lesson_id,
                "joined_at": attendance.joined_at.isoformat(),
                "left_at": (
                    attendance.left_at.isoformat()
                    if attendance.left_at
                    else None
                ),
                "duration_seconds": attendance.duration_seconds,
            },
        },
        status=status.HTTP_201_CREATED,
    )


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def student_leave_lesson(request):
    """
    POST /api/students/attendance/leave/
    Body: {"attendance_id": 123}
    """
    attendance_id = request.data.get("attendance_id")

    if attendance_id is None:
        return Response(
            {"error": "attendance_id is required."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    from .attendance import record_student_leave

    try:
        attendance = record_student_leave(
            request.user,
            attendance_id,
        )
    except Exception as exc:
        from rest_framework.exceptions import APIException

        if isinstance(exc, APIException):
            return Response(
                {"error": str(exc.detail)},
                status=exc.status_code,
            )
        raise

    return Response(
        {
            "message": "Attendance completed.",
            "attendance": {
                "id": attendance.pk,
                "lesson_id": attendance.lesson_id,
                "joined_at": attendance.joined_at.isoformat(),
                "left_at": attendance.left_at.isoformat(),
                "duration_seconds": attendance.duration_seconds,
            },
        },
        status=status.HTTP_200_OK,
    )


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def student_attendance_history(request):
    """
    GET /api/students/attendance/
    Return only the authenticated student's own attendance.
    """
    student = get_eligible_student(request.user)

    records = (
        student.attendance_records
        .select_related("lesson", "lesson__school_class")
        .order_by("-joined_at")[:100]
    )

    return Response(
        {
            "attendance": [
                {
                    "id": record.pk,
                    "lesson_id": record.lesson_id,
                    "lesson_title": (
                        record.lesson.title
                        if record.lesson
                        else "Unknown lesson"
                    ),
                    "school_class": (
                        record.lesson.school_class.name
                        if record.lesson
                        else None
                    ),
                    "joined_at": record.joined_at.isoformat(),
                    "left_at": (
                        record.left_at.isoformat()
                        if record.left_at
                        else None
                    ),
                    "duration_seconds": record.duration_seconds,
                }
                for record in records
            ]
        },
        status=status.HTTP_200_OK,
    )


from django.db import transaction
from django.utils import timezone

from rest_framework.exceptions import PermissionDenied, ValidationError

from classroom.models import Lesson
from .models import Student, LessonAttendance


def get_eligible_student(user):
    """
    Return the authenticated student only if registration,
    account status, fee status, and class assignment are valid.
    """
    if not user or not user.is_authenticated or not user.is_active:
        raise PermissionDenied("Please log in with an active student account.")

    try:
        student = Student.objects.select_related(
            "school_class", "user"
        ).get(user=user)
    except Student.DoesNotExist:
        raise PermissionDenied("No student record is linked to this account.")

    if student.registration_status != Student.RegistrationStatus.REGISTERED:
        raise PermissionDenied("Please complete student registration.")

    if student.fee_status != Student.FeeStatus.PAID:
        raise PermissionDenied(
            "Your fees must be confirmed as paid before joining lessons."
        )

    if student.school_class is None:
        raise PermissionDenied(
            "The school has not assigned you to a class yet."
        )

    return student


def get_eligible_lesson(student, lesson_id):
    """
    Find a lesson only if it belongs to the student's assigned class
    and is currently live.
    """
    try:
        lesson = Lesson.objects.select_related(
            "school_class"
        ).get(pk=lesson_id)
    except (Lesson.DoesNotExist, ValueError, TypeError):
        raise ValidationError({"lesson_id": "The requested lesson was not found."})

    if lesson.school_class_id != student.school_class_id:
        raise PermissionDenied(
            "You can only join lessons for your assigned class."
        )

    if lesson.status != "live":
        raise PermissionDenied("This lesson is not currently live.")

    return lesson


@transaction.atomic
def record_student_join(user, lesson_id):
    """
    Record a student's arrival. Reuse an existing open attendance
    record for the same lesson to avoid duplicate join records.
    """
    student = get_eligible_student(user)
    lesson = get_eligible_lesson(student, lesson_id)

    open_record = (
        LessonAttendance.objects.select_for_update()
        .filter(
            student=student,
            lesson=lesson,
            left_at__isnull=True,
        )
        .order_by("-joined_at")
        .first()
    )

    if open_record:
        return open_record

    return LessonAttendance.objects.create(
        student=student,
        lesson=lesson,
        joined_at=timezone.now(),
    )


@transaction.atomic
def record_student_leave(user, attendance_id):
    """
    Close only the authenticated student's own open attendance record.
    Calculate duration on the server rather than trusting the browser.
    """
    student = get_eligible_student(user)

    try:
        attendance = (
            LessonAttendance.objects.select_for_update()
            .get(
                pk=attendance_id,
                student=student,
                left_at__isnull=True,
            )
        )
    except LessonAttendance.DoesNotExist:
        raise ValidationError({
            "attendance_id":
                "No open attendance record was found for this student."
        })

    left_at = timezone.now()
    elapsed = (left_at - attendance.joined_at).total_seconds()

    attendance.left_at = left_at
    attendance.duration_seconds = max(0, int(elapsed))
    attendance.save(update_fields=["left_at", "duration_seconds"])

    return attendance

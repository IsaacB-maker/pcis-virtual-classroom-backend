
from rest_framework.permissions import BasePermission

from .models import Student


class IsPaidStudent(BasePermission):
    """
    Allow access only to an authenticated, registered student
    whose current fee status is PAID and who has an assigned class.
    """

    message = (
        "Access denied. Your account must be registered, "
        "your fees must be confirmed as paid, and you must "
        "have an assigned class."
    )

    def has_permission(self, request, view):
        user = request.user

        if not user or not user.is_authenticated:
            return False

        if not user.is_active:
            return False

        try:
            student = Student.objects.select_related(
                "school_class"
            ).get(user=user)
        except Student.DoesNotExist:
            return False

        return (
            student.registration_status
            == Student.RegistrationStatus.REGISTERED
            and student.fee_status == Student.FeeStatus.PAID
            and student.school_class is not None
        )


class IsAssignedClassStudent(BasePermission):
    """
    Object-level permission for lessons and classroom resources.
    The object's school_class must match the student's assigned class.
    """

    message = "You can only access lessons for your assigned class."

    def has_permission(self, request, view):
        return IsPaidStudent().has_permission(request, view)

    def has_object_permission(self, request, view, obj):
        try:
            student = Student.objects.select_related(
                "school_class"
            ).get(user=request.user)
        except Student.DoesNotExist:
            return False

        if not student.school_class:
            return False

        # Supports a Lesson-like object or an object that
        # directly exposes school_class.
        lesson_class = getattr(obj, "school_class", None)

        # Supports a classroom session linked to a lesson.
        if lesson_class is None:
            lesson = getattr(obj, "lesson", None)
            if lesson is not None:
                lesson_class = getattr(lesson, "school_class", None)

        return (
            lesson_class is not None
            and lesson_class.pk == student.school_class_id
        )

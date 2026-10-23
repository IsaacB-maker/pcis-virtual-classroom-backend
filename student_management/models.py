
from django.conf import settings
from django.db import models
from django.utils import timezone

from classroom.models import SchoolClass, Lesson


class Student(models.Model):
    class FeeStatus(models.TextChoices):
        NOT_PAID = "not_paid", "Not Paid"
        PENDING = "pending", "Pending Verification"
        PAID = "paid", "Paid"
        SUSPENDED = "suspended", "Suspended"

    class RegistrationStatus(models.TextChoices):
        NOT_REGISTERED = "not_registered", "Not Registered"
        REGISTERED = "registered", "Registered"

    admission_number = models.CharField(
        max_length=50,
        unique=True,
    )
    full_name = models.CharField(max_length=200)
    email = models.EmailField(blank=True)
    phone_number = models.CharField(max_length=30, blank=True)

    school_class = models.ForeignKey(
        SchoolClass,
        on_delete=models.PROTECT,
        related_name="students",
        db_column="school_class_id",
        null=True,
        blank=True,
    )

    fee_status = models.CharField(
        max_length=20,
        choices=FeeStatus.choices,
        default=FeeStatus.NOT_PAID,
    )

    registration_status = models.CharField(
        max_length=20,
        choices=RegistrationStatus.choices,
        default=RegistrationStatus.NOT_REGISTERED,
    )

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="pcis_student_record",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.admission_number} - {self.full_name}"

    @property
    def can_access_lessons(self):
        return (
            self.registration_status == self.RegistrationStatus.REGISTERED
            and self.fee_status == self.FeeStatus.PAID
            and self.user is not None
            and self.user.is_active
        )


class StudentRegistrationCode(models.Model):
    student = models.OneToOneField(
        Student,
        on_delete=models.CASCADE,
        related_name="registration_code",
    )
    code_hash = models.CharField(max_length=128)

    # Retained for compatibility with the existing database.
    # Permanent registration codes do not expire.
    expires_at = models.DateTimeField(
        null=True,
        blank=True,
        default=None,
    )

    used_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Registration code for {self.student.admission_number}"

    @property
    def is_valid(self):
        return self.used_at is None


class LessonAttendance(models.Model):
    student = models.ForeignKey(
        Student,
        on_delete=models.CASCADE,
        related_name="attendance_records",
    )

    lesson = models.ForeignKey(
        Lesson,
        on_delete=models.PROTECT,
        related_name="student_attendance",
        db_column="lesson_id",
        null=True,
        blank=True,
    )

    joined_at = models.DateTimeField(default=timezone.now)
    left_at = models.DateTimeField(null=True, blank=True)
    duration_seconds = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["-joined_at"]
        indexes = [
            models.Index(fields=["student", "joined_at"]),
            models.Index(fields=["lesson", "joined_at"]),
        ]

    def __str__(self):
        lesson_title = self.lesson.title if self.lesson else "No lesson"
        return f"{self.student.admission_number} - {lesson_title}"

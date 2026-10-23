
from django.db import models
from django.db.models import Q
import uuid


class Teacher(models.Model):
    name = models.CharField(max_length=150)

    email = models.EmailField(unique=True)

    password = models.CharField(max_length=255)

    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    def __str__(self):
        return self.name


class SchoolClass(models.Model):
    CLASS_CHOICES = [
        ("P1", "Primary 1"),
        ("P2", "Primary 2"),
        ("P3", "Primary 3"),
        ("P4", "Primary 4"),
        ("P5", "Primary 5"),
        ("P6", "Primary 6"),
        ("P7", "Primary 7"),
    ]

    name = models.CharField(
        max_length=10,
        choices=CLASS_CHOICES,
        unique=True,
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    def __str__(self):
        return self.name


class Lesson(models.Model):
    STATUS_CHOICES = [
        ("scheduled", "Scheduled"),
        ("live", "Live"),
        ("completed", "Completed"),
        ("cancelled", "Cancelled"),
    ]

    teacher = models.ForeignKey(
        Teacher,
        on_delete=models.CASCADE,
        related_name="lessons"
    )

    school_class = models.ForeignKey(
        SchoolClass,
        on_delete=models.CASCADE,
        related_name="lessons"
    )

    subject = models.CharField(
        max_length=150
    )

    title = models.CharField(
        max_length=255
    )

    lesson_date = models.DateField()

    lesson_time = models.TimeField()

    description = models.TextField(
        blank=True,
        default=""
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="scheduled"
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    updated_at = models.DateTimeField(
        auto_now=True
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["school_class"],
                condition=Q(
                    status__in=["scheduled", "live"]
                ),
                name="one_active_lesson_per_class",
            ),
        ]

    def __str__(self):
        return (
            f"{self.school_class.name} "
            f"- {self.subject} "
            f"- {self.title}"
        )


class ClassroomSession(models.Model):
    SESSION_STATUS = [
        ("ready", "Ready"),
        ("live", "Live"),
        ("ended", "Ended"),
    ]

    lesson = models.OneToOneField(
        Lesson,
        on_delete=models.CASCADE,
        related_name="session"
    )

    # Every lesson gets a different room.
    room_id = models.UUIDField(
        default=uuid.uuid4,
        editable=False,
        unique=True
    )

    host = models.ForeignKey(
        Teacher,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="hosted_sessions"
    )

    status = models.CharField(
        max_length=20,
        choices=SESSION_STATUS,
        default="ready"
    )

    started_at = models.DateTimeField(
        null=True,
        blank=True
    )

    ended_at = models.DateTimeField(
        null=True,
        blank=True
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    updated_at = models.DateTimeField(
        auto_now=True
    )

    @property
    def is_live(self):
        return self.status == "live"

    def __str__(self):
        return (
            f"{self.lesson.school_class.name} "
            f"Live Room"
        )

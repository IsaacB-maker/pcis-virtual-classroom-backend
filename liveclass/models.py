from django.db import models


class RecordedLesson(models.Model):

    RECORDING_STATUS = [
        ("processing", "Processing"),
        ("ready", "Ready"),
        ("failed", "Failed"),
    ]

    lesson = models.OneToOneField(
        "classroom.Lesson",
        on_delete=models.CASCADE,
        related_name="recording",
    )

    video = models.FileField(
        upload_to="recordings/%Y/%m/%d/",
        null=True,
        blank=True,
    )

    duration = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Duration in seconds",
    )

    status = models.CharField(
        max_length=20,
        choices=RECORDING_STATUS,
        default="processing",
    )

    recorded_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    def __str__(self):
        return (
            f"{self.lesson.school_class.name} - "
            f"{self.lesson.title}"
        )
from django.contrib import admin

from .models import RecordedLesson


@admin.register(RecordedLesson)
class RecordedLessonAdmin(admin.ModelAdmin):

    list_display = (
        "id",
        "lesson",
        "status",
        "duration",
        "recorded_at",
        "created_at",
    )

    list_filter = (
        "status",
        "recorded_at",
    )

    search_fields = (
        "lesson__title",
        "lesson__subject",
        "lesson__school_class__name",
        "lesson__teacher__name",
    )

    readonly_fields = (
        "created_at",
        "updated_at",
    )

    ordering = (
        "-created_at",
    )
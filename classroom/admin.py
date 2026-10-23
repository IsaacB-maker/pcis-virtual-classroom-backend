from django.contrib import admin

from .models import (
    Teacher,
    SchoolClass,
    Lesson,
    ClassroomSession,
)


@admin.register(Teacher)
class TeacherAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "email",
        "is_active",
        "created_at",
    )

    search_fields = (
        "name",
        "email",
    )

    list_filter = (
        "is_active",
    )


@admin.register(SchoolClass)
class SchoolClassAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "created_at",
    )

    search_fields = (
        "name",
    )


@admin.register(Lesson)
class LessonAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "subject",
        "school_class",
        "teacher",
        "lesson_date",
        "lesson_time",
        "status",
    )

    search_fields = (
        "title",
        "subject",
        "teacher__name",
        "teacher__email",
    )

    list_filter = (
        "school_class",
        "status",
        "lesson_date",
    )


@admin.register(ClassroomSession)
class ClassroomSessionAdmin(admin.ModelAdmin):
    list_display = (
        "lesson",
        "status",
        "started_at",
        "ended_at",
        "created_at",
    )

    search_fields = (
        "lesson__title",
        "lesson__subject",
        "lesson__teacher__name",
    )

    list_filter = (
        "status",
    )

import secrets

from django.contrib import admin, messages
from django.contrib.auth.hashers import make_password
from django.db import transaction
from django.utils.html import format_html, format_html_join

from .models import (
    Student,
    StudentRegistrationCode,
    LessonAttendance,
)


@admin.register(Student)
class StudentAdmin(admin.ModelAdmin):
    list_display = (
        "admission_number",
        "full_name",
        "school_class",
        "fee_status",
        "registration_status",
        "user",
        "created_at",
    )

    list_filter = (
        "fee_status",
        "registration_status",
        "school_class",
    )

    search_fields = (
        "admission_number",
        "full_name",
        "email",
        "phone_number",
    )

    readonly_fields = (
        "created_at",
        "updated_at",
    )

    list_select_related = ("school_class", "user")
    list_per_page = 25

    actions = ("generate_registration_codes",)

    @admin.action(
        description="Generate registration code for selected students"
    )
    def generate_registration_codes(self, request, queryset):
        generated_codes = []
        skipped = 0

        with transaction.atomic():
            students = queryset.select_for_update().order_by(
                "admission_number"
            )

            for student in students:
                # Never issue a new code to an already registered student.
                if (
                    student.user_id is not None
                    or student.registration_status
                    == Student.RegistrationStatus.REGISTERED
                ):
                    skipped += 1
                    continue

                code = secrets.token_urlsafe(8)

                StudentRegistrationCode.objects.update_or_create(
                    student=student,
                    defaults={
                        "code_hash": make_password(code),
                        "expires_at": None,
                        "used_at": None,
                    },
                )

                # Keep the original code only for this response.
                generated_codes.append(
                    (student.admission_number, student.full_name, code)
                )

        if generated_codes:
            code_rows = format_html_join(
                "",
                "<li><strong>{}</strong> — {}: "
                "<code>{}</code></li>",
                (
                    (admission, full_name, code)
                    for admission, full_name, code in generated_codes
                ),
            )

            self.message_user(
                request,
                format_html(
                    "<p><strong>Registration codes generated.</strong>"
                    "</p><p>Copy each code and give it securely to "
                    "the correct student. These codes are shown only "
                    "in this result message.</p><ul>{}</ul>",
                    code_rows,
                ),
                level=messages.SUCCESS,
            )

        if skipped:
            self.message_user(
                request,
                (
                    f"{skipped} student(s) were skipped because "
                    "they have already registered."
                ),
                level=messages.WARNING,
            )

        if not generated_codes and not skipped:
            self.message_user(
                request,
                "No students were selected.",
                level=messages.WARNING,
            )


@admin.register(StudentRegistrationCode)
class StudentRegistrationCodeAdmin(admin.ModelAdmin):
    list_display = (
        "student",
        "expires_at",
        "used_at",
        "created_at",
    )

    search_fields = (
        "student__admission_number",
        "student__full_name",
    )

    readonly_fields = (
        "created_at",
        "used_at",
    )

    list_select_related = ("student",)
    list_per_page = 25


@admin.register(LessonAttendance)
class LessonAttendanceAdmin(admin.ModelAdmin):
    list_display = (
        "student",
        "lesson",
        "get_school_class",
        "joined_at",
        "left_at",
        "duration_seconds",
    )

    list_filter = (
        "lesson__school_class",
        "joined_at",
    )

    search_fields = (
        "student__admission_number",
        "student__full_name",
        "lesson__title",
        "lesson__subject",
    )

    readonly_fields = (
        "student",
        "lesson",
        "joined_at",
        "left_at",
        "duration_seconds",
    )

    list_select_related = (
        "student",
        "lesson",
        "lesson__school_class",
    )

    list_per_page = 50

    @admin.display(description="Class")
    def get_school_class(self, obj):
        return obj.lesson.school_class.name

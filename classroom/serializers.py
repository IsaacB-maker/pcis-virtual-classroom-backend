
from rest_framework import serializers

from .models import (
    Teacher,
    SchoolClass,
    Lesson,
    ClassroomSession,
)


class TeacherSerializer(serializers.ModelSerializer):
    class Meta:
        model = Teacher
        fields = [
            "id",
            "name",
            "email",
            "is_active",
            "created_at",
        ]


class SchoolClassSerializer(serializers.ModelSerializer):
    class Meta:
        model = SchoolClass
        fields = [
            "id",
            "name",
            "created_at",
        ]


class ClassroomSessionSerializer(serializers.ModelSerializer):
    lesson_title = serializers.CharField(
        source="lesson.title",
        read_only=True,
    )

    subject = serializers.CharField(
        source="lesson.subject",
        read_only=True,
    )

    school_class = serializers.CharField(
        source="lesson.school_class.name",
        read_only=True,
    )

    teacher_name = serializers.CharField(
        source="lesson.teacher.name",
        read_only=True,
    )

    room_id = serializers.UUIDField(
        read_only=True,
    )

    host_id = serializers.IntegerField(
        source="host.id",
        read_only=True,
        allow_null=True,
    )

    host_name = serializers.CharField(
        source="host.name",
        read_only=True,
        allow_null=True,
    )

    is_live = serializers.BooleanField(
        read_only=True,
    )

    class Meta:
        model = ClassroomSession

        fields = [
            "id",
            "lesson",
            "lesson_title",
            "subject",
            "school_class",
            "teacher_name",
            "room_id",
            "host_id",
            "host_name",
            "status",
            "is_live",
            "started_at",
            "ended_at",
            "created_at",
            "updated_at",
        ]


class LessonSerializer(serializers.ModelSerializer):
    teacher_name = serializers.CharField(
        source="teacher.name",
        read_only=True,
    )

    class_name = serializers.CharField(
        source="school_class.name",
        read_only=True,
    )

    classroom_session = serializers.SerializerMethodField()

    def get_classroom_session(self, obj):
        """
        The current Django model uses the reverse relationship
        name 'session' for ClassroomSession.

        We expose it to the frontend as 'classroom_session'
        so the existing React code does not need to change.
        """

        session = getattr(
            obj,
            "session",
            None,
        )

        if not session:
            return None

        return ClassroomSessionSerializer(
            session,
            context=self.context,
        ).data

    class Meta:
        model = Lesson

        fields = [
            "id",
            "teacher",
            "teacher_name",
            "school_class",
            "class_name",
            "subject",
            "title",
            "lesson_date",
            "lesson_time",
            "description",
            "status",
            "classroom_session",
            "created_at",
            "updated_at",
        ]


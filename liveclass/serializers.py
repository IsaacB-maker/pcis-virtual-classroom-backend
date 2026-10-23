from rest_framework import serializers

from .models import RecordedLesson


class RecordedLessonSerializer(serializers.ModelSerializer):

    subject = serializers.CharField(
        source="lesson.subject",
        read_only=True,
    )

    title = serializers.CharField(
        source="lesson.title",
        read_only=True,
    )

    description = serializers.CharField(
        source="lesson.description",
        read_only=True,
    )

    teacher_name = serializers.CharField(
        source="lesson.teacher.name",
        read_only=True,
    )

    class_name = serializers.CharField(
        source="lesson.school_class.name",
        read_only=True,
    )

    lesson_date = serializers.DateField(
        source="lesson.lesson_date",
        read_only=True,
    )

    video_url = serializers.SerializerMethodField()

    def get_video_url(self, obj):
        request = self.context.get("request")

        if not obj.video:
            return None

        url = obj.video.url

        if request:
            return request.build_absolute_uri(url)

        return url

    class Meta:
        model = RecordedLesson
        fields = [
            "id",
            "subject",
            "title",
            "description",
            "teacher_name",
            "class_name",
            "lesson_date",
            "video",
            "video_url",
            "duration",
            "status",
            "recorded_at",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields
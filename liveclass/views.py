from rest_framework import generics, status
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.response import Response

from .models import RecordedLesson
from .serializers import RecordedLessonSerializer


class RecordedLessonListView(generics.ListAPIView):
    serializer_class = RecordedLessonSerializer

    def get_queryset(self):
        queryset = (
            RecordedLesson.objects
            .select_related(
                "lesson",
                "lesson__teacher",
                "lesson__school_class",
            )
            .filter(status="ready")
            .order_by("-created_at")
        )

        class_name = self.request.query_params.get("class")

        if class_name:
            class_name = class_name.strip().upper()

            queryset = queryset.filter(
                lesson__school_class__name__iexact=class_name
            )

        return queryset


class RecordedLessonUploadView(generics.CreateAPIView):
    queryset = RecordedLesson.objects.all()
    serializer_class = RecordedLessonSerializer

    parser_classes = (
        MultiPartParser,
        FormParser,
    )

    def create(self, request, *args, **kwargs):
        lesson_id = request.data.get("lesson_id")
        video = request.FILES.get("video")

        if not lesson_id:
            return Response(
                {
                    "error": "lesson_id is required."
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not video:
            return Response(
                {
                    "error": "video file is required."
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            from classroom.models import Lesson

            lesson = Lesson.objects.get(
                id=lesson_id
            )

        except Lesson.DoesNotExist:
            return Response(
                {
                    "error": "Lesson not found."
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        recording, created = (
            RecordedLesson.objects.get_or_create(
                lesson=lesson
            )
        )

        recording.video = video
        recording.status = "ready"
        recording.save()

        serializer = self.get_serializer(
            recording
        )

        return Response(
            serializer.data,
            status=(
                status.HTTP_201_CREATED
                if created
                else status.HTTP_200_OK
            ),
        )
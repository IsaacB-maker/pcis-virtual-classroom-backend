from django.urls import path

from .views import (
    RecordedLessonListView,
    RecordedLessonUploadView,
)


urlpatterns = [
    path(
        "recordings/",
        RecordedLessonListView.as_view(),
        name="recorded-lessons",
    ),

    path(
        "recordings/upload/",
        RecordedLessonUploadView.as_view(),
        name="recorded-lessons-upload",
    ),
]
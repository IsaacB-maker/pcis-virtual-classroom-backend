from django.urls import path

from .views import (
    TeacherLoginView,
    SchoolClassListView,
    LessonListCreateView,
    ClassroomSessionListView,
    StartClassroomSessionView,
    EndClassroomSessionView,
    LiveClassroomView,
)


urlpatterns = [

    # TEACHER LOGIN
    path(
        "teacher-login/",
        TeacherLoginView.as_view(),
        name="teacher-login",
    ),


    # CLASSES P1 - P7
    path(
        "classes/",
        SchoolClassListView.as_view(),
        name="class-list",
    ),


    # LESSONS
    path(
        "lessons/",
        LessonListCreateView.as_view(),
        name="lesson-list-create",
    ),


    # ALL CLASSROOM SESSIONS
    path(
        "sessions/",
        ClassroomSessionListView.as_view(),
        name="session-list",
    ),


    # START LIVE CLASSROOM
    path(
        "sessions/<int:session_id>/start/",
        StartClassroomSessionView.as_view(),
        name="start-classroom",
    ),


    # END LIVE CLASSROOM
    path(
        "sessions/<int:session_id>/end/",
        EndClassroomSessionView.as_view(),
        name="end-classroom",
    ),


    # CHECK LIVE CLASSROOM FOR STUDENTS
    # Example:
    # /api/live-classroom/P1/
    # /api/live-classroom/P2/
    path(
        "live-classroom/<str:school_class>/",
        LiveClassroomView.as_view(),
        name="live-classroom",
    ),

]
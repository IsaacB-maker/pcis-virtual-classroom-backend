
from django.urls import path

from . import views

from . import attendance_views


app_name = "student_management"

urlpatterns = [
    path(
        "register/",
        views.student_register,
        name="student-register",
    ),
    path(
        "login/",
        views.student_login,
        name="student-login",
    ),
    path(
        "registration-code/",
        views.issue_registration_code,
        name="issue-registration-code",
    ),
    path(
        "me/",
        views.student_me,
        name="student-me",
    ),

    path(
    "attendance/join/",
    attendance_views.student_join_lesson,
    name="student-attendance-join",
),
path(
    "attendance/leave/",
    attendance_views.student_leave_lesson,
    name="student-attendance-leave",
),
path(
    "attendance/",
    attendance_views.student_attendance_history,
    name="student-attendance-history",
),
path("csrf/", views.student_csrf_token, name="student-csrf-token"),
]

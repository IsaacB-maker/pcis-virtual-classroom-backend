
from django.db import IntegrityError, transaction
from django.db.models import Q
from django.utils import timezone

from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import (
    Teacher,
    SchoolClass,
    Lesson,
    ClassroomSession,
)

from .serializers import (
    SchoolClassSerializer,
    LessonSerializer,
    ClassroomSessionSerializer,
)


# ============================================================
# HELPER: FIND AN ACTIVE LESSON IN A CLASS
# ============================================================

def get_active_lesson(school_class, exclude_lesson_id=None):
    """
    A class is occupied while a lesson is scheduled or live.

    Completed and cancelled lessons do not block the class.
    """

    lessons = Lesson.objects.filter(
        school_class=school_class,
        status__in=["scheduled", "live"],
    )

    if exclude_lesson_id is not None:
        lessons = lessons.exclude(
            id=exclude_lesson_id
        )

    return lessons.select_related(
        "teacher",
        "school_class",
    ).first()


def class_conflict_response(school_class, lesson):
    teacher_name = lesson.teacher.name

    return Response(
        {
            "error": (
                f"{school_class.name} already has "
                "an active lesson."
            ),
            "message": (
                f"{school_class.name} already has a "
                f"scheduled or live lesson with "
                f"{teacher_name}. Please use another "
                "available class or wait until that "
                "lesson has ended."
            ),
            "active_lesson_id": lesson.id,
            "active_teacher": teacher_name,
            "school_class": school_class.name,
        },
        status=status.HTTP_409_CONFLICT,
    )


# ============================================================
# TEACHER LOGIN
# ============================================================

class TeacherLoginView(APIView):

    def post(self, request):
        email = request.data.get("email")
        password = request.data.get("password")

        if not email or not password:
            return Response(
                {
                    "error": (
                        "Email and password are required."
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            teacher = Teacher.objects.get(
                email__iexact=email
            )
        except Teacher.DoesNotExist:
            return Response(
                {
                    "error": "Invalid email or password."
                },
                status=status.HTTP_401_UNAUTHORIZED,
            )

        if not teacher.is_active:
            return Response(
                {
                    "error": (
                        "This teacher account is inactive."
                    )
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        if teacher.password != password:
            return Response(
                {
                    "error": "Invalid email or password."
                },
                status=status.HTTP_401_UNAUTHORIZED,
            )

        return Response(
            {
                "id": teacher.id,
                "name": teacher.name,
                "email": teacher.email,
            },
            status=status.HTTP_200_OK,
        )


# ============================================================
# SCHOOL CLASSES
# ============================================================

class SchoolClassListView(APIView):

    def get(self, request):
        classes = SchoolClass.objects.all().order_by(
            "name"
        )

        serializer = SchoolClassSerializer(
            classes,
            many=True,
        )

        return Response(serializer.data)


# ============================================================
# LESSONS: LIST AND CREATE
# ============================================================

class LessonListCreateView(APIView):

    def get(self, request):
        """
        Return lessons.

        Optional:
        /api/lessons/?class=P4
        """

        lessons = Lesson.objects.select_related(
            "teacher",
            "school_class",
            "session",
        ).order_by(
            "-lesson_date",
            "-lesson_time",
        )

        school_class = request.query_params.get(
            "class"
        )

        if school_class:
            lessons = lessons.filter(
                school_class__name__iexact=school_class
            )

        serializer = LessonSerializer(
            lessons,
            many=True,
        )

        return Response(serializer.data)

    def post(self, request):
        """
        Create one lesson and its READY classroom session.

        A class cannot have a second scheduled or live
        lesson until the existing lesson is completed
        or cancelled.
        """

        serializer = LessonSerializer(
            data=request.data
        )

        if not serializer.is_valid():
            return Response(
                serializer.errors,
                status=status.HTTP_400_BAD_REQUEST,
            )

        teacher_id = request.data.get("teacher")
        school_class_id = request.data.get("school_class")

        # ----------------------------------------------------
        # CHECK TEACHER
        # ----------------------------------------------------

        try:
            teacher = Teacher.objects.get(
                id=teacher_id,
                is_active=True,
            )
        except (
            Teacher.DoesNotExist,
            ValueError,
            TypeError,
        ):
            return Response(
                {
                    "error": (
                        "The selected teacher does not "
                        "exist or is inactive."
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        # ----------------------------------------------------
        # CHECK CLASS
        # ----------------------------------------------------

        try:
            school_class = SchoolClass.objects.get(
                id=school_class_id
            )
        except (
            SchoolClass.DoesNotExist,
            ValueError,
            TypeError,
        ):
            return Response(
                {
                    "error": (
                        "The selected class does not exist."
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        # ----------------------------------------------------
        # CREATE SAFELY
        # ----------------------------------------------------

        try:
            with transaction.atomic():

                # Lock the class row on databases that
                # support select_for_update().
                locked_class = (
                    SchoolClass.objects.select_for_update()
                    .get(id=school_class.id)
                )

                active_lesson = get_active_lesson(
                    locked_class
                )

                if active_lesson:
                    return class_conflict_response(
                        locked_class,
                        active_lesson,
                    )

                lesson = serializer.save(
                    teacher=teacher,
                    school_class=locked_class,
                )

                classroom_session = (
                    ClassroomSession.objects.create(
                        lesson=lesson,
                        status="ready",
                    )
                )

        except IntegrityError:
            # The database constraint is the final
            # protection against duplicate active lessons.
            active_lesson = get_active_lesson(
                school_class
            )

            if active_lesson:
                return class_conflict_response(
                    school_class,
                    active_lesson,
                )

            return Response(
                {
                    "error": (
                        "The lesson could not be created "
                        "because of a database conflict. "
                        "Please try again."
                    )
                },
                status=status.HTTP_409_CONFLICT,
            )

        # ----------------------------------------------------
        # RESPONSE
        # ----------------------------------------------------

        return Response(
            {
                "message": "Lesson created successfully.",
                "lesson": LessonSerializer(
                    lesson
                ).data,
                "classroom_session": (
                    ClassroomSessionSerializer(
                        classroom_session
                    ).data
                ),
            },
            status=status.HTTP_201_CREATED,
        )


# ============================================================
# CLASSROOM SESSIONS
# ============================================================

class ClassroomSessionListView(APIView):

    def get(self, request):
        """
        Optional filters:

        /api/sessions/?class=P4
        /api/sessions/?status=live
        /api/sessions/?class=P4&status=live
        """

        sessions = ClassroomSession.objects.select_related(
            "lesson",
            "lesson__teacher",
            "lesson__school_class",
            "host",
        ).order_by(
            "-created_at"
        )

        school_class = request.query_params.get(
            "class"
        )

        if school_class:
            sessions = sessions.filter(
                lesson__school_class__name__iexact=school_class
            )

        status_filter = request.query_params.get(
            "status"
        )

        if status_filter:
            sessions = sessions.filter(
                status=status_filter
            )

        serializer = ClassroomSessionSerializer(
            sessions,
            many=True,
        )

        return Response(serializer.data)


# ============================================================
# START CLASSROOM SESSION
# ============================================================

class StartClassroomSessionView(APIView):

    def post(self, request, session_id):
        """
        Only the lesson's teacher can start the session.

        The class must not have another scheduled or
        live lesson.
        """

        teacher_id = request.data.get("teacher")

        if not teacher_id:
            return Response(
                {
                    "error": "Teacher ID is required."
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            with transaction.atomic():

                # Get the session and its lesson.
                session = (
                    ClassroomSession.objects.select_related(
                        "lesson",
                        "lesson__teacher",
                        "lesson__school_class",
                    ).get(
                        id=session_id
                    )
                )

                # Lock the relevant class where supported.
                school_class = (
                    SchoolClass.objects.select_for_update()
                    .get(
                        id=session.lesson.school_class_id
                    )
                )

                # Confirm the teacher owns this lesson.
                if str(
                    session.lesson.teacher_id
                ) != str(teacher_id):
                    return Response(
                        {
                            "error": (
                                "Only the lesson teacher "
                                "can start this classroom."
                            )
                        },
                        status=status.HTTP_403_FORBIDDEN,
                    )

                # Ended sessions cannot be restarted.
                if session.status == "ended":
                    return Response(
                        {
                            "error": (
                                "This classroom session "
                                "has already ended."
                            )
                        },
                        status=status.HTTP_400_BAD_REQUEST,
                    )

                # Do not start completed or cancelled lessons.
                if session.lesson.status in [
                    "completed",
                    "cancelled",
                ]:
                    return Response(
                        {
                            "error": (
                                "This lesson is no longer "
                                "available to start."
                            )
                        },
                        status=status.HTTP_400_BAD_REQUEST,
                    )

                # Block any OTHER scheduled or live lesson
                # in this class, not just a live session.
                active_lesson = get_active_lesson(
                    school_class,
                    exclude_lesson_id=session.lesson_id,
                )

                if active_lesson:
                    return class_conflict_response(
                        school_class,
                        active_lesson,
                    )

                # Start the session.
                session.status = "live"
                session.host = session.lesson.teacher

                if not session.started_at:
                    session.started_at = timezone.now()

                session.ended_at = None

                session.save(
                    update_fields=[
                        "status",
                        "host",
                        "started_at",
                        "ended_at",
                        "updated_at",
                    ]
                )

                # Mark the lesson live.
                lesson = session.lesson
                lesson.status = "live"

                lesson.save(
                    update_fields=[
                        "status",
                        "updated_at",
                    ]
                )

        except ClassroomSession.DoesNotExist:
            return Response(
                {
                    "error": "Classroom session not found."
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        except SchoolClass.DoesNotExist:
            return Response(
                {
                    "error": "The selected class was not found."
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        except IntegrityError:
            return Response(
                {
                    "error": (
                        "This class could not be started "
                        "because another lesson conflicts "
                        "with it. Refresh and try again."
                    )
                },
                status=status.HTTP_409_CONFLICT,
            )

        return Response(
            {
                "message": "Classroom is now live.",
                "session": ClassroomSessionSerializer(
                    session
                ).data,
            },
            status=status.HTTP_200_OK,
        )


# ============================================================
# END CLASSROOM SESSION
# ============================================================

class EndClassroomSessionView(APIView):

    def post(self, request, session_id):
        """
        Only the lesson's teacher can end the session.

        Session -> ended
        Lesson  -> completed

        Completing the lesson releases the class.
        """

        teacher_id = request.data.get("teacher")

        if not teacher_id:
            return Response(
                {
                    "error": "Teacher ID is required."
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            with transaction.atomic():

                session = (
                    ClassroomSession.objects.select_related(
                        "lesson",
                        "lesson__teacher",
                        "lesson__school_class",
                    ).get(
                        id=session_id
                    )
                )

                if str(
                    session.lesson.teacher_id
                ) != str(teacher_id):
                    return Response(
                        {
                            "error": (
                                "Only the lesson teacher "
                                "can end this classroom."
                            )
                        },
                        status=status.HTTP_403_FORBIDDEN,
                    )

                # Keep both records consistent if the
                # session was already ended.
                if session.status != "ended":
                    session.status = "ended"
                    session.ended_at = timezone.now()

                    session.save(
                        update_fields=[
                            "status",
                            "ended_at",
                            "updated_at",
                        ]
                    )

                lesson = session.lesson

                if lesson.status != "completed":
                    lesson.status = "completed"

                    lesson.save(
                        update_fields=[
                            "status",
                            "updated_at",
                        ]
                    )

        except ClassroomSession.DoesNotExist:
            return Response(
                {
                    "error": "Classroom session not found."
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        return Response(
            {
                "message": (
                    "Classroom session ended. "
                    "This class is now available for "
                    "another lesson."
                ),
                "session": ClassroomSessionSerializer(
                    session
                ).data,
            },
            status=status.HTTP_200_OK,
        )


# ============================================================
# LIVE CLASSROOM FOR ONE SPECIFIC CLASS
# ============================================================

class LiveClassroomView(APIView):

    def get(self, request, school_class):
        """
        Example:
        /api/live/P4/

        Returns a live session for P4 only.
        """

        session = (
            ClassroomSession.objects.select_related(
                "lesson",
                "lesson__teacher",
                "lesson__school_class",
                "host",
            )
            .filter(
                lesson__school_class__name__iexact=school_class,
                status="live",
                lesson__status="live",
            )
            .order_by(
                "-started_at"
            )
            .first()
        )

        if not session:
            return Response(
                {
                    "live": False,
                    "message": (
                        "There is no lesson going on "
                        "in this class."
                    ),
                    "school_class": school_class.upper(),
                },
                status=status.HTTP_200_OK,
            )

        return Response(
            {
                "live": True,
                "school_class": (
                    session.lesson.school_class.name
                ),
                "subject": session.lesson.subject,
                "topic": session.lesson.title,
                "description": session.lesson.description,
                "teacher": session.lesson.teacher.name,
                "room_id": str(session.room_id),
                "session": ClassroomSessionSerializer(
                    session
                ).data,
            },
            status=status.HTTP_200_OK,
        )

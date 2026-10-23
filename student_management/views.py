
import secrets

from django.contrib.auth import (
    authenticate,
    get_user_model,
    login as auth_login,
)
from django.contrib.auth.hashers import make_password
from django.db import transaction

from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from django.http import JsonResponse
from django.middleware.csrf import get_token
from django.views.decorators.csrf import ensure_csrf_cookie

from .models import Student, StudentRegistrationCode
from .serializers import StudentRegistrationSerializer


User = get_user_model()


def get_student_record(user):
    """Return the student record linked to an authenticated user."""
    try:
        return Student.objects.select_related(
            "school_class"
        ).get(user=user)
    except Student.DoesNotExist:
        return None


def student_access_error(student):
    """Explain why a student cannot access lessons."""
    if not student.user or not student.user.is_active:
        return "This student account is inactive."

    if (
        student.registration_status
        != Student.RegistrationStatus.REGISTERED
    ):
        return "Please complete student registration first."

    if student.fee_status != Student.FeeStatus.PAID:
        return (
            "Your fees have not been confirmed as paid. "
            "You can access your student portal, but lessons "
            "remain locked until the school confirms payment."
        )

    if not student.school_class:
        return (
            "No class has been assigned to your student record. "
            "Please contact the school administration."
        )

    return None


def student_response_data(student):
    """Return safe student information for the frontend."""
    access_error = student_access_error(student)

    return {
        "admission_number": student.admission_number,
        "full_name": student.full_name,
        "school_class": (
            student.school_class.name
            if student.school_class
            else None
        ),
        "fee_status": student.fee_status,
        "registration_status": student.registration_status,
        "access_allowed": access_error is None,
        "access_message": access_error,
    }


@api_view(["POST"])
@permission_classes([AllowAny])
def student_register(request):
    """Register a student against an existing school record."""
    serializer = StudentRegistrationSerializer(data=request.data)

    if not serializer.is_valid():
        return Response(
            {"errors": serializer.errors},
            status=status.HTTP_400_BAD_REQUEST,
        )

    student = serializer.save()
    # Registration does not automatically grant lesson access.
    access_error = student_access_error(student)

    return Response(
        {
            "message": "Student registered successfully.",
            "student": StudentSerializer(student).data,
            "access_allowed": student.can_access_lessons,
            "access_message": access_error,
        },
        status=status.HTTP_201_CREATED,
    )


@ensure_csrf_cookie
def student_csrf_token(request):
    return JsonResponse({
        "csrfToken": get_token(request),
    })
    return Response(
        {
            "message": (
                "Registration completed successfully. "
                "You can now log in using your admission number "
                "and password."
            ),
            "student": student_response_data(student),
            "access_allowed": access_error is None,
            "access_message": access_error,
        },
        status=status.HTTP_201_CREATED,
    )



@api_view(["POST"])
@permission_classes([AllowAny])
def student_login(request):
    """
    Student login using the full name and class assigned by the school.

    POST /api/students/login/
    Body: {"full_name": "...", "school_class": "Primary 1"}
    """
    from django.db import transaction

    full_name = request.data.get("full_name", "").strip()
    school_class_name = request.data.get("school_class", "").strip()

    if not full_name or not school_class_name:
        return Response(
            {
                "error": "Please enter your full name and select your class."
            },
            status=status.HTTP_400_BAD_REQUEST,
        )

    # Match the student against the school's existing records.
    matching_students = Student.objects.select_related(
        "school_class", "user"
    ).filter(
        full_name__iexact=full_name,
        school_class__name__iexact=school_class_name,
    )

    # Never choose arbitrarily if multiple students have the same name
    # in the same class.
    matching_count = matching_students.count()

    if matching_count == 0:
        return Response(
            {
                "error": (
                    "No matching student was found. "
                    "Please check your full name and class with the school."
                )
            },
            status=status.HTTP_401_UNAUTHORIZED,
        )

    if matching_count > 1:
        return Response(
            {
                "error": (
                    "More than one student has these details. "
                    "Please contact the school administrator."
                )
            },
            status=status.HTTP_409_CONFLICT,
        )

    with transaction.atomic():
        student = matching_students.select_for_update().get()

        # A school-created student record is treated as registered
        # for this new school-managed login workflow.
        if student.user_id is None:
            username = f"pcis_student_{student.pk}"

            user = User.objects.create_user(
                username=username,
                password=None,
            )
            user.is_active = True
            user.save(update_fields=["is_active"])

            student.user = user
            student.registration_status = (
                Student.RegistrationStatus.REGISTERED
            )
            student.save(
                update_fields=[
                    "user",
                    "registration_status",
                    "updated_at",
                ]
            )
        else:
            user = student.user

        if not user.is_active:
            return Response(
                {
                    "error": (
                        "This student account is inactive. "
                        "Please contact the school administrator."
                    )
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        # Establish the Django session required by attendance endpoints.
        auth_login(
            request,
            user,
            backend="django.contrib.auth.backends.ModelBackend",
        )

    # Reuse the existing response helper so the frontend receives
    # the student's access status and school-class information.
    student.refresh_from_db()
    response_data = student_response_data(student)

    return Response(
        {
            "message": "Student login successful.",
            "student": response_data,
        },
        status=status.HTTP_200_OK,
    )



@api_view(["POST"])
@permission_classes([IsAuthenticated])
@transaction.atomic
def issue_registration_code(request):
    """
    Allow authorized school staff to issue a registration code.

    The code does not expire automatically, is stored only as a
    hash, and can be used once to create the student's account.
    """
    if not request.user.is_staff:
        return Response(
            {
                "error": (
                    "Only authorized school staff can issue codes."
                )
            },
            status=status.HTTP_403_FORBIDDEN,
        )

    admission_number = str(
        request.data.get("admission_number", "")
    ).strip()

    if not admission_number:
        return Response(
            {"error": "Admission number is required."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        student = Student.objects.select_for_update().get(
            admission_number__iexact=admission_number
        )
    except Student.DoesNotExist:
        return Response(
            {
                "error": (
                    "No student record exists for that "
                    "admission number."
                )
            },
            status=status.HTTP_404_NOT_FOUND,
        )

    if (
        student.user_id is not None
        or student.registration_status
        == Student.RegistrationStatus.REGISTERED
    ):
        return Response(
            {"error": "This student has already registered."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    code = secrets.token_urlsafe(8)

    StudentRegistrationCode.objects.update_or_create(
        student=student,
        defaults={
            "code_hash": make_password(code),
            "expires_at": None,
            "used_at": None,
        },
    )

    # Show the raw code only in this response; never store it as text.
    return Response(
        {
            "message": (
                "Registration code issued successfully. "
                "Give this code securely to the correct student."
            ),
            "admission_number": student.admission_number,
            "registration_code": code,
            "expires_at": None,
        },
        status=status.HTTP_201_CREATED,
    )


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def student_me(request):
    """Return the student's current portal and lesson-access status."""
    student = get_student_record(request.user)

    if student is None:
        return Response(
            {"error": "No student record is linked to this account."},
            status=status.HTTP_403_FORBIDDEN,
        )

    student_data = student_response_data(student)

    return Response(
        {
            "student": student_data,
            "access_allowed": student_data["access_allowed"],
            "access_message": student_data["access_message"],
        },
        status=status.HTTP_200_OK,
    )


import json

from django.apps import apps
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.http import JsonResponse
from django.middleware.csrf import get_token
from django.views.decorators.csrf import csrf_protect
from django.views.decorators.http import require_http_methods
from django.db.models.deletion import ProtectedError

from classroom.models import (
    Teacher,
    SchoolClass,
    Lesson,
    ClassroomSession,
)
from student_management.models import (
    Student,
    LessonAttendance,
)
from liveclass.models import RecordedLesson


# Only these school-operation models are exposed by this API.
# Administrator accounts and registration-code records are excluded.
RESOURCES = {
    "teachers": {
        "model": Teacher,
        "app": "classroom",
        "model_name": "teacher",
        "fields": {"name", "email", "password", "is_active"},
        "writable": True,
    },
    "classes": {
        "model": SchoolClass,
        "app": "classroom",
        "model_name": "schoolclass",
        "fields": {"name"},
        "writable": True,
    },
    "students": {
        "model": Student,
        "app": "student_management",
        "model_name": "student",
        "fields": {
            "admission_number",
            "full_name",
            "email",
            "phone_number",
            "school_class_id",
            "fee_status",
            "registration_status",
        },
        "writable": True,
    },
    "lessons": {
        "model": Lesson,
        "app": "classroom",
        "model_name": "lesson",
        "fields": {
            "teacher_id",
            "school_class_id",
            "subject",
            "title",
            "lesson_date",
            "lesson_time",
            "description",
            "status",
        },
        "writable": True,
    },
    "sessions": {
        "model": ClassroomSession,
        "app": "classroom",
        "model_name": "classroomsession",
        "fields": set(),
        "writable": False,
    },
    "attendance": {
        "model": LessonAttendance,
        "app": "student_management",
        "model_name": "lessonattendance",
        "fields": set(),
        "writable": False,
    },
    "recordings": {
        "model": RecordedLesson,
        "app": "liveclass",
        "model_name": "recordedlesson",
        "fields": set(),
        "writable": False,
    },
}


def error_response(message, status=400, errors=None):
    response = {
        "success": False,
        "message": message,
    }

    if errors is not None:
        response["errors"] = errors

    return JsonResponse(response, status=status)


def read_json(request):
    try:
        data = json.loads(request.body or b"{}")
    except (json.JSONDecodeError, UnicodeDecodeError):
        return None

    return data if isinstance(data, dict) else None


def authorized(request, resource, action):
    """
    The owner can access school data.
    Other administrators need the specific Django model permission.
    """
    user = request.user

    if not (
        user
        and user.is_authenticated
        and user.is_active
        and user.is_staff
    ):
        return False

    if user.is_superuser:
        return True

    config = RESOURCES[resource]
    permission = (
        f"{config['app']}.{action}_{config['model_name']}"
    )

    return user.has_perm(permission)


def require_access(request, resource, action):
    if not (
        request.user.is_authenticated
        and request.user.is_active
        and request.user.is_staff
    ):
        return error_response(
            "Please sign in with an authorized administrator account.",
            401,
        )

    if not authorized(request, resource, action):
        return error_response(
            f"You do not have permission to {action} {resource}.",
            403,
        )

    return None


def iso(value):
    return value.isoformat() if value is not None else None


def serialize_teacher(obj):
    return {
        "id": obj.id,
        "name": obj.name,
        "email": obj.email,
        "is_active": obj.is_active,
        "created_at": iso(obj.created_at),
    }


def serialize_class(obj):
    return {
        "id": obj.id,
        "name": obj.name,
        "created_at": iso(obj.created_at),
    }


def serialize_student(obj):
    linked_user = obj.user

    return {
        "id": obj.id,
        "admission_number": obj.admission_number,
        "full_name": obj.full_name,
        "email": obj.email,
        "phone_number": obj.phone_number,
        "school_class_id": obj.school_class_id,
        "school_class_name": (
            obj.school_class.name if obj.school_class else None
        ),
        "fee_status": obj.fee_status,
        "registration_status": obj.registration_status,
        "user_id": obj.user_id,
        "account_is_active": (
            linked_user.is_active if linked_user else False
        ),
        "can_access_lessons": obj.can_access_lessons,
        "created_at": iso(obj.created_at),
        "updated_at": iso(obj.updated_at),
    }


def serialize_lesson(obj):
    session = getattr(obj, "session", None)
    return {
        "id": obj.id,
        "teacher_id": obj.teacher_id,
        "teacher_name": obj.teacher.name if obj.teacher else None,
        "school_class_id": obj.school_class_id,
        "class_name": (
            obj.school_class.name if obj.school_class else None
        ),
        "subject": obj.subject,
        "title": obj.title,
        "lesson_date": iso(obj.lesson_date),
        "lesson_time": iso(obj.lesson_time),
        "description": obj.description,
        "status": obj.status,
        "classroom_session": (
            serialize_session(session) if session else None
        ),
        "created_at": iso(obj.created_at),
        "updated_at": iso(obj.updated_at),
    }


def serialize_session(obj):
    lesson = obj.lesson

    return {
        "id": obj.id,
        "lesson_id": lesson.id,
        "lesson_title": lesson.title,
        "subject": lesson.subject,
        "school_class_id": lesson.school_class_id,
        "class_name": (
            lesson.school_class.name if lesson.school_class else None
        ),
        "teacher_name": (
            lesson.teacher.name if lesson.teacher else None
        ),
        "room_id": str(obj.room_id),
        "host_id": obj.host_id,
        "status": obj.status,
        "is_live": obj.is_live,
        "started_at": iso(obj.started_at),
        "ended_at": iso(obj.ended_at),
        "created_at": iso(obj.created_at),
        "updated_at": iso(obj.updated_at),
    }



def serialize_attendance(obj):
    student = getattr(obj, "student", None)
    lesson = getattr(obj, "lesson", None)

    student_class = (
        getattr(getattr(student, "school_class", None), "name", None)
        if student
        else None
    )

    lesson_class = (
        getattr(getattr(lesson, "school_class", None), "name", None)
        if lesson
        else None
    )

    class_name = student_class or lesson_class

    # An attendance record with a join timestamp means the
    # student attended. Leaving the lesson does not mean absent.
    status = "Present" if obj.joined_at else "Unknown"

    return {
        "id": obj.id,
        "student_id": obj.student_id,
        "student_name": student.full_name if student else None,
        "full_name": student.full_name if student else None,

        "class_name": class_name,
        "school_class_name": class_name,
        "student_class": class_name,

        "lesson_id": obj.lesson_id,
        "lesson_title": lesson.title if lesson else None,
        "lesson_name": lesson.title if lesson else None,
        "lesson_class_name": lesson_class,

        "status": status,
        "attendance_status": status,

        "date": iso(obj.joined_at),
        "attendance_date": iso(obj.joined_at),
        "joined_at": iso(obj.joined_at),
        "left_at": iso(obj.left_at),
        "duration_seconds": obj.duration_seconds,
    }


def serialize_recording(obj, request):
    video_url = None

    if obj.video:
        try:
            video_url = request.build_absolute_uri(obj.video.url)
        except (ValueError, AttributeError):
            video_url = None

    return {
        "id": obj.id,
        "lesson_id": obj.lesson_id,
        "title": obj.lesson.title,
        "subject": obj.lesson.subject,
        "teacher_name": obj.lesson.teacher.name,
        "class_name": obj.lesson.school_class.name,
        "video_url": video_url,
        "duration_seconds": obj.duration_seconds,
        "status": obj.status,
        "recorded_at": iso(obj.recorded_at),
        "created_at": iso(obj.created_at),
        "updated_at": iso(obj.updated_at),
    }


SERIALIZERS = {
    "teachers": serialize_teacher,
    "classes": serialize_class,
    "students": serialize_student,
    "lessons": serialize_lesson,
    "sessions": serialize_session,
    "attendance": serialize_attendance,
    "recordings": serialize_recording,
}


def serialize_object(resource, obj, request):
    serializer = SERIALIZERS[resource]

    if resource == "recordings":
        return serializer(obj, request)

    return serializer(obj)

def get_queryset(resource):
    model = RESOURCES[resource]["model"]
    queryset = model.objects.all()

    if resource == "students":
        queryset = queryset.select_related("school_class", "user")

    elif resource == "lessons":
        queryset = queryset.select_related(
            "teacher",
            "school_class",
            "session",
        )

    elif resource == "sessions":
        queryset = queryset.select_related(
            "lesson",
            "lesson__teacher",
            "lesson__school_class",
        )

   
    elif resource == "attendance":
        queryset = queryset.select_related(
            "student",
            "student__school_class",
            "lesson",
            "lesson__school_class",
        )

    elif resource == "recordings":
        queryset = queryset.select_related(
            "lesson",
            "lesson__teacher",
            "lesson__school_class",
        )

    return queryset


def validate_payload(resource, data, partial=False, instance=None):
    config = RESOURCES[resource]

    if not config["writable"]:
        return None, "This resource is read-only."

    unexpected = sorted(set(data.keys()) - config["fields"])

    if unexpected:
        return None, (
            "Unsupported fields: " + ", ".join(unexpected)
        )

    if partial and not data:
        return None, "Provide at least one field to update."

    model = config["model"]

    try:
        with transaction.atomic():
            obj = instance if instance is not None else model()

            for field, value in data.items():
                setattr(obj, field, value)

            obj.full_clean()
            obj.save()

            # Validate and persist the object before leaving the
            # transaction; return it only after successful validation.
            return obj, None

    except ValidationError as exc:
        if hasattr(exc, "message_dict"):
            return None, exc.message_dict

        return None, exc.messages

    except (IntegrityError, ProtectedError):
        return None, (
            "The record conflicts with existing school records."
        )

    except (TypeError, ValueError, AttributeError) as exc:
        return None, str(exc)


@require_http_methods(["GET", "POST"])
@csrf_protect
def data_collection_view(request, resource):
    if resource not in RESOURCES:
        return error_response("Unknown resource.", 404)

    action = "view" if request.method == "GET" else "add"
    denied = require_access(request, resource, action)

    if denied:
        return denied

    if request.method == "GET":
        queryset = get_queryset(resource).order_by("-pk")

        # Optional filtering supported by the React portal.
        class_name = request.GET.get("class")
        if class_name and resource in {
            "students", "lessons", "sessions", "attendance", "recordings"
        }:
            if resource == "students":
                queryset = queryset.filter(school_class__name=class_name)
            elif resource == "lessons":
                queryset = queryset.filter(school_class__name=class_name)
            elif resource == "sessions":
                queryset = queryset.filter(lesson__school_class__name=class_name)
            elif resource == "attendance":
                queryset = queryset.filter(
                    student__school_class__name=class_name
                )
            elif resource == "recordings":
                queryset = queryset.filter(
                    lesson__school_class__name=class_name
                )

        return JsonResponse({
            "success": True,
            "results": [
                serialize_object(resource, obj, request)
                for obj in queryset
            ],
        })

    data = read_json(request)

    if data is None:
        return error_response("Invalid JSON request.")

    obj, errors = validate_payload(resource, data)

    if errors:
        return error_response(
            "The record could not be saved.",
            400,
            errors,
        )

    return JsonResponse({
        "success": True,
        "message": "Record created successfully.",
        "result": serialize_object(resource, obj, request),
    }, status=201)


@require_http_methods(["GET", "PATCH", "PUT", "DELETE"])
@csrf_protect
def data_detail_view(request, resource, object_id):
    if resource not in RESOURCES:
        return error_response("Unknown resource.", 404)

    if request.method == "GET":
        action = "view"
    elif request.method == "DELETE":
        action = "delete"
    else:
        action = "change"

    denied = require_access(request, resource, action)

    if denied:
        return denied

    try:
        obj = get_queryset(resource).get(pk=object_id)
    except RESOURCES[resource]["model"].DoesNotExist:
        return error_response("Record not found.", 404)

    if request.method == "GET":
        return JsonResponse({
            "success": True,
            "result": serialize_object(resource, obj, request),
        })

    if request.method == "DELETE":
        if resource in {"sessions", "attendance"}:
            return error_response(
                "Sessions and attendance are managed by the classroom system.",
                405,
            )

        if resource == "recordings":
            if obj.video:
                obj.video.delete(save=False)

        try:
            obj.delete()
        except (ProtectedError, IntegrityError):
            return error_response(
                "This record is linked to other records and cannot be deleted.",
                409,
            )

        return JsonResponse({
            "success": True,
            "message": "Record deleted successfully.",
        })

    data = read_json(request)

    if data is None:
        return error_response("Invalid JSON request.")

    obj, errors = validate_payload(
        resource,
        data,
        partial=True,
        instance=obj,
    )

    if errors:
        return error_response(
            "The record could not be updated.",
            400,
            errors,
        )

    return JsonResponse({
        "success": True,
        "message": "Record updated successfully.",
        "result": serialize_object(resource, obj, request),
    })

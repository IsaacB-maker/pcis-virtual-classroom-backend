
import json

from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.contrib.auth.models import Permission
from django.core.exceptions import ValidationError
from django.db import transaction
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_protect
from django.views.decorators.http import require_GET, require_http_methods

User = get_user_model()

# Only these school-operation models may have permissions assigned
# through this API. Administrator-account management is deliberately
# excluded from this list.
ALLOWED_MODELS = {
    "classroom": {
        "teacher",
        "schoolclass",
        "lesson",
        "classroomsession",
    },
    "student_management": {
        "student",
        "studentregistrationcode",
        "lessonattendance",
    },
    "liveclass": {
        "recordedlesson",
    },
}

ALLOWED_ACTIONS = {"view", "add", "change", "delete"}


def error_response(message, status=400):
    return JsonResponse(
        {"success": False, "message": message},
        status=status,
    )


def owner_required(request):
    user = request.user

    return bool(
        user
        and user.is_authenticated
        and user.is_active
        and user.is_superuser
    )


def allowed_permissions():
    permissions = Permission.objects.select_related("content_type")

    return [
        permission
        for permission in permissions
        if (
            permission.content_type.app_label in ALLOWED_MODELS
            and permission.content_type.model
            in ALLOWED_MODELS[permission.content_type.app_label]
            and permission.codename.split("_", 1)[0]
            in ALLOWED_ACTIONS
            and "_" in permission.codename
        )
    ]


def permission_key(permission):
    return (
        f"{permission.content_type.app_label}."
        f"{permission.codename}"
    )


def administrator_data(user):
    allowed = {
        permission_key(permission): permission
        for permission in allowed_permissions()
    }

    assigned = user.user_permissions.filter(
        id__in=[permission.id for permission in allowed.values()]
    ).select_related("content_type")

    return {
        "id": user.id,
        "username": user.get_username(),
        "email": user.email,
        "is_active": user.is_active,
        "permissions": sorted(
            permission_key(permission)
            for permission in assigned
        ),
    }


def read_json(request):
    try:
        data = json.loads(request.body or b"{}")
    except (json.JSONDecodeError, UnicodeDecodeError):
        return None

    return data if isinstance(data, dict) else None


def resolve_permissions(permission_names):
    if not isinstance(permission_names, list):
        raise ValueError("'permissions' must be a list.")

    if not all(
        isinstance(name, str) and name.strip()
        for name in permission_names
    ):
        raise ValueError("Every permission must be a non-empty string.")

    if len(permission_names) != len(set(permission_names)):
        raise ValueError("Duplicate permissions are not allowed.")

    available = {
        permission_key(permission): permission
        for permission in allowed_permissions()
    }

    unknown = sorted(set(permission_names) - set(available))

    if unknown:
        raise ValueError(
            "Unsupported permissions: " + ", ".join(unknown)
        )

    return [available[name] for name in permission_names]


@require_GET
def administrator_list_view(request):
    if not owner_required(request):
        return error_response("Owner access required.", 403)

    administrators = User.objects.filter(
        is_staff=True,
        is_superuser=False,
    ).order_by("username")

    return JsonResponse({
        "success": True,
        "administrators": [
            administrator_data(user)
            for user in administrators
        ],
    })


@csrf_protect
@require_http_methods(["POST"])
def administrator_create_view(request):
    if not owner_required(request):
        return error_response("Owner access required.", 403)

    data = read_json(request)

    if data is None:
        return error_response("Invalid JSON request.")

    username = data.get("username")
    email = data.get("email", "")
    password = data.get("password")
    permission_names = data.get("permissions", [])

    if not isinstance(username, str) or not username.strip():
        return error_response("A username is required.")

    username = username.strip()

    if not isinstance(email, str):
        return error_response("Email must be text.")

    if not isinstance(password, str) or not password:
        return error_response("A password is required.")

    if User.objects.filter(username__iexact=username).exists():
        return error_response("That username is already in use.")

    try:
        permissions = resolve_permissions(permission_names)
    except ValueError as exc:
        return error_response(str(exc))

    candidate = User(username=username, email=email.strip())

    try:
        validate_password(password, user=candidate)
    except ValidationError as exc:
        return error_response(
            " ".join(exc.messages)
        )

    with transaction.atomic():
        user = User(
            username=username,
            email=email.strip(),
            is_active=True,
            is_staff=True,
            is_superuser=False,
        )
        user.set_password(password)
        user.save()
        user.user_permissions.set(permissions)

    return JsonResponse({
        "success": True,
        "message": "Administrator account created.",
        "administrator": administrator_data(user),
    }, status=201)


@csrf_protect
@require_http_methods(["POST"])
def administrator_permissions_view(request, user_id):
    if not owner_required(request):
        return error_response("Owner access required.", 403)

    try:
        administrator = User.objects.get(
            pk=user_id,
            is_staff=True,
            is_superuser=False,
        )
    except User.DoesNotExist:
        return error_response(
            "School administrator not found.",
            404,
        )

    data = read_json(request)

    if data is None or "permissions" not in data:
        return error_response(
            "Provide a permissions list."
        )

    try:
        permissions = resolve_permissions(data["permissions"])
    except ValueError as exc:
        return error_response(str(exc))

    administrator.user_permissions.set(permissions)

    return JsonResponse({
        "success": True,
        "message": "Administrator permissions updated.",
        "administrator": administrator_data(administrator),
    })


@csrf_protect
@require_http_methods(["POST"])
def administrator_deactivate_view(request, user_id):
    if not owner_required(request):
        return error_response("Owner access required.", 403)

    try:
        administrator = User.objects.get(
            pk=user_id,
            is_staff=True,
            is_superuser=False,
        )
    except User.DoesNotExist:
        return error_response(
            "School administrator not found.",
            404,
        )

    administrator.is_active = False
    administrator.save(update_fields=["is_active"])

    return JsonResponse({
        "success": True,
        "message": "Administrator account deactivated.",
        "administrator": administrator_data(administrator),
    })

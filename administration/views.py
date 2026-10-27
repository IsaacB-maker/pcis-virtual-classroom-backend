
import json

from django.contrib.auth import authenticate, login, logout
from django.http import JsonResponse
from django.middleware.csrf import get_token
from django.views.decorators.csrf import csrf_protect
from django.views.decorators.http import require_GET, require_POST


def json_error(message, status=400):
    return JsonResponse(
        {"success": False, "message": message},
        status=status,
    )


@require_GET
def csrf_token_view(request):
    """
    Provide a CSRF token for the React administration portal.
    """
    return JsonResponse({
        "success": True,
        "csrfToken": get_token(request),
    })


@csrf_protect
@require_POST
def admin_login_view(request):
    """
    Only active Django staff accounts may enter the
    administration portal. Public admin registration is not allowed.
    """
    try:
        data = json.loads(request.body or b"{}")
    except (json.JSONDecodeError, UnicodeDecodeError):
        return json_error("Invalid JSON request.")

    username = str(data.get("username", "")).strip()
    password = data.get("password", "")

    if not username or not isinstance(password, str) or not password:
        return json_error("Username and password are required.")

    user = authenticate(
        request,
        username=username,
        password=password,
    )

    if user is None or not user.is_active or not user.is_staff:
        return json_error(
            "Invalid credentials or no administration access.",
            status=401,
        )

    login(request, user)

    return JsonResponse({
        "success": True,
        "message": "Login successful.",
        "user": {
            "id": user.id,
            "username": user.get_username(),
            "email": user.email,
            "is_owner": user.is_superuser,
        },
    })


@require_GET
def admin_me_view(request):
    """
    Return the current authenticated administrator.
    """
    user = request.user

    if not user.is_authenticated or not user.is_active or not user.is_staff:
        return json_error("Authentication required.", status=401)

    return JsonResponse({
        "success": True,
        "user": {
            "id": user.id,
            "username": user.get_username(),
            "email": user.email,
            "is_owner": user.is_superuser,
        },
    })


@csrf_protect
@require_POST
def admin_logout_view(request):
    """
    Log out the current Django session.
    """
    if not request.user.is_authenticated:
        return json_error("You are not logged in.", status=401)

    logout(request)

    return JsonResponse({
        "success": True,
        "message": "Logout successful.",
    })

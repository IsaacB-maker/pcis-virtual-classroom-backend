
from django.urls import path

from .views import (
    admin_login_view,
    admin_logout_view,
    admin_me_view,
    csrf_token_view,
)

from .account_views import (
    administrator_list_view,
    administrator_create_view,
    administrator_permissions_view,
    administrator_deactivate_view,
)

from .data_views import (
    data_collection_view,
    data_detail_view,
)

urlpatterns = [
    # Administration login and session
    path("csrf/", csrf_token_view, name="administration-csrf"),
    path("login/", admin_login_view, name="administration-login"),
    path("me/", admin_me_view, name="administration-me"),
    path("logout/", admin_logout_view, name="administration-logout"),

    # Owner-only administrator management
    path(
        "accounts/",
        administrator_list_view,
        name="administrator-list",
    ),
    path(
        "accounts/create/",
        administrator_create_view,
        name="administrator-create",
    ),
    path(
        "accounts/<int:user_id>/permissions/",
        administrator_permissions_view,
        name="administrator-permissions",
    ),
    path(
        "accounts/<int:user_id>/deactivate/",
        administrator_deactivate_view,
        name="administrator-deactivate",
    ),

    # Protected school-data management API
    path(
        "data/<str:resource>/",
        data_collection_view,
        name="administration-data-list",
    ),
    path(
        "data/<str:resource>/<int:object_id>/",
        data_detail_view,
        name="administration-data-detail",
    ),
]

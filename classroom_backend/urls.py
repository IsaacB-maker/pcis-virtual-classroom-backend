
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path


urlpatterns = [
    path("admin/", admin.site.urls),

    # Existing classroom and teacher API
    path("api/", include("classroom.urls")),

    # Existing recordings API
    path("api/", include("liveclass.urls")),

    # Existing student API
    path("api/students/", include("student_management.urls")),

    # New administration API
    path("api/administration/", include("administration.urls")),
]


if settings.DEBUG:
    urlpatterns += static(
        settings.MEDIA_URL,
        document_root=settings.MEDIA_ROOT,
    )

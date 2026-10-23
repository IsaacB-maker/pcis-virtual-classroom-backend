from django.urls import re_path

from .consumers import ClassroomConsumer


websocket_urlpatterns = [
    re_path(
        r"ws/classroom/(?P<room_id>[0-9a-fA-F-]+)/$",
        ClassroomConsumer.as_asgi(),
    ),
]
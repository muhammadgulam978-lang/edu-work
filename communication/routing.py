from django.urls import re_path

from .consumers import CommunicationConsumer


websocket_urlpatterns = [
    re_path(
        r"^ws/communication/(?P<conversation_id>\d+)/$",
        CommunicationConsumer.as_asgi(),
    ),
]

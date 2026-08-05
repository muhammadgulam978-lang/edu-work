"""
ASGI config for sms project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/5.2/howto/deployment/asgi/
"""

import os

from channels.auth import AuthMiddlewareStack
from channels.routing import ProtocolTypeRouter, URLRouter
from django.core.asgi import get_asgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'sms.settings')

django_asgi_application = get_asgi_application()

from communication.routing import websocket_urlpatterns as communication_websockets
from edupilot_core.routing import websocket_urlpatterns as voucher_websockets

websocket_urlpatterns = communication_websockets + voucher_websockets

application = ProtocolTypeRouter(
    {
        "http": django_asgi_application,
        "websocket": AuthMiddlewareStack(URLRouter(websocket_urlpatterns)),
    }
)

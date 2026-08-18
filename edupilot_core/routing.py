from django.urls import re_path

from .consumers import VoucherConsumer


websocket_urlpatterns = [
    re_path(r'^ws/vouchers/$', VoucherConsumer.as_asgi()),
]

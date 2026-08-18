from django.urls import path

from . import views


app_name = "communication"

urlpatterns = [
    path("", views.inbox, name="inbox"),
    path("start/", views.start_direct, name="start_direct"),
    path("groups/create/", views.create_group, name="create_group"),
    path("conversations/updates/", views.conversation_updates, name="updates"),
    path(
        "conversations/<int:conversation_id>/send/",
        views.send_message,
        name="send_message",
    ),
    path(
        "conversations/<int:conversation_id>/poll/",
        views.poll,
        name="poll",
    ),
    path(
        "conversations/<int:conversation_id>/setting/",
        views.conversation_setting,
        name="conversation_setting",
    ),
    path("messages/<int:message_id>/action/", views.message_action, name="message_action"),
    path("presence/", views.heartbeat, name="heartbeat"),
]

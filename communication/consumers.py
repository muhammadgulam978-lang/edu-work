import json

from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer
from django.utils import timezone

from .models import Conversation, UserPresence
from .services import CommunicationService, display_name


class CommunicationConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.user = self.scope["user"]
        self.conversation_id = self.scope["url_route"]["kwargs"]["conversation_id"]
        if not self.user.is_authenticated or not await self._is_member():
            await self.close(code=4403)
            return

        self.conversation_group = (
            f"communication_conversation_{self.conversation_id}"
        )
        self.user_group = f"communication_user_{self.user.pk}"
        await self.channel_layer.group_add(
            self.conversation_group, self.channel_name
        )
        await self.channel_layer.group_add(self.user_group, self.channel_name)
        await self.accept()
        await self._set_presence(True)
        await self._mark_delivered()
        name = await self._display_name()
        await self.channel_layer.group_send(
            self.conversation_group,
            {
                "type": "communication.presence",
                "user_id": self.user.pk,
                "name": name,
                "online": True,
            },
        )

    async def disconnect(self, close_code):
        if not getattr(self, "user", None) or not self.user.is_authenticated:
            return
        await self._set_presence(False)
        if hasattr(self, "conversation_group"):
            name = await self._display_name()
            await self.channel_layer.group_send(
                self.conversation_group,
                {
                    "type": "communication.presence",
                    "user_id": self.user.pk,
                    "name": name,
                    "online": False,
                },
            )
            await self.channel_layer.group_discard(
                self.conversation_group, self.channel_name
            )
        if hasattr(self, "user_group"):
            await self.channel_layer.group_discard(self.user_group, self.channel_name)

    async def receive(self, text_data=None, bytes_data=None):
        try:
            payload = json.loads(text_data or "{}")
        except json.JSONDecodeError:
            return
        event_type = payload.get("type")
        if event_type == "typing":
            name = await self._display_name()
            await self.channel_layer.group_send(
                self.conversation_group,
                {
                    "type": "communication.typing",
                    "user_id": self.user.pk,
                    "name": name,
                    "typing": bool(payload.get("typing")),
                },
            )
        elif event_type == "read":
            await self._mark_read()

    async def communication_message(self, event):
        await self.send(
            text_data=json.dumps(
                {
                    "type": "message",
                    "message_id": event["message_id"],
                    "sender_id": event["sender_id"],
                }
            )
        )

    async def communication_inbox(self, event):
        await self.send(
            text_data=json.dumps(
                {
                    "type": "inbox",
                    "conversation_id": event["conversation_id"],
                }
            )
        )

    async def communication_typing(self, event):
        if event["user_id"] != self.user.pk:
            await self.send(text_data=json.dumps({**event, "type": "typing"}))

    async def communication_receipt(self, event):
        await self.send(text_data=json.dumps({**event, "type": "receipt"}))

    async def communication_presence(self, event):
        if event["user_id"] != self.user.pk:
            await self.send(text_data=json.dumps({**event, "type": "presence"}))

    @database_sync_to_async
    def _is_member(self):
        return Conversation.objects.filter(
            pk=self.conversation_id,
            memberships__user=self.user,
            is_archived=False,
        ).exists()

    @database_sync_to_async
    def _set_presence(self, online):
        UserPresence.objects.update_or_create(
            user=self.user,
            defaults={"is_online": online, "last_seen": timezone.now()},
        )

    @database_sync_to_async
    def _display_name(self):
        return display_name(self.user)

    @database_sync_to_async
    def _mark_delivered(self):
        conversation = Conversation.objects.get(pk=self.conversation_id)
        CommunicationService.mark_delivered(conversation, self.user)

    @database_sync_to_async
    def _mark_read(self):
        conversation = Conversation.objects.get(pk=self.conversation_id)
        CommunicationService.mark_read(conversation, self.user)

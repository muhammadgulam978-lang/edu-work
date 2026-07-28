from django.conf import settings
from django.db import models
from django.utils import timezone


class Conversation(models.Model):
    GROUP_TYPES = [
        ("DIRECT", "Direct"),
        ("CLASS", "Class"),
        ("DEPARTMENT", "Department"),
        ("CLUB", "Club"),
        ("COMMITTEE", "Committee"),
        ("BROADCAST", "Broadcast"),
    ]

    name = models.CharField(max_length=200, blank=True)
    description = models.TextField(blank=True)
    is_group = models.BooleanField(default=False)
    group_type = models.CharField(max_length=20, choices=GROUP_TYPES, default="DIRECT")
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="created_communication_conversations",
    )
    class_fk = models.ForeignKey(
        "admin_panel.Class",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="communication_conversations",
    )
    allow_all_members_post = models.BooleanField(default=True)
    is_archived = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    last_message_at = models.DateTimeField(null=True, blank=True, db_index=True)

    class Meta:
        ordering = ["-last_message_at", "-created_at"]

    def __str__(self):
        return self.name or f"Conversation {self.pk}"


class ConversationParticipant(models.Model):
    conversation = models.ForeignKey(
        Conversation, on_delete=models.CASCADE, related_name="memberships"
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="communication_memberships",
    )
    is_admin = models.BooleanField(default=False)
    is_muted = models.BooleanField(default=False)
    is_archived = models.BooleanField(default=False)
    joined_at = models.DateTimeField(auto_now_add=True)
    last_read_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["conversation", "user"], name="unique_conversation_member"
            )
        ]

class Message(models.Model):
    STATUSES = [
        ("SENT", "Sent"),
        ("DELIVERED", "Delivered"),
        ("READ", "Read"),
        ("FAILED", "Failed"),
    ]

    conversation = models.ForeignKey(
        Conversation, on_delete=models.CASCADE, related_name="messages"
    )
    sender = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="communication_messages",
    )
    content = models.TextField(blank=True)
    attachment = models.FileField(
        upload_to="communication/%Y/%m/", null=True, blank=True
    )
    delivery_status = models.CharField(
        max_length=12, choices=STATUSES, default="SENT", db_index=True
    )
    is_pinned = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    edited_at = models.DateTimeField(null=True, blank=True)
    deleted_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["created_at"]

    @property
    def is_deleted(self):
        return self.deleted_at is not None


class MessageReceipt(models.Model):
    STATUSES = [("DELIVERED", "Delivered"), ("READ", "Read")]

    message = models.ForeignKey(
        Message, on_delete=models.CASCADE, related_name="receipts"
    )
    reader = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="communication_receipts",
    )
    status = models.CharField(max_length=12, choices=STATUSES, default="DELIVERED")
    delivered_at = models.DateTimeField(default=timezone.now)
    read_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["message", "reader"], name="unique_message_reader"
            )
        ]


class MessageReaction(models.Model):
    message = models.ForeignKey(
        Message, on_delete=models.CASCADE, related_name="reactions"
    )
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    emoji = models.CharField(max_length=24)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["message", "user", "emoji"], name="unique_message_reaction"
            )
        ]


class CommunicationNotification(models.Model):
    TYPES = [
        ("NEW_MESSAGE", "New message"),
        ("MESSAGE_READ", "Message read"),
        ("GROUP_ADDED", "Added to group"),
        ("MENTION", "Mention"),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="communication_notifications",
    )
    from_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="sent_communication_notifications",
    )
    message = models.ForeignKey(
        Message,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="notifications",
    )
    conversation = models.ForeignKey(
        Conversation,
        on_delete=models.CASCADE,
        related_name="notifications",
    )
    notification_type = models.CharField(
        max_length=24, choices=TYPES, default="NEW_MESSAGE"
    )
    is_read = models.BooleanField(default=False, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)


class UserPresence(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="communication_presence",
    )
    is_online = models.BooleanField(default=False)
    last_seen = models.DateTimeField(default=timezone.now)


class UserBlock(models.Model):
    blocker = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="communication_blocks_created",
    )
    blocked = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="communication_blocks_received",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["blocker", "blocked"], name="unique_communication_block"
            )
        ]

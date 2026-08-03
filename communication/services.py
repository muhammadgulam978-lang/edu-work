from pathlib import Path
import re

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import IntegrityError, transaction
from django.db.models import Count
from django.utils import timezone

from .models import (
    CommunicationNotification,
    Conversation,
    ConversationParticipant,
    Message,
    MessageReceipt,
)
from .permissions import can_contact


ALLOWED_ATTACHMENT_EXTENSIONS = {
    ".pdf", ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx",
    ".png", ".jpg", ".jpeg", ".gif", ".txt", ".zip",
}
MAX_ATTACHMENT_SIZE = 10 * 1024 * 1024
MENTION_PATTERN = re.compile(r"(?<!\w)@([A-Za-z0-9_.-]+)")


def direct_key(user_a, user_b):
    first, second = sorted((user_a.pk, user_b.pk))
    return f"{first}:{second}"


def _group_send(group, event):
    channel_layer = get_channel_layer()
    if channel_layer is not None:
        async_to_sync(channel_layer.group_send)(group, event)


def display_name(user):
    for attr in ("teacher", "student", "parent"):
        profile = getattr(user, attr, None)
        if profile:
            return getattr(profile, "name", None) or getattr(
                profile, "full_name", None
            ) or user.get_full_name() or user.username
    return user.get_full_name() or user.username


class CommunicationService:
    @staticmethod
    def conversations_for(user):
        return (
            Conversation.objects.filter(
                memberships__user=user,
                memberships__is_archived=False,
                is_archived=False,
            )
            .prefetch_related("memberships__user")
            .distinct()
        )

    @staticmethod
    @transaction.atomic
    def get_or_create_direct(sender, recipient):
        if not can_contact(sender, recipient):
            raise PermissionDenied("You cannot message this user.")
        key = direct_key(sender, recipient)
        conversation = Conversation.objects.filter(direct_key=key).first()
        if conversation:
            if conversation.is_archived:
                conversation.is_archived = False
                conversation.save(update_fields=["is_archived"])
            conversation.memberships.filter(user__in=[sender, recipient]).update(
                is_archived=False
            )
            return conversation
        try:
            with transaction.atomic():
                conversation = Conversation.objects.create(
                    created_by=sender,
                    is_group=False,
                    group_type="DIRECT",
                    direct_key=key,
                )
        except IntegrityError:
            conversation = Conversation.objects.get(direct_key=key)
            conversation.memberships.filter(user__in=[sender, recipient]).update(
                is_archived=False
            )
            return conversation
        ConversationParticipant.objects.bulk_create(
            [
                ConversationParticipant(
                    conversation=conversation, user=sender, is_admin=True
                ),
                ConversationParticipant(conversation=conversation, user=recipient),
            ]
        )
        return conversation

    @staticmethod
    def _refresh_message_statuses(message_ids):
        messages = Message.objects.filter(pk__in=message_ids).prefetch_related("receipts")
        changed = []
        for message in messages:
            statuses = [receipt.status for receipt in message.receipts.all()]
            status = "SENT"
            if statuses and all(item == "READ" for item in statuses):
                status = "READ"
            elif statuses and all(item in {"DELIVERED", "READ"} for item in statuses):
                status = "DELIVERED"
            if message.delivery_status != status:
                message.delivery_status = status
                changed.append(message)
        if changed:
            Message.objects.bulk_update(changed, ["delivery_status"])

    @staticmethod
    @transaction.atomic
    def create_group(creator, name, members, group_type="CLASS", description=""):
        allowed_members = [u for u in members if u.pk == creator.pk or can_contact(creator, u)]
        if creator not in allowed_members:
            allowed_members.append(creator)
        if len(allowed_members) < 2:
            raise ValidationError("Select at least one permitted recipient.")
        conversation = Conversation.objects.create(
            name=name.strip(),
            description=description.strip(),
            is_group=True,
            group_type=group_type,
            created_by=creator,
        )
        ConversationParticipant.objects.bulk_create(
            [
                ConversationParticipant(
                    conversation=conversation,
                    user=member,
                    is_admin=member.pk == creator.pk,
                )
                for member in allowed_members
            ]
        )
        return conversation

    @staticmethod
    def validate_attachment(attachment):
        if not attachment:
            return
        if attachment.size > MAX_ATTACHMENT_SIZE:
            raise ValidationError("Attachment must be 10 MB or smaller.")
        if Path(attachment.name).suffix.lower() not in ALLOWED_ATTACHMENT_EXTENSIONS:
            raise ValidationError("This attachment type is not allowed.")

    @staticmethod
    @transaction.atomic
    def send_message(
        conversation,
        sender,
        content="",
        attachment=None,
        reply_to=None,
        forwarded_from=None,
    ):
        membership = ConversationParticipant.objects.filter(
            conversation=conversation, user=sender
        ).first()
        if not membership:
            raise PermissionDenied("You are not a member of this conversation.")
        if (
            conversation.is_group
            and not conversation.allow_all_members_post
            and not membership.is_admin
        ):
            raise PermissionDenied("Only group administrators can post here.")
        content = content.strip()
        CommunicationService.validate_attachment(attachment)
        if reply_to and reply_to.conversation_id != conversation.pk:
            raise ValidationError("The replied message belongs to another conversation.")
        if forwarded_from and not ConversationParticipant.objects.filter(
            conversation=forwarded_from.conversation, user=sender
        ).exists():
            raise PermissionDenied("You cannot forward this message.")
        if forwarded_from and not content:
            content = forwarded_from.content
        if forwarded_from and not attachment and forwarded_from.attachment:
            attachment = forwarded_from.attachment.name
        if not content and not attachment:
            raise ValidationError("Write a message or attach a file.")
        message = Message.objects.create(
            conversation=conversation,
            sender=sender,
            content=content,
            attachment=attachment,
            delivery_status="SENT",
            reply_to=reply_to,
            forwarded_from=forwarded_from,
        )
        now = timezone.now()
        conversation.last_message_at = now
        conversation.save(update_fields=["last_message_at"])
        recipients = list(
            conversation.memberships.exclude(user=sender).values_list("user_id", flat=True)
        )
        MessageReceipt.objects.bulk_create(
            [
                MessageReceipt(message=message, reader_id=user_id)
                for user_id in recipients
            ]
        )
        mentioned_ids = set(
            conversation.memberships.filter(
                user__username__in=MENTION_PATTERN.findall(content)
            )
            .exclude(user=sender)
            .values_list("user_id", flat=True)
        )
        CommunicationNotification.objects.bulk_create(
            [
                CommunicationNotification(
                    user_id=user_id,
                    from_user=sender,
                    message=message,
                    conversation=conversation,
                    notification_type=(
                        "MENTION" if user_id in mentioned_ids else "NEW_MESSAGE"
                    ),
                )
                for user_id in recipients
            ]
        )
        transaction.on_commit(
            lambda: (
                _group_send(
                    f"communication_conversation_{conversation.pk}",
                    {
                        "type": "communication.message",
                        "message_id": message.pk,
                        "sender_id": sender.pk,
                    },
                ),
                [
                    _group_send(
                        f"communication_user_{user_id}",
                        {
                            "type": "communication.inbox",
                            "conversation_id": conversation.pk,
                        },
                    )
                    for user_id in recipients
                ],
            )
        )
        return message

    @staticmethod
    @transaction.atomic
    def mark_delivered(conversation, user):
        now = timezone.now()
        receipts = MessageReceipt.objects.filter(
            message__conversation=conversation,
            reader=user,
            status="SENT",
        )
        message_ids = list(receipts.values_list("message_id", flat=True))
        receipts.update(status="DELIVERED", delivered_at=now)
        CommunicationService._refresh_message_statuses(message_ids)
        if message_ids:
            transaction.on_commit(
                lambda: _group_send(
                    f"communication_conversation_{conversation.pk}",
                    {
                        "type": "communication.receipt",
                        "message_ids": message_ids,
                        "status": "DELIVERED",
                        "timestamp": now.isoformat(),
                    },
                )
            )
        return now

    @staticmethod
    @transaction.atomic
    def mark_read(conversation, user):
        membership = ConversationParticipant.objects.filter(
            conversation=conversation, user=user
        ).first()
        if not membership:
            raise PermissionDenied
        now = timezone.now()
        CommunicationService.mark_delivered(conversation, user)
        membership.last_read_at = now
        membership.save(update_fields=["last_read_at"])
        receipts = MessageReceipt.objects.filter(
            message__conversation=conversation,
            reader=user,
            read_at__isnull=True,
        )
        message_ids = list(receipts.values_list("message_id", flat=True))
        receipts.update(status="READ", read_at=now)
        CommunicationService._refresh_message_statuses(message_ids)
        CommunicationNotification.objects.filter(
            conversation=conversation, user=user, is_read=False
        ).update(is_read=True)
        if message_ids:
            transaction.on_commit(
                lambda: _group_send(
                    f"communication_conversation_{conversation.pk}",
                    {
                        "type": "communication.receipt",
                        "message_ids": message_ids,
                        "status": "READ",
                        "timestamp": now.isoformat(),
                    },
                )
            )
        return now

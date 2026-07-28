from pathlib import Path

from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
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
        conversation = (
            Conversation.objects.filter(
                is_group=False,
                memberships__user=sender,
            )
            .filter(memberships__user=recipient)
            .annotate(member_count=Count("memberships"))
            .filter(member_count=2)
            .first()
        )
        if conversation:
            return conversation
        conversation = Conversation.objects.create(
            created_by=sender, is_group=False, group_type="DIRECT"
        )
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
    def send_message(conversation, sender, content="", attachment=None):
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
        if not content and not attachment:
            raise ValidationError("Write a message or attach a file.")
        CommunicationService.validate_attachment(attachment)
        message = Message.objects.create(
            conversation=conversation,
            sender=sender,
            content=content,
            attachment=attachment,
            delivery_status="DELIVERED",
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
        CommunicationNotification.objects.bulk_create(
            [
                CommunicationNotification(
                    user_id=user_id,
                    from_user=sender,
                    message=message,
                    conversation=conversation,
                )
                for user_id in recipients
            ]
        )
        return message

    @staticmethod
    @transaction.atomic
    def mark_read(conversation, user):
        membership = ConversationParticipant.objects.filter(
            conversation=conversation, user=user
        ).first()
        if not membership:
            raise PermissionDenied
        now = timezone.now()
        membership.last_read_at = now
        membership.save(update_fields=["last_read_at"])
        MessageReceipt.objects.filter(
            message__conversation=conversation,
            reader=user,
            read_at__isnull=True,
        ).update(status="READ", read_at=now)
        CommunicationNotification.objects.filter(
            conversation=conversation, user=user, is_read=False
        ).update(is_read=True)
        return now

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied, ValidationError
from django.db.models import Count, Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_GET, require_POST
from django.views.decorators.csrf import ensure_csrf_cookie

from .models import (
    Conversation,
    ConversationParticipant,
    Message,
    MessageReaction,
    UserBlock,
    UserPresence,
)
from .permissions import contactable_users, user_role
from .services import CommunicationService, display_name


User = get_user_model()

PORTAL_CONFIG = {
    "admin": ("admin_panel/bases.html", "Admin Communication"),
    "teacher": ("teacher_dashboard/bases.html", "Teacher Communication"),
    "student": ("student_profile/bases.html", "Student Messages"),
    "parent": ("parent_dashboard/base.html", "Parent Communication"),
}


def _config(user):
    role = user_role(user)
    return role, *PORTAL_CONFIG.get(role, PORTAL_CONFIG["student"])


def _member_conversation(user, conversation_id):
    return get_object_or_404(
        Conversation.objects.prefetch_related("memberships__user"),
        pk=conversation_id,
        memberships__user=user,
        is_archived=False,
    )


def _conversation_label(conversation, user):
    if conversation.is_group:
        return conversation.name
    other = next(
        (
            membership.user
            for membership in conversation.memberships.all()
            if membership.user_id != user.pk
        ),
        None,
    )
    return display_name(other) if other else "Conversation"


def _contact_payload(contact):
    role = user_role(contact)
    values = [
        str(contact.pk),
        contact.username,
        contact.get_full_name(),
        contact.email,
        display_name(contact),
        role,
    ]
    details = []

    student = getattr(contact, "student", None)
    if student:
        class_name = (
            getattr(student.class_fk, "class_name", "") if student.class_fk else ""
        )
        section_name = str(student.section) if student.section else ""
        parent_names = list(student.parents.values_list("full_name", flat=True))
        values.extend(
            [
                student.student_id,
                student.name,
                student.email,
                student.phone,
                student.roll_no,
                student.father_name,
                student.mother_name,
                class_name,
                section_name,
                *parent_names,
            ]
        )
        details = [student.student_id, class_name, section_name]

    teacher = getattr(contact, "teacher", None)
    if teacher:
        employee = getattr(teacher, "employee", None)
        values.extend(
            [
                teacher.name,
                teacher.email,
                teacher.phone,
                teacher.department,
                getattr(employee, "employee_id", "") if employee else "",
            ]
        )
        details = [teacher.department, teacher.email]

    parent = getattr(contact, "parent", None)
    if parent:
        children = list(
            parent.students.select_related("class_fk").values_list(
                "student_id", "name", "class_fk__class_name"
            )
        )
        values.extend([parent.full_name, parent.email, parent.phone])
        for student_id, name, class_name in children:
            values.extend([student_id, name, class_name])
        details = [parent.email, ", ".join(child[1] for child in children)]

    return {
        "id": contact.pk,
        "name": display_name(contact),
        "role": role,
        "detail": " | ".join(str(value) for value in details if value),
        "search": " ".join(str(value) for value in values if value).lower(),
    }


def _conversation_payload(conversation, user):
    membership = next(
        (
            item
            for item in conversation.memberships.all()
            if item.user_id == user.pk
        ),
        None,
    )
    last_read = membership.last_read_at if membership else None
    unread = conversation.messages.exclude(sender=user)
    if last_read:
        unread = unread.filter(created_at__gt=last_read)
    last_message = conversation.messages.select_related("sender").last()
    return {
        "id": conversation.pk,
        "name": _conversation_label(conversation, user),
        "is_group": conversation.is_group,
        "group_type": conversation.group_type,
        "last_message": (
            "Attachment"
            if last_message and last_message.attachment and not last_message.content
            else (last_message.content[:80] if last_message else "No messages yet")
        ),
        "last_message_at": (
            last_message.created_at.isoformat() if last_message else None
        ),
        "unread": unread.count(),
        "muted": bool(membership and membership.is_muted),
    }


def _message_payload(message, viewer):
    reactions = {}
    for reaction in message.reactions.all():
        reactions.setdefault(reaction.emoji, 0)
        reactions[reaction.emoji] += 1
    return {
        "id": message.pk,
        "sender_id": message.sender_id,
        "sender": display_name(message.sender),
        "mine": message.sender_id == viewer.pk,
        "content": "Message deleted" if message.deleted_at else message.content,
        "attachment_url": (
            message.attachment.url if message.attachment and not message.deleted_at else ""
        ),
        "attachment_name": (
            message.attachment.name.rsplit("/", 1)[-1]
            if message.attachment and not message.deleted_at
            else ""
        ),
        "status": message.delivery_status,
        "created_at": message.created_at.isoformat(),
        "edited": bool(message.edited_at),
        "pinned": message.is_pinned,
        "deleted": bool(message.deleted_at),
        "reactions": reactions,
    }


@login_required
@ensure_csrf_cookie
def inbox(request):
    role, base_template, page_title = _config(request.user)
    memberships = (
        ConversationParticipant.objects.filter(
            user=request.user,
            is_archived=False,
            conversation__is_archived=False,
        )
        .select_related("conversation")
        .order_by("-conversation__last_message_at", "-conversation__created_at")
    )
    conversations = [
        membership.conversation
        for membership in memberships
    ]
    conversation_ids = [item.pk for item in conversations]
    hydrated = {
        item.pk: item
        for item in Conversation.objects.filter(pk__in=conversation_ids).prefetch_related(
            "memberships__user"
        )
    }
    conversations = [hydrated[item.pk] for item in conversations if item.pk in hydrated]
    active_id = request.GET.get("conversation")
    active = next(
        (item for item in conversations if str(item.pk) == str(active_id)),
        conversations[0] if conversations else None,
    )
    if active:
        CommunicationService.mark_read(active, request.user)
    today = timezone.localdate()
    user_messages = Message.objects.filter(conversation_id__in=conversation_ids)
    delivered = user_messages.exclude(delivery_status="FAILED")
    stats = {
        "messages_today": user_messages.filter(created_at__date=today).count(),
        "active_conversations": len(conversations),
        "groups": sum(1 for item in conversations if item.is_group),
        "delivery_rate": round(
            (delivered.count() / user_messages.count()) * 100
            if user_messages.exists()
            else 100
        ),
    }
    contacts = contactable_users(request.user)
    if not hasattr(contacts, "order_by"):
        contacts = sorted(contacts, key=display_name)
    else:
        contacts = contacts.order_by("first_name", "username")
    context = {
        "base_template": base_template,
        "portal_role": role,
        "page_title": page_title,
        "stats": stats,
        "conversations": [
            _conversation_payload(item, request.user) for item in conversations
        ],
        "active_conversation": active,
        "active_name": _conversation_label(active, request.user) if active else "",
        "initial_messages": (
            [
                _message_payload(item, request.user)
                for item in active.messages.select_related("sender").prefetch_related(
                    "reactions"
                )[:150]
            ]
            if active
            else []
        ),
        "contacts": [_contact_payload(contact) for contact in contacts],
        "can_create_group": role in {"admin", "teacher"},
    }
    return render(request, "communication/inbox.html", context)


@login_required
@require_POST
def start_direct(request):
    recipient = get_object_or_404(User, pk=request.POST.get("recipient_id"), is_active=True)
    try:
        conversation = CommunicationService.get_or_create_direct(
            request.user, recipient
        )
        content = request.POST.get("content", "").strip()
        if content:
            CommunicationService.send_message(conversation, request.user, content)
    except (PermissionDenied, ValidationError) as exc:
        messages.error(request, str(exc))
        return redirect("communication:inbox")
    return redirect(f"{request.build_absolute_uri('/communication/')}?conversation={conversation.pk}")


@login_required
@require_POST
def create_group(request):
    if user_role(request.user) not in {"admin", "teacher"}:
        raise PermissionDenied
    member_ids = request.POST.getlist("members")
    members = list(User.objects.filter(pk__in=member_ids, is_active=True))
    try:
        conversation = CommunicationService.create_group(
            request.user,
            request.POST.get("name", ""),
            members,
            request.POST.get("group_type", "CLASS"),
            request.POST.get("description", ""),
        )
    except ValidationError as exc:
        messages.error(request, "; ".join(exc.messages))
        return redirect("communication:inbox")
    return redirect(f"{request.build_absolute_uri('/communication/')}?conversation={conversation.pk}")


@login_required
@require_POST
def send_message(request, conversation_id):
    conversation = _member_conversation(request.user, conversation_id)
    try:
        message = CommunicationService.send_message(
            conversation,
            request.user,
            request.POST.get("content", ""),
            request.FILES.get("attachment"),
        )
    except (PermissionDenied, ValidationError) as exc:
        detail = exc.messages[0] if isinstance(exc, ValidationError) else str(exc)
        return JsonResponse({"ok": False, "error": detail}, status=400)
    return JsonResponse({"ok": True, "message": _message_payload(message, request.user)})


@login_required
@require_GET
def poll(request, conversation_id):
    conversation = _member_conversation(request.user, conversation_id)
    after_id = request.GET.get("after", 0)
    try:
        after_id = int(after_id)
    except (TypeError, ValueError):
        after_id = 0
    CommunicationService.mark_read(conversation, request.user)
    messages_qs = (
        conversation.messages.filter(pk__gt=after_id)
        .select_related("sender")
        .prefetch_related("reactions")
    )
    presence = {
        item.user_id: {
            "online": item.is_online,
            "last_seen": item.last_seen.isoformat(),
        }
        for item in UserPresence.objects.filter(
            user_id__in=conversation.memberships.values_list("user_id", flat=True)
        )
    }
    return JsonResponse(
        {
            "ok": True,
            "messages": [_message_payload(item, request.user) for item in messages_qs],
            "presence": presence,
        }
    )


@login_required
@require_GET
def conversation_updates(request):
    conversations = Conversation.objects.filter(
        memberships__user=request.user,
        memberships__is_archived=False,
        is_archived=False,
    ).prefetch_related("memberships__user")
    return JsonResponse(
        {
            "ok": True,
            "conversations": [
                _conversation_payload(item, request.user) for item in conversations
            ],
        }
    )


@login_required
@require_POST
def message_action(request, message_id):
    message = get_object_or_404(
        Message.objects.select_related("conversation"),
        pk=message_id,
        conversation__memberships__user=request.user,
    )
    action = request.POST.get("action")
    membership = ConversationParticipant.objects.get(
        conversation=message.conversation, user=request.user
    )
    if action == "delete" and message.sender_id == request.user.pk:
        message.deleted_at = timezone.now()
        message.content = ""
        message.save(update_fields=["deleted_at", "content"])
    elif action == "pin" and (membership.is_admin or message.sender_id == request.user.pk):
        message.is_pinned = not message.is_pinned
        message.save(update_fields=["is_pinned"])
    elif action == "edit" and message.sender_id == request.user.pk and not message.deleted_at:
        content = request.POST.get("content", "").strip()
        if content:
            message.content = content
            message.edited_at = timezone.now()
            message.save(update_fields=["content", "edited_at"])
    elif action == "react" and not message.deleted_at:
        emoji = request.POST.get("emoji", "")[:24]
        if emoji:
            reaction, created = MessageReaction.objects.get_or_create(
                message=message, user=request.user, emoji=emoji
            )
            if not created:
                reaction.delete()
    else:
        return JsonResponse({"ok": False, "error": "Action not permitted."}, status=403)
    message.refresh_from_db()
    return JsonResponse({"ok": True, "message": _message_payload(message, request.user)})


@login_required
@require_POST
def conversation_setting(request, conversation_id):
    membership = get_object_or_404(
        ConversationParticipant, conversation_id=conversation_id, user=request.user
    )
    action = request.POST.get("action")
    if action == "mute":
        membership.is_muted = not membership.is_muted
        membership.save(update_fields=["is_muted"])
    elif action == "archive":
        membership.is_archived = True
        membership.save(update_fields=["is_archived"])
    elif action == "block" and not membership.conversation.is_group:
        other = membership.conversation.memberships.exclude(user=request.user).first()
        if other:
            UserBlock.objects.get_or_create(blocker=request.user, blocked=other.user)
    else:
        return JsonResponse({"ok": False}, status=400)
    return JsonResponse({"ok": True})


@login_required
@require_POST
def heartbeat(request):
    presence, _ = UserPresence.objects.get_or_create(user=request.user)
    presence.is_online = request.POST.get("online", "true") == "true"
    presence.last_seen = timezone.now()
    presence.save(update_fields=["is_online", "last_seen"])
    return JsonResponse({"ok": True})

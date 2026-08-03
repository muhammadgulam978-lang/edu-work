from django.db import migrations, models
import django.db.models.deletion


def merge_direct_conversations(apps, schema_editor):
    Conversation = apps.get_model("communication", "Conversation")
    Participant = apps.get_model("communication", "ConversationParticipant")
    Message = apps.get_model("communication", "Message")
    Notification = apps.get_model("communication", "CommunicationNotification")

    pairs = {}
    direct_ids = Conversation.objects.filter(is_group=False).values_list("id", flat=True)
    for conversation_id in direct_ids.iterator():
        user_ids = sorted(
            set(
                Participant.objects.filter(conversation_id=conversation_id)
                .values_list("user_id", flat=True)
            )
        )
        if len(user_ids) != 2:
            continue
        pairs.setdefault(tuple(user_ids), []).append(conversation_id)

    for pair, conversation_ids in pairs.items():
        ordered_ids = list(
            Conversation.objects.filter(id__in=conversation_ids)
            .order_by("created_at", "id")
            .values_list("id", flat=True)
        )
        canonical_id = ordered_ids[0]
        duplicate_ids = ordered_ids[1:]
        direct_key = f"{pair[0]}:{pair[1]}"

        if duplicate_ids:
            Message.objects.filter(conversation_id__in=duplicate_ids).update(
                conversation_id=canonical_id
            )
            Notification.objects.filter(conversation_id__in=duplicate_ids).update(
                conversation_id=canonical_id
            )

            for user_id in pair:
                memberships = list(
                    Participant.objects.filter(
                        conversation_id__in=ordered_ids, user_id=user_id
                    ).order_by("joined_at", "id")
                )
                canonical_membership = next(
                    (
                        membership
                        for membership in memberships
                        if membership.conversation_id == canonical_id
                    ),
                    None,
                )
                if canonical_membership is None:
                    canonical_membership = memberships[0]
                    canonical_membership.conversation_id = canonical_id

                read_values = [
                    membership.last_read_at
                    for membership in memberships
                    if membership.last_read_at is not None
                ]
                canonical_membership.last_read_at = max(read_values) if read_values else None
                canonical_membership.is_admin = any(
                    membership.is_admin for membership in memberships
                )
                canonical_membership.is_muted = any(
                    membership.is_muted for membership in memberships
                )
                canonical_membership.is_archived = all(
                    membership.is_archived for membership in memberships
                )
                canonical_membership.save()
                Participant.objects.filter(
                    conversation_id__in=duplicate_ids, user_id=user_id
                ).delete()

            Conversation.objects.filter(id__in=duplicate_ids).delete()

        latest = (
            Message.objects.filter(conversation_id=canonical_id)
            .order_by("-created_at", "-id")
            .values_list("created_at", flat=True)
            .first()
        )
        Conversation.objects.filter(id=canonical_id).update(
            direct_key=direct_key,
            group_type="DIRECT",
            last_message_at=latest,
        )


class Migration(migrations.Migration):
    atomic = False

    dependencies = [
        ("communication", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="conversation",
            name="direct_key",
            field=models.CharField(blank=True, max_length=64, null=True),
        ),
        migrations.AddField(
            model_name="message",
            name="forwarded_from",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="forwards",
                to="communication.message",
            ),
        ),
        migrations.AddField(
            model_name="message",
            name="reply_to",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="replies",
                to="communication.message",
            ),
        ),
        migrations.AlterField(
            model_name="messagereceipt",
            name="delivered_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name="messagereceipt",
            name="status",
            field=models.CharField(
                choices=[
                    ("SENT", "Sent"),
                    ("DELIVERED", "Delivered"),
                    ("READ", "Read"),
                ],
                default="SENT",
                max_length=12,
            ),
        ),
        migrations.RunPython(merge_direct_conversations, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="conversation",
            name="direct_key",
            field=models.CharField(
                blank=True,
                db_index=True,
                max_length=64,
                null=True,
                unique=True,
            ),
        ),
    ]

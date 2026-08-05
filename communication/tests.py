from datetime import date

from asgiref.sync import async_to_sync
from channels.testing import WebsocketCommunicator
from django.contrib.auth.models import User
from django.core.exceptions import PermissionDenied
from django.test import TestCase, TransactionTestCase
from django.urls import reverse

from parent_dashboard.models import Parent
from student_profile.models import Student

from .models import (
    CommunicationNotification,
    Conversation,
    ConversationParticipant,
    MessageReceipt,
)
from .permissions import can_contact
from .services import CommunicationService
from .consumers import CommunicationConsumer


class CommunicationServiceTests(TestCase):
    def setUp(self):
        User.objects.bulk_create(
            [
                User(username="comm-admin", is_staff=True),
                User(username="comm-student"),
                User(username="comm-student-2"),
                User(username="comm-parent"),
            ]
        )
        self.admin = User.objects.get(username="comm-admin")
        self.student_user = User.objects.get(username="comm-student")
        self.other_student_user = User.objects.get(username="comm-student-2")
        self.parent_user = User.objects.get(username="comm-parent")
        self.student = Student.objects.create(
            user=self.student_user,
            student_id="COMM-ST-1",
            name="Communication Student",
            father_name="Parent",
            mother_name="Parent",
            roll_no="1",
            gender="Male",
            date_of_birth=date(2012, 1, 1),
            email="comm.student@example.com",
        )
        self.other_student = Student.objects.create(
            user=self.other_student_user,
            student_id="COMM-ST-2",
            name="Other Student",
            father_name="Parent",
            mother_name="Parent",
            roll_no="2",
            gender="Male",
            date_of_birth=date(2012, 1, 1),
            email="comm.student2@example.com",
        )
        self.parent = Parent.objects.create(
            user=self.parent_user,
            full_name="Communication Parent",
            email="comm.parent@example.com",
        )
        self.parent.students.add(self.student)

    def test_admin_can_start_direct_conversation_and_deliver(self):
        conversation = CommunicationService.get_or_create_direct(
            self.admin, self.student_user
        )
        message = CommunicationService.send_message(
            conversation, self.admin, "School update"
        )
        self.assertEqual(message.delivery_status, "SENT")
        receipt = MessageReceipt.objects.get(
            message=message, reader=self.student_user
        )
        self.assertEqual(receipt.status, "SENT")
        self.assertIsNone(receipt.delivered_at)
        CommunicationService.mark_delivered(conversation, self.student_user)
        message.refresh_from_db()
        receipt.refresh_from_db()
        self.assertEqual(message.delivery_status, "DELIVERED")
        self.assertEqual(receipt.status, "DELIVERED")
        self.assertIsNotNone(receipt.delivered_at)
        self.assertTrue(
            CommunicationNotification.objects.filter(
                message=message, user=self.student_user, is_read=False
            ).exists()
        )

    def test_read_updates_receipt_and_notification(self):
        conversation = CommunicationService.get_or_create_direct(
            self.admin, self.student_user
        )
        message = CommunicationService.send_message(
            conversation, self.admin, "Please read"
        )
        CommunicationService.mark_read(conversation, self.student_user)
        receipt = MessageReceipt.objects.get(
            message=message, reader=self.student_user
        )
        self.assertEqual(receipt.status, "READ")
        self.assertIsNotNone(receipt.read_at)
        self.assertFalse(
            CommunicationNotification.objects.filter(
                message=message, user=self.student_user, is_read=False
            ).exists()
        )

    def test_direct_conversation_is_reused_in_both_directions(self):
        first = CommunicationService.get_or_create_direct(
            self.admin, self.student_user
        )
        second = CommunicationService.get_or_create_direct(
            self.admin, self.student_user
        )
        reverse = CommunicationService.get_or_create_direct(
            self.student_user, self.admin
        )
        self.assertEqual(first.pk, second.pk)
        self.assertEqual(first.pk, reverse.pk)
        self.assertEqual(
            Conversation.objects.filter(direct_key=first.direct_key).count(), 1
        )

    def test_archived_direct_conversation_reopens(self):
        conversation = CommunicationService.get_or_create_direct(
            self.admin, self.student_user
        )
        ConversationParticipant.objects.filter(
            conversation=conversation, user=self.admin
        ).update(is_archived=True)
        reopened = CommunicationService.get_or_create_direct(
            self.admin, self.student_user
        )
        self.assertEqual(reopened.pk, conversation.pk)
        self.assertFalse(
            ConversationParticipant.objects.get(
                conversation=conversation, user=self.admin
            ).is_archived
        )

    def test_reply_forward_and_mention_keep_message_context(self):
        conversation = CommunicationService.get_or_create_direct(
            self.admin, self.student_user
        )
        original = CommunicationService.send_message(
            conversation, self.admin, "Original"
        )
        reply = CommunicationService.send_message(
            conversation,
            self.student_user,
            "Reply",
            reply_to=original,
        )
        forwarded = CommunicationService.send_message(
            conversation,
            self.admin,
            forwarded_from=reply,
        )
        mention = CommunicationService.send_message(
            conversation,
            self.admin,
            f"@{self.student_user.username} please review",
        )
        self.assertEqual(reply.reply_to_id, original.pk)
        self.assertEqual(forwarded.forwarded_from_id, reply.pk)
        self.assertEqual(forwarded.content, reply.content)
        self.assertTrue(
            CommunicationNotification.objects.filter(
                message=mention,
                user=self.student_user,
                notification_type="MENTION",
            ).exists()
        )

    def test_parent_can_only_contact_linked_child(self):
        self.assertTrue(can_contact(self.parent_user, self.student_user))
        self.assertFalse(can_contact(self.parent_user, self.other_student_user))
        with self.assertRaises(PermissionDenied):
            CommunicationService.get_or_create_direct(
                self.parent_user, self.other_student_user
            )

    def test_student_without_shared_class_cannot_contact_other_student(self):
        self.assertFalse(can_contact(self.student_user, self.other_student_user))


class CommunicationWebSocketTests(TransactionTestCase):
    reset_sequences = True

    def setUp(self):
        self.admin = User.objects.create_user(
            username="comm-ws-admin", is_staff=True
        )
        self.recipient = User.objects.create_user(username="comm-ws-recipient")
        self.conversation = CommunicationService.get_or_create_direct(
            self.admin, self.recipient
        )

    @staticmethod
    def app_for(user, conversation_id):
        consumer = CommunicationConsumer.as_asgi()

        async def application(scope, receive, send):
            scope["user"] = user
            scope["url_route"] = {
                "kwargs": {"conversation_id": conversation_id}
            }
            await consumer(scope, receive, send)

        return application

    def test_typing_and_presence_are_broadcast_to_other_participant(self):
        async_to_sync(self._typing_scenario)()

    async def _typing_scenario(self):
        admin_socket = WebsocketCommunicator(
            self.app_for(self.admin, self.conversation.pk),
            f"/ws/communication/{self.conversation.pk}/",
        )
        recipient_socket = WebsocketCommunicator(
            self.app_for(self.recipient, self.conversation.pk),
            f"/ws/communication/{self.conversation.pk}/",
        )
        admin_connected, _ = await admin_socket.connect()
        recipient_connected, _ = await recipient_socket.connect()
        self.assertTrue(admin_connected)
        self.assertTrue(recipient_connected)

        presence = await admin_socket.receive_json_from(timeout=1)
        self.assertEqual(presence["type"], "presence")
        self.assertTrue(presence["online"])

        await admin_socket.send_json_to({"type": "typing", "typing": True})
        typing = await recipient_socket.receive_json_from(timeout=1)
        if typing["type"] == "presence":
            typing = await recipient_socket.receive_json_from(timeout=1)
        self.assertEqual(typing["type"], "typing")
        self.assertTrue(typing["typing"])

        await recipient_socket.disconnect()
        await admin_socket.disconnect()


class CommunicationViewTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_user(
            username="comm-view-admin",
            password="test-password",
            is_staff=True,
        )
        self.recipient = User.objects.create_user(username="comm-view-recipient")
        self.client.force_login(self.admin)

    def test_inbox_renders_realtime_controls(self):
        response = self.client.get(reverse("communication:inbox"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'data-websocket-url=""')
        self.assertContains(response, "?view=unread")
        self.assertContains(response, 'id="forward-message-dialog"')

    def test_start_direct_reuses_existing_thread(self):
        url = reverse("communication:start_direct")
        first = self.client.post(url, {"recipient_id": self.recipient.pk})
        second = self.client.post(url, {"recipient_id": self.recipient.pk})
        conversation = Conversation.objects.get(
            direct_key=f"{min(self.admin.pk, self.recipient.pk)}:"
            f"{max(self.admin.pk, self.recipient.pk)}"
        )
        expected_suffix = f"?conversation={conversation.pk}"
        self.assertTrue(first.url.endswith(expected_suffix))
        self.assertTrue(second.url.endswith(expected_suffix))
        self.assertEqual(Conversation.objects.filter(is_group=False).count(), 1)

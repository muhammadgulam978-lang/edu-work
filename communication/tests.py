from datetime import date

from django.contrib.auth.models import User
from django.core.exceptions import PermissionDenied
from django.test import TestCase

from parent_dashboard.models import Parent
from student_profile.models import Student

from .models import CommunicationNotification, MessageReceipt
from .permissions import can_contact
from .services import CommunicationService


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
        self.assertEqual(message.delivery_status, "DELIVERED")
        self.assertTrue(
            MessageReceipt.objects.filter(
                message=message, reader=self.student_user
            ).exists()
        )
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

    def test_parent_can_only_contact_linked_child(self):
        self.assertTrue(can_contact(self.parent_user, self.student_user))
        self.assertFalse(can_contact(self.parent_user, self.other_student_user))
        with self.assertRaises(PermissionDenied):
            CommunicationService.get_or_create_direct(
                self.parent_user, self.other_student_user
            )

    def test_student_without_shared_class_cannot_contact_other_student(self):
        self.assertFalse(can_contact(self.student_user, self.other_student_user))

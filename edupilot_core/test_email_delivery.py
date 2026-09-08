import os
from datetime import date
from unittest.mock import patch

from django.contrib.auth.models import User
from django.test import TestCase, override_settings

from admin_panel.models import AcademicYear
from student_profile.models import Student as PortalStudent

from .email_delivery import queue_account_email, queue_voucher_email
from .models import EmailOutbox, FeeVoucher, Student as LegacyStudent


@override_settings(
    STUDENT_PORTAL_LOGIN_URL='http://student.example/login/',
    PARENT_PORTAL_LOGIN_URL='http://parent.example/login/',
    TEACHER_PORTAL_LOGIN_URL='http://teacher.example/login/',
)
class EmailDeliveryTests(TestCase):
    def test_account_email_is_idempotent_and_contains_login_details(self):
        user = User.objects.create_user(
            username='new.student', email='student@example.com', password='Secret@123'
        )

        first = queue_account_email(
            user=user, password='Secret@123', role='student', display_name='New Student'
        )
        second = queue_account_email(
            user=user, password='Secret@123', role='student', display_name='New Student'
        )

        self.assertTrue(first)
        self.assertFalse(second)
        item = EmailOutbox.objects.get()
        self.assertIn('new.student', item.body)
        self.assertIn('Secret@123', item.body)
        self.assertIn('http://student.example/login/', item.body)

    @patch('edupilot_core.email_delivery.kick_email_dispatch')
    def test_voucher_email_queues_pdf_attachment_once(self, _kick):
        year = AcademicYear.objects.create(year='2026-27', is_active=True)
        user = User.objects.create_user(username='voucher.student', email='voucher@example.com')
        student = PortalStudent.objects.create(
            user=user, academic_year=year, student_id='STU-V1', name='Voucher Student',
            father_name='Parent', mother_name='Parent', roll_no='1', gender='Male',
            date_of_birth=date(2015, 1, 1), email='voucher@example.com',
            nationality='Pakistani', address='Karachi', admission_date=date.today(),
        )
        legacy = LegacyStudent.objects.get(canonical_student=student)
        voucher = FeeVoucher.objects.create(
            student=legacy, canonical_student=student, voucher_no='V-EMAIL-1',
            month='August', year=2026, issue_date=date.today(), due_date=date.today(),
            gross_amount=1000, discount=0, net_amount=1000,
        )

        self.assertTrue(queue_voucher_email(voucher, student, user, 'STUDENT'))
        self.assertFalse(queue_voucher_email(voucher, student, user, 'STUDENT'))
        item = EmailOutbox.objects.get(dedupe_key=f'voucher:{voucher.pk}:recipient:{user.pk}')
        self.assertTrue(item.attachment_path.endswith(os.path.join('vouchers', 'voucher_V-EMAIL-1.pdf')))

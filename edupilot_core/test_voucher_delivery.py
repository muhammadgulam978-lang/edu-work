from datetime import date
from tempfile import TemporaryDirectory

from django.contrib.auth.models import User
from django.test import TestCase, override_settings
from django.urls import reverse

from admin_panel.models import AcademicYear, Class, ClassTeacher, Section
from parent_dashboard.models import Parent
from student_profile.models import Student as PortalStudent
from teacher_dashboard.models import Teacher as PortalTeacher

from .models import FeeVoucher, PortalNotification, Student, VoucherDelivery


class VoucherDeliveryTests(TestCase):
    def setUp(self):
        self.student_user = User.objects.create_user('voucher_student', password='test-pass')
        self.parent_user = User.objects.create_user('voucher_parent', password='test-pass')
        self.teacher_user = User.objects.create_user('voucher_teacher', password='test-pass')
        self.other_user = User.objects.create_user('voucher_other', password='test-pass')
        self.year = AcademicYear.objects.create(year='2026-2027', is_active=True)
        self.class_obj = Class.objects.create(class_name='Voucher Test Class')
        self.section = Section.objects.create(
            academic_year=self.year, class_fk=self.class_obj, section_name='A', capacity=40
        )
        self.student = PortalStudent.objects.create(
            user=self.student_user,
            academic_year=self.year,
            student_id='VTEST001',
            name='Voucher Test Student',
            father_name='Test Father',
            mother_name='Test Mother',
            class_fk=self.class_obj,
            section=self.section,
            roll_no='1',
            gender='Male',
            date_of_birth=date(2015, 1, 1),
            email='voucher.student@example.test',
        )
        self.parent = Parent.objects.create(user=self.parent_user, full_name='Voucher Parent')
        self.parent.students.add(self.student)
        self.teacher = PortalTeacher.objects.create(
            user=self.teacher_user,
            name='Voucher Teacher',
            email='voucher.teacher@example.test',
            gender='Male',
            faculty_group='Junior Section',
        )
        ClassTeacher.objects.create(
            academic_year=self.year,
            class_fk=self.class_obj,
            section=self.section,
            teacher=self.teacher,
        )
        self.legacy_student = Student.objects.get(canonical_student=self.student)

    def create_voucher(self):
        with self.captureOnCommitCallbacks(execute=True):
            return FeeVoucher.objects.create(
                voucher_no='VTEST-2026-01',
                student=self.legacy_student,
                canonical_student=self.student,
                month='August',
                year=2026,
                issue_date=date(2026, 8, 1),
                due_date=date(2026, 8, 10),
                gross_amount=10000,
                net_amount=10000,
            )

    def test_new_voucher_distributes_to_student_parent_and_teacher(self):
        voucher = self.create_voucher()
        deliveries = VoucherDelivery.objects.filter(voucher=voucher)
        self.assertEqual(deliveries.count(), 3)
        self.assertSetEqual(
            set(deliveries.values_list('recipient_role', flat=True)),
            {'STUDENT', 'PARENT', 'TEACHER'},
        )
        self.assertEqual(PortalNotification.objects.filter(voucher=voucher).count(), 3)

    def test_summary_and_dismiss_are_scoped_to_logged_in_recipient(self):
        self.create_voucher()
        delivery = VoucherDelivery.objects.get(recipient=self.student_user)
        self.client.force_login(self.student_user)
        response = self.client.get(reverse('student_voucher_summary'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['popup']['id'], delivery.pk)
        response = self.client.post(reverse('student_voucher_dismiss', args=[delivery.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertIsNone(self.client.get(reverse('student_voucher_summary')).json()['popup'])

        self.client.force_login(self.other_user)
        response = self.client.get(reverse('student_voucher_view', args=[delivery.pk]))
        self.assertEqual(response.status_code, 404)

    def test_voucher_history_renders_in_all_recipient_portals(self):
        self.create_voucher()
        portals = (
            (self.student_user, 'student_vouchers'),
            (self.parent_user, 'parent_vouchers'),
            (self.teacher_user, 'teacher_vouchers'),
        )
        for user, route_name in portals:
            with self.subTest(route_name=route_name):
                self.client.force_login(user)
                response = self.client.get(reverse(route_name))
                self.assertEqual(response.status_code, 200)
                self.assertContains(response, 'VTEST-2026-01')

    def test_view_and_download_track_recipient_state(self):
        self.create_voucher()
        delivery = VoucherDelivery.objects.get(recipient=self.student_user)
        self.client.force_login(self.student_user)
        with TemporaryDirectory() as media_root, override_settings(MEDIA_ROOT=media_root):
            view_response = self.client.get(reverse('student_voucher_view', args=[delivery.pk]))
            self.assertEqual(view_response.status_code, 200)
            delivery.refresh_from_db()
            self.assertIsNotNone(delivery.viewed_at)
            self.assertIsNotNone(delivery.last_viewed_at)
            for closer in view_response._resource_closers:
                closer()
            view_response._resource_closers.clear()

            download_response = self.client.get(reverse('student_voucher_download', args=[delivery.pk]))
            self.assertEqual(download_response.status_code, 200)
            delivery.refresh_from_db()
            self.assertIsNotNone(delivery.downloaded_at)
            for closer in download_response._resource_closers:
                closer()
            download_response._resource_closers.clear()

from datetime import date, timedelta

from cryptography.fernet import Fernet
from django.contrib.auth.models import User
from django.core.exceptions import PermissionDenied, ValidationError
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from access_control.models import Institution, Campus, RoleDefinition, RoleGrant, RoleAssignment, RecordScope
from student_profile.models import Student
from .models import LibraryBook, LibraryLoan, LabAsset, LabBooking, HealthCase
from . import services


class CampusWorkflowTests(TestCase):
    def setUp(self):
        self.settings_override = self.settings(EDUPILOT_FIELD_ENCRYPTION_KEY=Fernet.generate_key().decode())
        self.settings_override.enable()
        self.addCleanup(self.settings_override.disable)
        self.owner = User.objects.create_user('owner')
        self.maker = User.objects.create_user('maker')
        self.reviewer = User.objects.create_user('reviewer')
        self.school = Institution.objects.create(name='Test school', code='test')
        self.campus = Campus.objects.create(institution=self.school, name='North', code='north')
        self.other = Campus.objects.create(institution=self.school, name='South', code='south')
        self.role = RoleDefinition.objects.create(institution=self.school, name='Operations')
        for model in (LibraryBook, LibraryLoan, LabAsset, LabBooking, HealthCase, Student):
            for action in ('view', 'create', 'edit', 'approve'):
                RoleGrant.objects.create(role=self.role, resource=model._meta.label_lower, action=action)
        for user in (self.maker, self.reviewer):
            RoleAssignment.objects.create(user=user, role=self.role, campus=self.campus, approved_by=self.owner)
        self.student = Student.objects.create(student_id='S1', name='Student', father_name='Parent',
            mother_name='Parent', roll_no='1', date_of_birth=date(2010, 1, 1), email='student@example.test')
        RecordScope.objects.create(institution=self.school, campus=self.campus,
            resource='student_profile.student', object_id=self.student.pk)

    def test_library_capacity_return_and_campus_boundary(self):
        book = services.create_inventory(self.maker, LibraryBook, self.campus, {'title': 'Book', 'copies': 1})
        loan = services.issue_book(self.maker, book.pk, self.student, timezone.localdate())
        with self.assertRaises(ValidationError):
            services.issue_book(self.maker, book.pk, self.student, timezone.localdate())
        services.return_book(self.maker, loan.pk, 'Good')
        services.return_book(self.maker, loan.pk, 'Ignored duplicate')
        self.assertEqual(LibraryLoan.objects.get(pk=loan.pk).return_condition, 'Good')
        services.issue_book(self.maker, book.pk, self.student, timezone.localdate())
        with self.assertRaises(PermissionDenied):
            services.create_inventory(self.maker, LibraryBook, self.other, {'title': 'Forbidden'})

    def test_booking_independent_approval_and_overlap(self):
        asset = services.create_inventory(self.maker, LabAsset, self.campus,
            {'name': 'Microscope', 'laboratory': 'Science', 'inventory_code': 'M1'})
        start = timezone.now() + timedelta(days=1)
        first = services.book_lab(self.maker, asset.pk, start, start + timedelta(hours=1), 'Lesson')
        second = services.book_lab(self.maker, asset.pk, start, start + timedelta(hours=1), 'Other lesson')
        with self.assertRaises(PermissionDenied):
            services.decide_booking(self.maker, first.pk, True)
        services.decide_booking(self.reviewer, first.pk, True)
        with self.assertRaises(ValidationError):
            services.decide_booking(self.reviewer, second.pk, True)
        second.refresh_from_db()
        self.assertEqual(second.status, 'pending')
        with self.assertRaises(PermissionDenied):
            services.cancel_booking(self.reviewer, first.pk)
        services.cancel_booking(self.maker, first.pk)
        services.decide_booking(self.reviewer, second.pk, True)

    def test_confidential_notes_require_mfa_and_assigned_worker(self):
        values = dict(campus=self.campus, student=self.student, category='clinic',
                      notes='Private clinical notes', consent_reference='Consent 1')
        with self.assertRaises(PermissionDenied):
            services.create_case(self.maker, **values)
        case = services.create_case(self.maker, **values, mfa_verified=True)
        self.assertNotIn(values['notes'], case.encrypted_notes)
        with self.assertRaises(PermissionDenied):
            services.read_case(self.reviewer, case.pk, mfa_verified=True)
        self.assertEqual(services.read_case(self.maker, case.pk, mfa_verified=True)[1], values['notes'])
        with self.assertRaises(PermissionDenied):
            services.close_case(self.reviewer, case.pk, mfa_verified=True)
        services.close_case(self.maker, case.pk, mfa_verified=True)
        case.refresh_from_db()
        self.assertIsNotNone(case.closed_at)

    def test_workspace_and_forms_render_for_scoped_role_without_admin_group(self):
        self.client.force_login(self.maker)
        for url in (reverse('access_workspace'), reverse('operations_records', args=['library']),
                    reverse('operations_create', args=['library'])):
            response = self.client.get(url)
            self.assertEqual(response.status_code, 200, url)

    def test_forged_campus_in_inventory_form_is_rejected(self):
        self.client.force_login(self.maker)
        response = self.client.post(reverse('operations_create', args=['library']),
            {'campus': self.other.pk, 'title': 'Wrong campus', 'copies': 1})
        self.assertEqual(response.status_code, 200)
        self.assertFalse(LibraryBook.objects.exists())

    def test_scope_revocation_invalidates_existing_session(self):
        self.client.force_login(self.maker)
        RoleAssignment.objects.filter(user=self.maker).update(active=False)
        response = self.client.get(reverse('access_workspace'))
        self.assertEqual(response.status_code, 403)

    def test_other_campus_loan_identifier_is_not_accessible(self):
        book = services.create_inventory(self.maker, LibraryBook, self.campus, {'title': 'Book'})
        loan = services.issue_book(self.maker, book.pk, self.student, timezone.localdate())
        RoleAssignment.objects.filter(user=self.reviewer).update(campus=self.other)
        self.client.force_login(self.reviewer)
        response = self.client.post(reverse('operations_action', args=['loans', loan.pk]), {'action': 'return'})
        self.assertEqual(response.status_code, 404)
        loan.refresh_from_db()
        self.assertIsNone(loan.returned_at)

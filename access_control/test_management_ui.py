from datetime import date

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from student_profile.models import Student
from .models import Campus, Institution, RecordScope, RoleAssignment, RoleDefinition


class AccessManagementUiTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_superuser('security-admin', 'admin@example.test', 'secret')
        self.staff = User.objects.create_user('staff', password='secret')
        self.school = Institution.objects.create(name='School', code='school')
        self.campus = Campus.objects.create(institution=self.school, name='Main', code='main')
        self.role = RoleDefinition.objects.create(institution=self.school, name='Librarian')

    def test_management_pages_use_custom_ui_and_are_superuser_only(self):
        self.client.force_login(self.staff)
        self.assertEqual(self.client.get(reverse('access_security_center')).status_code, 403)
        self.client.force_login(self.admin)
        for name in ('access_security_center', 'access_institutions', 'access_campuses',
                     'access_accounts', 'access_roles', 'access_assignments',
                     'access_student_mapping', 'access_ownership_registry', 'access_approvals',
                     'access_payment_receipts', 'access_mfa_devices', 'access_audit_log'):
            response = self.client.get(reverse(name))
            self.assertEqual(response.status_code, 200, name)

    def test_role_permission_matrix_saves_explicit_grants(self):
        self.client.force_login(self.admin)
        response = self.client.post(reverse('access_role_edit', args=[self.role.pk]), {
            'institution': self.school.pk, 'name': self.role.name, 'active': 'on',
            'grant__school_operations.librarybook__view': '1',
            'grant__school_operations.libraryloan__create': '1',
        })
        self.assertRedirects(response, reverse('access_roles'))
        self.assertSetEqual(set(self.role.grants.values_list('resource', 'action')), {
            ('school_operations.librarybook', 'view'), ('school_operations.libraryloan', 'create')})

    def test_assignment_approval_and_revocation(self):
        self.client.force_login(self.admin)
        response = self.client.post(reverse('access_assignment_add'), {
            'user': self.staff.pk, 'role': self.role.pk, 'campus': self.campus.pk,
            'starts_at': '2026-09-08T12:00', 'active': 'on', 'is_primary': 'on'})
        self.assertRedirects(response, reverse('access_assignments'))
        assignment = RoleAssignment.objects.get(user=self.staff)
        self.assertIsNone(assignment.approved_by)
        self.client.post(reverse('access_assignment_action', args=[assignment.pk]), {'action': 'approve'})
        assignment.refresh_from_db()
        self.assertEqual(assignment.approved_by, self.admin)
        self.client.post(reverse('access_assignment_action', args=[assignment.pk]), {'action': 'revoke'})
        assignment.refresh_from_db()
        self.assertFalse(assignment.active)

    def test_student_mapping_builds_dimensions_server_side(self):
        student = Student.objects.create(student_id='S100', name='Student', father_name='Father',
            mother_name='Mother', roll_no='1', date_of_birth=date(2010, 1, 1), email='s100@example.test')
        self.client.force_login(self.admin)
        response = self.client.post(reverse('access_student_mapping'), {
            'institution': self.school.pk, 'campus': self.campus.pk, 'students': [student.pk]})
        self.assertRedirects(response, reverse('access_student_mapping'))
        owner = RecordScope.objects.get(resource='student_profile.student', object_id=student.pk)
        self.assertEqual(owner.campus, self.campus)
        self.assertEqual(owner.dimensions['student'], [student.pk])

    def test_existing_legacy_role_urls_open_the_new_security_ui(self):
        self.client.force_login(self.admin)
        for name in ('user_role_management', 'create_role', 'list_roles', 'assign_role'):
            response = self.client.get(reverse(name))
            self.assertEqual(response.status_code, 200, name)
            self.assertTemplateUsed(response, 'access_control/management/base.html')

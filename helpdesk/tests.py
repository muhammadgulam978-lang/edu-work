from datetime import date, timedelta

from django.contrib.auth.models import User
from django.core.exceptions import PermissionDenied
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from parent_dashboard.models import Parent
from student_profile.models import Student
from teacher_dashboard.models import Teacher

from .models import Ticket, TicketEvent, TicketMessage, TicketNotification
from .services import create_ticket, ensure_defaults, escalate_overdue_tickets, record_transition


def make_student(username, student_id):
    user = User.objects.create_user(username, password='TestPass@123')
    student = Student.objects.create(user=user, student_id=student_id, name=username.title(),
                                     father_name='Parent', mother_name='Parent', roll_no=student_id,
                                     date_of_birth=date(2012, 1, 1), email=f'{username}@example.com')
    return user, student


class HelpdeskWorkflowTests(TestCase):
    def setUp(self):
        self.categories = ensure_defaults()
        self.student_user, self.student = make_student('student.one', 'HD-001')
        self.other_user, self.other_student = make_student('student.two', 'HD-002')
        self.parent_user = User.objects.create_user('parent.one', password='TestPass@123')
        self.parent = Parent.objects.create(user=self.parent_user, full_name='Parent One')
        self.parent.students.add(self.student)
        self.teacher_user = User.objects.create_user('teacher.one', password='TestPass@123')
        self.teacher = Teacher.objects.create(user=self.teacher_user, name='Teacher One',
                                              email='teacher.one@example.com', gender='Male',
                                              faculty_group='Junior Section')
        self.staff = User.objects.create_superuser('support.admin', 'support@example.com', 'TestPass@123')

    def ticket(self, requester=None, student=None):
        return create_ticket(
            requester=requester or self.student_user, requester_role='STUDENT',
            student=student or self.student, category=self.categories['academics'],
            ticket_type='COMPLAINT', subject='Marks need review', description='Please verify the result.',
            priority='HIGH', privacy='NORMAL',
        )

    def test_ticket_number_sla_audit_and_notification_are_created(self):
        ticket = self.ticket()
        self.assertRegex(ticket.number, r'^TKT-\d{4}-\d{6}$')
        self.assertGreater(ticket.due_at, ticket.created_at)
        self.assertTrue(TicketEvent.objects.filter(ticket=ticket, action='SUBMITTED').exists())
        self.assertTrue(TicketNotification.objects.filter(ticket=ticket, user=self.student_user).exists())

    def test_parent_cannot_submit_for_unlinked_child(self):
        with self.assertRaises(PermissionDenied):
            create_ticket(requester=self.parent_user, requester_role='PARENT', student=self.other_student,
                          category=self.categories['academics'], ticket_type='ENQUIRY', subject='Question',
                          description='Question about results.')

    def test_portal_user_cannot_read_another_users_ticket(self):
        ticket = self.ticket()
        self.client.force_login(self.other_user)
        self.assertEqual(self.client.get(reverse('helpdesk:ticket_detail', args=[ticket.pk])).status_code, 404)

    def test_internal_notes_are_hidden_from_requester(self):
        ticket = self.ticket()
        TicketMessage.objects.create(ticket=ticket, author=self.staff, body='Private staff note', is_internal=True)
        TicketMessage.objects.create(ticket=ticket, author=self.staff, body='Public response', is_internal=False)
        self.client.force_login(self.student_user)
        response = self.client.get(reverse('helpdesk:ticket_detail', args=[ticket.pk]))
        self.assertContains(response, 'Public response')
        self.assertNotContains(response, 'Private staff note')

    def test_staff_resolves_and_requester_can_close(self):
        ticket = self.ticket()
        record_transition(ticket, self.staff, 'IN_REVIEW')
        ticket.resolution = 'Marks were corrected.'
        ticket.save(update_fields=['resolution', 'updated_at'])
        record_transition(ticket, self.staff, 'RESOLVED')
        self.client.force_login(self.student_user)
        response = self.client.post(reverse('helpdesk:ticket_portal_action', args=[ticket.pk, 'close']))
        self.assertEqual(response.status_code, 302)
        ticket.refresh_from_db()
        self.assertEqual(ticket.status, 'CLOSED')

    def test_requester_cannot_resolve_own_ticket(self):
        ticket = self.ticket()
        record_transition(ticket, self.staff, 'IN_REVIEW')
        with self.assertRaises(PermissionDenied):
            record_transition(ticket, self.student_user, 'RESOLVED')

    def test_overdue_ticket_is_escalated_only_once(self):
        ticket = self.ticket()
        Ticket.objects.filter(pk=ticket.pk).update(due_at=timezone.now() - timedelta(hours=1))
        self.assertEqual(escalate_overdue_tickets(), 1)
        self.assertEqual(escalate_overdue_tickets(), 0)
        self.assertEqual(TicketEvent.objects.filter(ticket=ticket, action='SLA_ESCALATED').count(), 1)

    def test_each_portal_gets_role_scoped_helpdesk_screen(self):
        for user in (self.student_user, self.parent_user, self.teacher_user):
            self.client.force_login(user)
            self.assertEqual(self.client.get(reverse('helpdesk:portal')).status_code, 200)
            self.assertEqual(self.client.get(reverse('helpdesk:ticket_create')).status_code, 200)
        self.client.force_login(self.parent_user)
        self.assertNotContains(self.client.get(reverse('helpdesk:ticket_create')), 'Salary, tax and deductions')
        self.client.force_login(self.teacher_user)
        self.assertContains(self.client.get(reverse('helpdesk:ticket_create')), 'Salary, tax and deductions')


class HelpdeskScreenTests(TestCase):
    def setUp(self):
        ensure_defaults()
        self.admin = User.objects.create_superuser('helpdesk.admin', 'helpdesk@example.com', 'TestPass@123')

    def test_staff_dashboard_is_real_app_screen(self):
        self.client.force_login(self.admin)
        response = self.client.get(reverse('helpdesk:staff_dashboard'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Ticket Operations Dashboard')

    def test_ordinary_account_cannot_open_staff_dashboard(self):
        user = User.objects.create_user('ordinary.helpdesk', password='TestPass@123')
        self.client.force_login(user)
        self.assertEqual(self.client.get(reverse('helpdesk:staff_dashboard')).status_code, 403)

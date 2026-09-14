from datetime import timedelta

from django.core.exceptions import PermissionDenied, ValidationError
from django.db import IntegrityError, transaction
from django.contrib.auth import get_user_model
from django.db.models import Max, Q
from django.utils import timezone

from .models import SLAPolicy, Ticket, TicketCategory, TicketEvent, TicketNotification


DEFAULT_CATEGORIES = [
    ('academics', 'Academics, exams and results', 'Academic', True, True, False, False),
    ('attendance', 'Attendance correction', 'Academic', True, True, True, False),
    ('fees', 'Fees, refund and concession', 'Finance', True, True, False, True),
    ('salary', 'Salary, tax and deductions', 'Finance', False, False, True, True),
    ('leave-hr', 'Leave and HR records', 'HR / Administration', False, False, True, True),
    ('timetable', 'Timetable and workload', 'Academic', True, True, True, False),
    ('transport', 'Transport', 'Transport', True, True, True, False),
    ('facilities', 'Facilities and equipment', 'Maintenance / Procurement', True, True, True, False),
    ('it-support', 'Portal and IT support', 'IT Support', True, True, True, False),
    ('safety', 'Safety, bullying or safeguarding', 'Safeguarding', True, True, True, True),
    ('documents', 'Certificate or document request', 'Administration', True, True, True, False),
]

DEFAULT_SLA = {'LOW': (72, 120), 'NORMAL': (24, 72), 'HIGH': (8, 24), 'URGENT': (4, 12), 'CRITICAL': (1, 4)}


def ensure_defaults():
    categories = {}
    for code, name, department, student, parent, teacher, confidential in DEFAULT_CATEGORIES:
        category, _ = TicketCategory.objects.get_or_create(code=code, defaults={
            'name': name, 'department': department, 'student_enabled': student,
            'parent_enabled': parent, 'teacher_enabled': teacher,
            'confidential_by_default': confidential,
        })
        categories[code] = category
    for priority, (first, resolution) in DEFAULT_SLA.items():
        SLAPolicy.objects.get_or_create(category=None, priority=priority,
                                       defaults={'first_response_hours': first, 'resolution_hours': resolution})
    return categories


def policy_for(category, priority):
    return (SLAPolicy.objects.filter(category=category, priority=priority, is_active=True).first()
            or SLAPolicy.objects.filter(category__isnull=True, priority=priority, is_active=True).first())


def next_ticket_number():
    year = timezone.localdate().year
    prefix = f'TKT-{year}-'
    latest = Ticket.objects.filter(number__startswith=prefix).aggregate(value=Max('number'))['value']
    sequence = int(latest.rsplit('-', 1)[-1]) + 1 if latest else 1
    return f'{prefix}{sequence:06d}'


@transaction.atomic
def create_ticket(*, requester, requester_role, category, ticket_type, subject, description,
                  priority='NORMAL', privacy='NORMAL', student=None, anonymous_to_handlers=False):
    if requester_role == 'PARENT' and (student is None or not requester.parent.students.filter(pk=student.pk).exists()):
        raise PermissionDenied('Parents can submit tickets only for their linked children.')
    if requester_role == 'STUDENT':
        if student and student.user_id != requester.pk:
            raise PermissionDenied('Students can submit tickets only for themselves.')
        student = requester.student
    enabled = {'STUDENT': category.student_enabled, 'PARENT': category.parent_enabled,
               'TEACHER': category.teacher_enabled}.get(requester_role, True)
    if not category.is_active or not enabled:
        raise ValidationError('This category is unavailable for your portal role.')
    policy = policy_for(category, priority)
    due_at = timezone.now() + timedelta(hours=policy.resolution_hours if policy else 72)
    if category.confidential_by_default and privacy == 'NORMAL':
        privacy = 'CONFIDENTIAL'
    ticket = None
    for _ in range(5):
        try:
            with transaction.atomic():
                ticket = Ticket.objects.create(
                    number=next_ticket_number(), requester=requester, requester_role=requester_role,
                    student=student, category=category, ticket_type=ticket_type, subject=subject,
                    description=description, priority=priority, privacy=privacy,
                    anonymous_to_handlers=anonymous_to_handlers,
                    assigned_department=category.department, due_at=due_at,
                )
            break
        except IntegrityError:
            continue
    if ticket is None:
        raise ValidationError('Could not allocate a ticket number. Please retry.')
    TicketEvent.objects.create(ticket=ticket, actor=requester, action='SUBMITTED', to_status='SUBMITTED')
    TicketNotification.objects.create(user=requester, ticket=ticket,
                                      text=f'{ticket.number} submitted to {category.department}.')
    return ticket


def record_transition(ticket, actor, target, details=None):
    allowed = {
        'SUBMITTED': {'ASSIGNED', 'IN_REVIEW', 'REJECTED'}, 'ASSIGNED': {'IN_REVIEW', 'WAITING_USER', 'RESOLVED'},
        'IN_REVIEW': {'WAITING_USER', 'RESOLVED', 'REJECTED'}, 'WAITING_USER': {'IN_REVIEW', 'RESOLVED'},
        'RESOLVED': {'REOPENED', 'CLOSED'}, 'REOPENED': {'IN_REVIEW', 'RESOLVED'},
    }
    if target not in allowed.get(ticket.status, set()):
        raise ValidationError(f'{ticket.get_status_display()} cannot change to {dict(Ticket.STATUS).get(target, target)}.')
    if ticket.requester_id == actor.pk and target in {'RESOLVED', 'REJECTED'}:
        raise PermissionDenied('A requester cannot resolve or reject their own ticket.')
    previous = ticket.status
    ticket.status = target
    now = timezone.now()
    if target == 'RESOLVED':
        ticket.resolved_at = now
    elif target == 'CLOSED':
        ticket.closed_at = now
    ticket.save(update_fields=['status', 'resolved_at', 'closed_at', 'updated_at'])
    TicketEvent.objects.create(ticket=ticket, actor=actor, action='STATUS_CHANGED', from_status=previous,
                               to_status=target, details=details or {})
    TicketNotification.objects.create(user=ticket.requester, ticket=ticket,
                                      text=f'{ticket.number} is now {ticket.get_status_display()}.')
    return ticket


def escalate_overdue_tickets():
    now = timezone.now()
    tickets = Ticket.objects.filter(due_at__lt=now).exclude(status__in=['RESOLVED', 'CLOSED', 'REJECTED'])
    escalated = 0
    User = get_user_model()
    principals = User.objects.filter(is_active=True).filter(
        Q(is_superuser=True) | Q(groups__name='Principal')
    ).distinct()
    for ticket in tickets:
        if ticket.events.filter(action='SLA_ESCALATED').exists():
            continue
        TicketEvent.objects.create(ticket=ticket, action='SLA_ESCALATED', details={'due_at': ticket.due_at.isoformat()})
        recipients = list(principals)
        if ticket.assigned_to and ticket.assigned_to not in recipients:
            recipients.append(ticket.assigned_to)
        TicketNotification.objects.bulk_create([
            TicketNotification(user=user, ticket=ticket, text=f'{ticket.number} breached its resolution SLA.')
            for user in recipients
        ])
        escalated += 1
    return escalated

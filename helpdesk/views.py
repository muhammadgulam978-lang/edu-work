from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.db.models import Avg, Q
from django.http import FileResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from .forms import AssignmentForm, MessageForm, RatingForm, ResolutionForm, StaffMessageForm, TicketForm
from .models import Ticket, TicketEvent, TicketMessage, TicketNotification
from .services import create_ticket, ensure_defaults, record_transition


STAFF_GROUPS = ['Admin', 'Support Officer', 'Department Head', 'Principal', 'Finance Officer', 'HR']


def _portal_role(user):
    if hasattr(user, 'parent'):
        return 'PARENT'
    if hasattr(user, 'student'):
        return 'STUDENT'
    if hasattr(user, 'teacher'):
        return 'TEACHER'
    raise PermissionDenied('A parent, student or teacher profile is required.')


def _base_for(role):
    return {'PARENT': 'parent_dashboard/base.html', 'STUDENT': 'student_profile/bases.html',
            'TEACHER': 'teacher_dashboard/bases.html'}[role]


def _is_helpdesk_staff(user):
    return user.is_authenticated and (user.is_staff or user.is_superuser or
                                      user.groups.filter(name__in=STAFF_GROUPS).exists())


def helpdesk_staff_required(view):
    @login_required(login_url='login_admin')
    def wrapped(request, *args, **kwargs):
        if not _is_helpdesk_staff(request.user):
            raise PermissionDenied('Helpdesk staff access is not assigned to this account.')
        return view(request, *args, **kwargs)
    return wrapped


def _visible_staff_tickets(user):
    tickets = Ticket.objects.select_related('requester', 'student', 'category', 'assigned_to')
    if not user.is_superuser:
        groups = set(user.groups.values_list('name', flat=True))
        if not (user.has_perm('helpdesk.view_safeguarding_tickets') or groups.intersection({'Principal', 'Safeguarding Officer'})):
            tickets = tickets.exclude(privacy='SAFEGUARDING')
        if not (user.has_perm('helpdesk.view_confidential_tickets') or groups.intersection({'Principal', 'Finance Officer', 'HR', 'Department Head'})):
            tickets = tickets.exclude(privacy='CONFIDENTIAL')
    if user.groups.filter(name='Department Head').exists() and hasattr(user, 'teacher') and user.teacher.department:
        tickets = tickets.filter(assigned_department=user.teacher.department)
    return tickets


@login_required
def portal_dashboard(request):
    ensure_defaults()
    role = _portal_role(request.user)
    tickets = Ticket.objects.filter(requester=request.user).select_related('student', 'category', 'assigned_to')
    status = request.GET.get('status', '')
    if status:
        tickets = tickets.filter(status=status)
    context = {
        'base_template': _base_for(role), 'portal_role': role, 'tickets': tickets,
        'open_count': tickets.exclude(status__in=['CLOSED', 'REJECTED']).count(),
        'waiting_count': tickets.filter(status='WAITING_USER').count(),
        'resolved_count': tickets.filter(status__in=['RESOLVED', 'CLOSED']).count(),
        'notifications': TicketNotification.objects.filter(user=request.user, is_read=False)[:5],
        'statuses': Ticket.STATUS,
    }
    return render(request, 'helpdesk/portal_dashboard.html', context)


@login_required
def ticket_create(request):
    ensure_defaults()
    role = _portal_role(request.user)
    form = TicketForm(request.POST or None, request.FILES or None, user=request.user, role=role)
    if request.method == 'POST' and form.is_valid():
        try:
            data = {key: form.cleaned_data[key] for key in ['ticket_type', 'student', 'category', 'subject',
                    'description', 'priority', 'privacy', 'anonymous_to_handlers']}
            ticket = create_ticket(requester=request.user, requester_role=role, **data)
            if form.cleaned_data.get('attachment'):
                TicketMessage.objects.create(ticket=ticket, author=request.user, body='Initial supporting document',
                                             attachment=form.cleaned_data['attachment'])
            messages.success(request, f'{ticket.number} submitted successfully.')
            return redirect('helpdesk:ticket_detail', pk=ticket.pk)
        except (PermissionDenied, ValidationError) as exc:
            form.add_error(None, exc)
    return render(request, 'helpdesk/ticket_form.html', {'form': form, 'base_template': _base_for(role),
                                                         'portal_role': role})


@login_required
def ticket_detail(request, pk):
    role = _portal_role(request.user)
    ticket = get_object_or_404(Ticket.objects.select_related('student', 'category', 'assigned_to'),
                               pk=pk, requester=request.user)
    TicketNotification.objects.filter(user=request.user, ticket=ticket).update(is_read=True)
    form = MessageForm(request.POST or None, request.FILES or None)
    if request.method == 'POST' and form.is_valid():
        item = form.save(commit=False)
        item.ticket, item.author = ticket, request.user
        item.save()
        TicketEvent.objects.create(ticket=ticket, actor=request.user, action='USER_REPLIED')
        if ticket.status == 'WAITING_USER':
            record_transition(ticket, request.user, 'IN_REVIEW')
        elif ticket.status == 'RESOLVED':
            record_transition(ticket, request.user, 'REOPENED')
        if ticket.assigned_to:
            TicketNotification.objects.create(user=ticket.assigned_to, ticket=ticket,
                                              text=f'{ticket.number} has a new user reply.')
        messages.success(request, 'Reply added.')
        return redirect('helpdesk:ticket_detail', pk=ticket.pk)
    return render(request, 'helpdesk/ticket_detail.html', {
        'ticket': ticket, 'ticket_messages': ticket.messages.filter(is_internal=False).select_related('author'),
        'events': ticket.events.all(), 'form': form, 'rating_form': RatingForm(),
        'base_template': _base_for(role), 'portal_role': role,
    })


@login_required
@require_POST
def ticket_portal_action(request, pk, action):
    ticket = get_object_or_404(Ticket, pk=pk, requester=request.user)
    try:
        if action == 'close':
            record_transition(ticket, request.user, 'CLOSED')
        elif action == 'reopen':
            record_transition(ticket, request.user, 'REOPENED')
        elif action == 'rate' and ticket.status in {'RESOLVED', 'CLOSED'}:
            form = RatingForm(request.POST)
            if not form.is_valid():
                raise ValidationError('Choose a rating from 1 to 5.')
            ticket.satisfaction_rating = form.cleaned_data['rating']
            ticket.satisfaction_comment = form.cleaned_data['comment']
            ticket.save(update_fields=['satisfaction_rating', 'satisfaction_comment', 'updated_at'])
            TicketEvent.objects.create(ticket=ticket, actor=request.user, action='RATED',
                                       details={'rating': ticket.satisfaction_rating})
        else:
            raise ValidationError('That action is unavailable for this ticket.')
        messages.success(request, 'Ticket updated.')
    except (PermissionDenied, ValidationError) as exc:
        messages.error(request, str(exc))
    return redirect('helpdesk:ticket_detail', pk=ticket.pk)


@helpdesk_staff_required
def staff_dashboard(request):
    ensure_defaults()
    tickets = _visible_staff_tickets(request.user)
    status, department, query = request.GET.get('status', ''), request.GET.get('department', ''), request.GET.get('q', '').strip()
    if status:
        tickets = tickets.filter(status=status)
    if department:
        tickets = tickets.filter(assigned_department=department)
    if query:
        tickets = tickets.filter(Q(number__icontains=query) | Q(subject__icontains=query) |
                                 Q(requester__username__icontains=query))
    now = timezone.now()
    all_visible = _visible_staff_tickets(request.user)
    context = {
        'tickets': tickets, 'statuses': Ticket.STATUS,
        'open_count': all_visible.exclude(status__in=['CLOSED', 'REJECTED']).count(),
        'overdue_count': all_visible.filter(due_at__lt=now).exclude(status__in=['RESOLVED', 'CLOSED', 'REJECTED']).count(),
        'unassigned_count': all_visible.filter(assigned_to__isnull=True).count(),
        'resolved_count': all_visible.filter(status__in=['RESOLVED', 'CLOSED']).count(),
        'average_rating': all_visible.aggregate(value=Avg('satisfaction_rating'))['value'],
        'departments': all_visible.order_by().values_list('assigned_department', flat=True).distinct(),
    }
    return render(request, 'helpdesk/staff_dashboard.html', context)


@helpdesk_staff_required
def staff_ticket_detail(request, pk):
    ticket = get_object_or_404(_visible_staff_tickets(request.user), pk=pk)
    return render(request, 'helpdesk/staff_ticket_detail.html', {
        'ticket': ticket, 'ticket_messages': ticket.messages.select_related('author'), 'events': ticket.events.all(),
        'message_form': StaffMessageForm(), 'assignment_form': AssignmentForm(instance=ticket),
        'resolution_form': ResolutionForm(),
    })


@helpdesk_staff_required
@require_POST
@transaction.atomic
def staff_ticket_action(request, pk, action):
    ticket = get_object_or_404(_visible_staff_tickets(request.user).select_for_update(), pk=pk)
    try:
        if action == 'assign':
            form = AssignmentForm(request.POST, instance=ticket)
            if not form.is_valid():
                raise ValidationError(form.errors.as_text())
            previous = ticket.status
            ticket = form.save(commit=False)
            if ticket.status == 'SUBMITTED':
                ticket.status = 'ASSIGNED'
            ticket.save()
            TicketEvent.objects.create(ticket=ticket, actor=request.user, action='ASSIGNED',
                                       from_status=previous, to_status=ticket.status,
                                       details={'department': ticket.assigned_department,
                                                'assignee': ticket.assigned_to_id})
            if ticket.assigned_to:
                TicketNotification.objects.create(user=ticket.assigned_to, ticket=ticket,
                                                  text=f'{ticket.number} was assigned to you.')
        elif action == 'reply':
            form = StaffMessageForm(request.POST, request.FILES)
            if not form.is_valid():
                raise ValidationError(form.errors.as_text())
            item = form.save(commit=False)
            item.ticket, item.author = ticket, request.user
            item.save()
            if not item.is_internal:
                if not ticket.first_responded_at:
                    ticket.first_responded_at = timezone.now()
                    ticket.save(update_fields=['first_responded_at', 'updated_at'])
                TicketNotification.objects.create(user=ticket.requester, ticket=ticket,
                                                  text=f'{ticket.number} has a new reply.')
            TicketEvent.objects.create(ticket=ticket, actor=request.user,
                                       action='INTERNAL_NOTE' if item.is_internal else 'STAFF_REPLIED')
        elif action == 'resolve':
            form = ResolutionForm(request.POST)
            if not form.is_valid():
                raise ValidationError('Resolution details are required.')
            ticket.resolution = form.cleaned_data['resolution']
            ticket.save(update_fields=['resolution', 'updated_at'])
            record_transition(ticket, request.user, 'RESOLVED', {'resolution': ticket.resolution})
        elif action in {'IN_REVIEW', 'WAITING_USER', 'REJECTED'}:
            note = request.POST.get('note', '').strip()
            if action == 'REJECTED' and not note:
                raise ValidationError('A rejection reason is required.')
            record_transition(ticket, request.user, action, {'note': note})
        else:
            raise ValidationError('Unknown helpdesk action.')
        messages.success(request, 'Ticket workflow updated.')
    except (PermissionDenied, ValidationError) as exc:
        messages.error(request, str(exc))
    return redirect('helpdesk:staff_ticket_detail', pk=ticket.pk)


@login_required
def attachment_download(request, pk):
    item = get_object_or_404(TicketMessage.objects.select_related('ticket').exclude(attachment=''),
                             pk=pk, attachment__isnull=False)
    is_staff = _is_helpdesk_staff(request.user) and _visible_staff_tickets(request.user).filter(pk=item.ticket_id).exists()
    is_owner = item.ticket.requester_id == request.user.pk and not item.is_internal
    if not (is_staff or is_owner):
        raise PermissionDenied('You cannot access this ticket attachment.')
    filename = item.attachment.name.rsplit('/', 1)[-1]
    return FileResponse(item.attachment.open('rb'), as_attachment=True, filename=filename)

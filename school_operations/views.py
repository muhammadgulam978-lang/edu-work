from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied, ValidationError
from django.http import Http404
from django.shortcuts import render, redirect, get_object_or_404
from django.views.decorators.http import require_POST
from django.db.models import Q

from access_control.models import Campus, RecordScope, RoleAssignment
from access_control.policy import permitted_assignment, scoped_queryset, assignments_for
from access_control.mfa import session_verified
from student_profile.models import Student
from .models import LibraryBook, LibraryLoan, LabAsset, LabBooking, HealthCase
from .forms import BookForm, LoanForm, AssetForm, BookingForm, CaseForm
from . import services

REGISTRY = {
    'library': (LibraryBook, BookForm, 'Library catalog', ['Title', 'Author', 'Copies']),
    'loans': (LibraryLoan, LoanForm, 'Book loans', ['Book', 'Student', 'Due date', 'Status']),
    'laboratory': (LabAsset, AssetForm, 'Laboratory equipment', ['Equipment', 'Laboratory', 'Quantity']),
    'bookings': (LabBooking, BookingForm, 'Laboratory bookings', ['Equipment', 'Starts', 'Ends', 'Status']),
    'health': (HealthCase, CaseForm, 'Confidential cases', ['Case', 'Student', 'Follow up', 'Status']),
}


def context_for(request):
    return {'mfa_verified': session_verified(request)}


def visible_records(request, model):
    ids = []
    for institution_id in RoleAssignment.objects.filter(user=request.user).values_list('role__institution_id', flat=True).distinct():
        ids.extend(scoped_queryset(request.user, 'view', model.objects.filter(archived=False),
                                    institution_id, **context_for(request)).values_list('pk', flat=True))
    result = model.objects.filter(pk__in=ids)
    if model is HealthCase:
        if not session_verified(request):
            return result.none()
        result = result.filter(assigned_to=request.user)
    return result


def allowed_campuses(request, model, action='create'):
    ids = []
    for campus in Campus.objects.select_related('institution'):
        if permitted_assignment(request.user, action, services.prospective_owner(model, campus), **context_for(request)):
            ids.append(campus.pk)
    return Campus.objects.filter(pk__in=ids)


def student_choices(request):
    ids = []
    for owner in RecordScope.objects.filter(resource='student_profile.student').select_related('campus'):
        if permitted_assignment(request.user, 'view', owner, **context_for(request)):
            ids.append(owner.object_id)
    return Student.objects.filter(pk__in=ids).order_by('name')


def workspace_links(request):
    links = []
    for key, (model, form, label, headers) in REGISTRY.items():
        if visible_records(request, model).exists() or allowed_campuses(request, model).exists():
            links.append({'key': key, 'label': label})
    return links


@login_required
def records(request, kind):
    if kind not in REGISTRY:
        raise Http404
    model, form_class, label, headers = REGISTRY[kind]
    items = visible_records(request, model).select_related('campus')
    can_create = allowed_campuses(request, model).exists()
    if not items.exists() and not can_create:
        raise PermissionDenied('Your current role and campus assignment do not permit this workspace.')
    rows = []
    for item in items:
        owner = services.ownership(item)
        actions = []
        if kind == 'library':
            cells = [item.title, item.author, item.copies]
        elif kind == 'loans':
            cells = [item.book.title, item.student.name, item.due_on, 'Returned' if item.returned_at else 'On loan']
            if not item.returned_at and permitted_assignment(request.user, 'edit', owner, **context_for(request)):
                actions = ['return']
        elif kind == 'laboratory':
            cells = [item.name, item.laboratory, item.quantity]
        elif kind == 'bookings':
            cells = [item.asset.name, item.starts_at, item.ends_at, item.get_status_display()]
            from django.utils import timezone
            if item.created_by_id == request.user.pk and item.status in {'pending', 'approved'} and item.starts_at > timezone.now() and permitted_assignment(
                    request.user, 'edit', owner, **context_for(request)):
                actions = ['cancel']
            if item.status == 'pending' and item.created_by_id != request.user.pk and permitted_assignment(
                    request.user, 'approve', owner, **context_for(request)):
                actions = ['approve', 'reject']
        else:
            cells = [f'Case {item.pk}', item.student.name, item.follow_up_on or '—', 'Closed' if item.closed_at else 'Open']
        rows.append({'id': item.pk, 'campus': item.campus.name, 'cells': cells, 'actions': actions})
        if kind == 'health':
            assignment = permitted_assignment(request.user, 'view', owner, **context_for(request))
            services.audit(request.user, assignment, item, 'health.list')
    return render(request, 'school_operations/list.html', {'title': label, 'headers': headers, 'rows': rows,
                  'kind': kind, 'can_create': can_create, 'workspace_links': workspace_links(request)})


@login_required
def create_record(request, kind):
    if kind not in REGISTRY:
        raise Http404
    model, form_class, label, headers = REGISTRY[kind]
    if not allowed_campuses(request, model).exists():
        raise PermissionDenied('You do not have permission to create records in this module.')
    form = form_class(request.POST or None)
    if 'campus' in form.fields:
        form.fields['campus'].queryset = allowed_campuses(request, model)
    if 'student' in form.fields:
        form.fields['student'].queryset = student_choices(request)
    if 'book' in form.fields:
        form.fields['book'].queryset = visible_records(request, LibraryBook)
    if 'asset' in form.fields:
        form.fields['asset'].queryset = visible_records(request, LabAsset)
    if request.method == 'POST' and form.is_valid():
        values = form.cleaned_data.copy()
        try:
            if kind in {'library', 'laboratory'}:
                services.create_inventory(request.user, model, values.pop('campus'), values, **context_for(request))
            elif kind == 'loans':
                services.issue_book(request.user, values['book'].pk, values['student'], values['due_on'], **context_for(request))
            elif kind == 'bookings':
                services.book_lab(request.user, values['asset'].pk, values['starts_at'], values['ends_at'], values['purpose'], **context_for(request))
            else:
                services.create_case(request.user, **values, **context_for(request))
        except ValidationError as exc:
            form.add_error(None, exc)
        else:
            messages.success(request, 'Record saved successfully.')
            return redirect('operations_records', kind=kind)
    return render(request, 'school_operations/form.html', {'title': label, 'form': form, 'kind': kind,
                                                           'workspace_links': workspace_links(request)})


@login_required
@require_POST
def record_action(request, kind, pk):
    if kind not in {'loans', 'bookings', 'health'}:
        raise Http404
    model = REGISTRY[kind][0]
    get_object_or_404(visible_records(request, model), pk=pk)
    action = request.POST.get('action')
    try:
        if kind == 'loans' and action == 'return':
            services.return_book(request.user, pk, request.POST.get('condition', ''), **context_for(request))
        elif kind == 'bookings' and action in {'approve', 'reject'}:
            services.decide_booking(request.user, pk, action == 'approve', **context_for(request))
        elif kind == 'bookings' and action == 'cancel':
            services.cancel_booking(request.user, pk, **context_for(request))
        elif kind == 'health' and action == 'close':
            services.close_case(request.user, pk, **context_for(request))
        else:
            raise ValidationError('Choose a valid action.')
    except ValidationError as exc:
        messages.error(request, '; '.join(exc.messages))
    else:
        messages.success(request, 'Action completed.')
    return redirect('operations_records', kind=kind)


@login_required
def case_detail(request, pk):
    get_object_or_404(visible_records(request, HealthCase), pk=pk)
    item, notes = services.read_case(request.user, pk, **context_for(request))
    can_close = not item.closed_at and bool(permitted_assignment(request.user, 'edit', services.ownership(item), **context_for(request)))
    return render(request, 'school_operations/case.html', {'title': f'Case {pk}', 'item': item, 'notes': notes, 'can_close': can_close,
                                                          'workspace_links': workspace_links(request)})

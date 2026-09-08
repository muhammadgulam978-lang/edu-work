from functools import wraps

from django.contrib import messages
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import transaction
from django.http import HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from student_profile.models import Student
from .management_forms import (AccountForm, AssignmentForm, CampusForm, InstitutionForm,
                               RoleForm, StudentCampusMappingForm)
from .models import (ApprovalRequest, AuditEvent, Campus, Institution, RecordScope,
                     RoleAssignment, RoleDefinition, RoleGrant, PaymentReceipt, MfaDevice)


RESOURCES = {
    'student_profile.student': 'Students', 'teacher_dashboard.teacher': 'Teachers',
    'teacher_dashboard.attendance': 'Attendance', 'teacher_dashboard.assignment': 'Assignments',
    'exam_system.generatedpaper': 'Examination papers', 'exam_system.centralizedresult': 'Results',
    'edupilot_core.feevoucher': 'Fee vouchers', 'edupilot_core.studentledger': 'Student ledgers',
    'edupilot_core.salaryvoucher': 'Salary vouchers', 'admin_panel.admission': 'Admissions',
    'admin_panel.purchaserequest': 'Purchase requests', 'admin_panel.employee': 'Employees',
    'admin_panel.vehicle': 'Vehicles', 'admin_panel.transporttrip': 'Transport trips',
    'school_operations.librarybook': 'Library catalog', 'school_operations.libraryloan': 'Library loans',
    'school_operations.labasset': 'Laboratory equipment', 'school_operations.labbooking': 'Laboratory bookings',
    'school_operations.healthcase': 'Confidential health cases',
}


def security_admin(view):
    @wraps(view)
    def wrapped(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('login_admin')
        if not request.user.is_active or not request.user.is_superuser:
            return HttpResponseForbidden('Only the institution security administrator may configure access.')
        return view(request, *args, **kwargs)
    return wrapped


def audit(request, action, obj, institution=None, evidence=None):
    AuditEvent.objects.create(actor=request.user, institution=institution, action=action,
        resource=obj._meta.label_lower, object_id=str(obj.pk), outcome='allowed', evidence=evidence or {})


@security_admin
def security_center(request):
    return render(request, 'access_control/management/dashboard.html', {'institutions': Institution.objects.filter(active=True), 'summary': {
        'institutions': Institution.objects.count(), 'campuses': Campus.objects.count(),
        'accounts': get_user_model().objects.count(), 'roles': RoleDefinition.objects.count(),
        'pending': RoleAssignment.objects.filter(active=True, approved_by__isnull=True).count(),
        'unmapped_students': Student.objects.exclude(pk__in=RecordScope.objects.filter(
            resource='student_profile.student').values('object_id')).count(),
    }, 'recent_audit': AuditEvent.objects.select_related('actor').order_by('-created_at')[:8]})


def _save_form(request, form_class, title, back_name, instance=None):
    form = form_class(request.POST or None, instance=instance)
    if request.method == 'POST' and form.is_valid():
        obj = form.save()
        institution = obj if isinstance(obj, Institution) else getattr(obj, 'institution', None)
        audit(request, 'configuration.save', obj, institution)
        messages.success(request, f'{obj._meta.verbose_name.title()} saved successfully.')
        return redirect(back_name)
    return render(request, 'access_control/management/form.html', {'title': title, 'form': form, 'back_name': back_name})


@security_admin
def institutions(request):
    return render(request, 'access_control/management/simple_list.html', {'title': 'Institutions',
        'items': Institution.objects.order_by('name'), 'columns': ('Name', 'Code', 'Status'), 'kind': 'institution'})

@security_admin
def institution_add(request): return _save_form(request, InstitutionForm, 'Add institution', 'access_institutions')

@security_admin
def institution_edit(request, pk):
    return _save_form(request, InstitutionForm, 'Edit institution', 'access_institutions', get_object_or_404(Institution, pk=pk))

@security_admin
def campuses(request):
    return render(request, 'access_control/management/simple_list.html', {'title': 'Campuses',
        'items': Campus.objects.select_related('institution').order_by('institution__name', 'name'),
        'columns': ('Campus', 'Code', 'Institution'), 'kind': 'campus'})

@security_admin
def campus_add(request): return _save_form(request, CampusForm, 'Add campus', 'access_campuses')

@security_admin
def campus_edit(request, pk):
    return _save_form(request, CampusForm, 'Edit campus', 'access_campuses', get_object_or_404(Campus, pk=pk))

@security_admin
def accounts(request):
    return render(request, 'access_control/management/accounts.html', {'title': 'User accounts', 'users': get_user_model().objects.order_by('username')})

@security_admin
def account_add(request): return _save_form(request, AccountForm, 'Add account', 'access_accounts')

@security_admin
def account_edit(request, pk):
    return _save_form(request, AccountForm, 'Edit account', 'access_accounts', get_object_or_404(get_user_model(), pk=pk))

@security_admin
def roles(request):
    return render(request, 'access_control/management/roles.html', {'title': 'Roles & permissions', 'roles': RoleDefinition.objects.select_related('institution').prefetch_related('grants').order_by('institution__name', 'name')})

@security_admin
def role_add(request): return _save_form(request, RoleForm, 'Add role', 'access_roles')

@security_admin
@transaction.atomic
def role_edit(request, pk):
    role = get_object_or_404(RoleDefinition, pk=pk)
    form = RoleForm(request.POST or None, instance=role)
    actions = [value for value, label in RoleGrant.ACTIONS]
    if request.method == 'POST' and form.is_valid():
        role = form.save()
        requested = {(resource, action) for resource in RESOURCES for action in actions
                     if request.POST.get(f'grant__{resource}__{action}') == '1'}
        for resource in RESOURCES:
            for action in actions:
                grant = RoleGrant.objects.filter(role=role, resource=resource, action=action).first()
                if (resource, action) in requested:
                    if grant:
                        if not grant.allowed:
                            grant.allowed = True; grant.save(update_fields=['allowed'])
                    else:
                        RoleGrant.objects.create(role=role, resource=resource, action=action, allowed=True)
                elif grant:
                    grant.delete()
        audit(request, 'role.permissions.save', role, role.institution, {'grant_count': len(requested)})
        messages.success(request, 'Role and permission matrix saved.')
        return redirect('access_roles')
    selected = {(g.resource, g.action) for g in role.grants.filter(allowed=True)}
    matrix = [{'resource': resource, 'label': label,
               'actions': [{'name': action, 'checked': (resource, action) in selected} for action in actions]}
              for resource, label in RESOURCES.items()]
    return render(request, 'access_control/management/role_form.html', {'title': 'Edit role permissions',
        'form': form, 'role': role, 'actions': actions, 'matrix': matrix})

@security_admin
def assignments(request):
    return render(request, 'access_control/management/assignments.html', {'title': 'Role assignments', 'assignments': RoleAssignment.objects.select_related(
        'user', 'role__institution', 'campus', 'approved_by').order_by('-active', 'user__username')})

@security_admin
def assignment_add(request):
    form = AssignmentForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        obj = form.save(commit=False); obj.approved_by = None; obj.save()
        audit(request, 'role.assignment.create', obj, obj.role.institution)
        messages.success(request, 'Assignment created and sent for independent approval.')
        return redirect('access_assignments')
    return render(request, 'access_control/management/form.html', {'title': 'Assign role and campus', 'form': form, 'back_name': 'access_assignments'})

@security_admin
def assignment_edit(request, pk):
    obj = get_object_or_404(RoleAssignment, pk=pk)
    form = AssignmentForm(request.POST or None, instance=obj)
    if request.method == 'POST' and form.is_valid():
        obj = form.save(commit=False)
        obj.approved_by = None
        obj.save()
        audit(request, 'role.assignment.edit', obj, obj.role.institution)
        messages.success(request, 'Assignment updated and returned for independent approval.')
        return redirect('access_assignments')
    return render(request, 'access_control/management/form.html', {'title': 'Edit role assignment',
        'form': form, 'back_name': 'access_assignments'})


@security_admin
@require_POST
@transaction.atomic
def seed_role_templates(request):
    institution = get_object_or_404(Institution, pk=request.POST.get('institution'), active=True)
    from .management.commands.seed_access_roles import ROLES, TEMPLATES
    sensitive = {'Health Officer', 'Finance Officer', 'HR and Payroll Officer',
                 'Institution Super Admin', 'SIS Platform Administrator'}
    created = 0
    for name in ROLES:
        role, was_created = RoleDefinition.objects.get_or_create(institution=institution, name=name,
            defaults={'system': True, 'requires_mfa': name in sensitive})
        created += int(was_created)
        for resource, actions in TEMPLATES.get(name, {}).items():
            for action in actions:
                RoleGrant.objects.get_or_create(role=role, resource=resource, action=action,
                                                defaults={'allowed': True})
    AuditEvent.objects.create(actor=request.user, institution=institution, action='role.templates.seed',
        resource='access_control.roledefinition', outcome='allowed', evidence={'created': created})
    messages.success(request, f'Standard role templates are ready. {created} new roles were created; review permissions before assignment.')
    return redirect('access_roles')

@security_admin
@require_POST
def assignment_action(request, pk):
    obj = get_object_or_404(RoleAssignment.objects.select_related('role__institution'), pk=pk)
    action = request.POST.get('action')
    if action == 'approve':
        if obj.user_id == request.user.pk:
            return HttpResponseForbidden('You cannot approve your own access assignment.')
        obj.approved_by = request.user; obj.save()
    elif action == 'revoke':
        obj.active = False; obj.approved_by = None; obj.save()
    else:
        return HttpResponseForbidden('Invalid assignment action.')
    audit(request, f'role.assignment.{action}', obj, obj.role.institution)
    messages.success(request, f'Assignment {action}d.')
    return redirect('access_assignments')

@security_admin
@transaction.atomic
def student_mapping(request):
    students = Student.objects.order_by('student_id')
    form = StudentCampusMappingForm(request.POST or None, students=students)
    if request.method == 'POST' and form.is_valid():
        institution, campus = form.cleaned_data['institution'], form.cleaned_data['campus']
        count = 0
        for student_id in form.cleaned_data['students']:
            student = get_object_or_404(Student, pk=int(student_id))
            dimensions = {'student': [student.pk]}
            if student.class_fk_id: dimensions['class'] = [student.class_fk_id]
            if student.section_id: dimensions['section'] = [student.section_id]
            if student.academic_year_id: dimensions['academic_year'] = [student.academic_year_id]
            RecordScope.objects.update_or_create(resource='student_profile.student', object_id=student.pk,
                defaults={'institution': institution, 'campus': campus, 'dimensions': dimensions})
            count += 1
        AuditEvent.objects.create(actor=request.user, institution=institution, action='student.campus.map',
            resource='student_profile.student', outcome='allowed', evidence={'campus': campus.pk, 'count': count})
        messages.success(request, f'{count} student record(s) mapped to {campus.name}.')
        return redirect('access_student_mapping')
    mappings = RecordScope.objects.filter(resource='student_profile.student').select_related('institution', 'campus')
    mapped = {m.object_id: m for m in mappings}
    rows = [{'student': s, 'mapping': mapped.get(s.pk)} for s in students]
    return render(request, 'access_control/management/student_mapping.html', {'title': 'Student campus mapping', 'form': form, 'rows': rows})

@security_admin
def approvals(request):
    return render(request, 'access_control/management/approvals.html', {'title': 'Approval queue', 'items': ApprovalRequest.objects.select_related(
        'maker', 'reviewer', 'ownership__institution', 'ownership__campus').order_by('-created_at')})


@security_admin
def ownership_registry(request):
    items = RecordScope.objects.select_related('institution', 'campus').order_by('resource', 'object_id')[:1000]
    return render(request, 'access_control/management/ownership.html', {'title': 'Record ownership', 'items': items})


@security_admin
def payment_receipts(request):
    items = PaymentReceipt.objects.select_related('voucher', 'recorded_by').order_by('-created_at')[:1000]
    return render(request, 'access_control/management/receipts.html', {'title': 'Payment receipts', 'items': items})


@security_admin
def mfa_devices(request):
    return render(request, 'access_control/management/mfa_devices.html', {'title': 'Authenticators', 'items': MfaDevice.objects.select_related(
        'user').order_by('user__username')})


@security_admin
@require_POST
@transaction.atomic
def revoke_mfa_device(request, pk):
    device = get_object_or_404(MfaDevice.objects.select_for_update().select_related('user'), pk=pk)
    AuditEvent.objects.create(actor=request.user, action='mfa.device.revoke', resource='access_control.mfadevice',
        object_id=str(device.pk), outcome='allowed', evidence={'user_id': device.user_id})
    username = device.user.username
    device.delete()
    messages.success(request, f'Authenticator enrollment revoked for {username}. The user can enroll again.')
    return redirect('access_mfa_devices')

@security_admin
def audit_log(request):
    items = AuditEvent.objects.select_related('actor', 'institution').order_by('-created_at')[:500]
    return render(request, 'access_control/management/audit.html', {'title': 'Access audit', 'items': items})

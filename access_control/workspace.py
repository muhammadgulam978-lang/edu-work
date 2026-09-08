import time
from django import forms
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied, ValidationError, ImproperlyConfigured
from django.db.models import Q
from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone
from django.views.decorators.http import require_http_methods

from .models import RoleAssignment, ApprovalRequest, MfaDevice
from .policy import permitted_assignment, require_action
from .mfa import begin_enrollment, verify_code, session_verified
from .workflows import transition


def current_assignments(user):
    now = timezone.now()
    return RoleAssignment.objects.filter(user=user, active=True, role__active=True,
        role__institution__active=True, approved_by__isnull=False, starts_at__lte=now
        ).exclude(approved_by=user).filter(Q(ends_at__isnull=True) | Q(ends_at__gt=now)).select_related('role', 'campus')


def approval_items(request):
    context = {'mfa_verified': session_verified(request)}
    return [item for item in ApprovalRequest.objects.select_related('ownership', 'maker', 'reviewer').order_by('-created_at')
            if permitted_assignment(request.user, 'view', item.ownership, **context)]


@login_required
def home(request):
    from school_operations.views import workspace_links
    assignments = current_assignments(request.user)
    return render(request, 'access_control/home.html', {
        'title': 'My workspace', 'assignments': assignments,
        'workspace_links': workspace_links(request), 'items': approval_items(request),
        'mfa_verified': session_verified(request),
    })


class AuthenticatorForm(forms.Form):
    password = forms.CharField(required=False, widget=forms.PasswordInput(attrs={'class': 'form-control', 'autocomplete': 'current-password'}))
    code = forms.RegexField(regex=r'^\d{6}$', required=False, label='Authenticator code',
                            widget=forms.TextInput(attrs={'class': 'form-control', 'inputmode': 'numeric', 'autocomplete': 'one-time-code'}))


@login_required
@require_http_methods(['GET', 'POST'])
def authenticator(request):
    device = MfaDevice.objects.filter(user=request.user).first()
    form = AuthenticatorForm(request.POST or None)
    secret = None
    if request.method == 'POST' and form.is_valid():
        if request.POST.get('action') == 'enroll':
            if not form.cleaned_data.get('password') or not request.user.check_password(form.cleaned_data['password']):
                form.add_error('password', 'Enter your current password to set up an authenticator.')
            else:
                try:
                    secret = begin_enrollment(request.user)
                except ImproperlyConfigured:
                    form.add_error(None, 'The administrator must configure protected storage before authenticator setup.')
        elif request.POST.get('action') == 'verify':
            if verify_code(request.user, form.cleaned_data.get('code')):
                request.session['mfa_verified_until'] = time.time() + 15 * 60
                messages.success(request, 'Identity verified for the next 15 minutes.')
                return redirect('access_workspace')
            form.add_error('code', 'The code is invalid, already used, or temporarily locked. Try a fresh code later.')
        else:
            form.add_error(None, 'Choose a valid action.')
    return render(request, 'access_control/authenticator.html', {
        'title': 'Verify your identity', 'form': form, 'device': device, 'secret': secret,
    })


@login_required
@require_http_methods(['GET', 'POST'])
def approval_detail(request, pk):
    item = get_object_or_404(ApprovalRequest.objects.select_related('ownership', 'maker', 'reviewer'), pk=pk)
    context = {'mfa_verified': session_verified(request)}
    require_action(request.user, 'view', item.ownership, **context)
    if request.method == 'POST':
        try:
            version = int(request.POST.get('version', ''))
            transition(request.user, pk, request.POST.get('action'), version, request.POST.get('reason', ''), **context)
        except (ValueError, ValidationError) as exc:
            messages.error(request, '; '.join(exc.messages) if isinstance(exc, ValidationError) else 'Reload the current record before deciding.')
        else:
            messages.success(request, 'Decision recorded.')
        return redirect('access_approval_detail', pk=pk)
    can_decide = item.status == 'submitted' and item.reviewer_id == request.user.pk and item.maker_id != request.user.pk and bool(
        permitted_assignment(request.user, 'approve', item.ownership, **context))
    can_submit = item.status == 'draft' and item.maker_id == request.user.pk and bool(
        permitted_assignment(request.user, 'submit', item.ownership, **context))
    return render(request, 'access_control/approval.html', {'title': 'Review request', 'item': item,
        'can_decide': can_decide, 'can_submit': can_submit,
        'details': [(key.replace('_', ' ').capitalize(), value) for key, value in item.payload.items()]})

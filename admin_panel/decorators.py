# admin_panel/decorators.py

from functools import wraps
from django.http import HttpResponseForbidden
from django.shortcuts import redirect
from django.conf import settings


def role_required(permission_code):
    """
    Checks if the logged-in user has the given permission.
    Uses Django's built-in permissions (via Groups).
    
    Example:
        @role_required('admin_panel.can_approve_admission')
    or just:
        @role_required('can_approve_admission')
    """

    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return redirect(settings.LOGIN_URL)

            # ✅ Superuser always has full access
            if request.user.is_superuser:
                return view_func(request, *args, **kwargs)

            # Determine full permission path if only codename is passed
            if '.' in permission_code:
                full_perm = permission_code
            else:
                # fallback to common app names (admin_panel, teacher_dashboard, etc.)
                candidates = [
                    f"admin_panel.{permission_code}",
                    f"teacher_dashboard.{permission_code}",
                    f"student_profile.{permission_code}",
                ]
                for c in candidates:
                    if request.user.has_perm(c):
                        return view_func(request, *args, **kwargs)
                return HttpResponseForbidden("You don't have permission to access this page.")
            
            # Direct check
            if request.user.has_perm(full_perm):
                return view_func(request, *args, **kwargs)

            return HttpResponseForbidden("You don't have permission to access this page.")
        return _wrapped_view
    return decorator







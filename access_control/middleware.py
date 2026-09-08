from django.contrib.auth import logout
from django.core.exceptions import PermissionDenied
from django.http import HttpResponseForbidden
from django.shortcuts import redirect
from django.utils.cache import patch_cache_control

from .identity import authorization_fingerprint, effective_role, has_portal


class IdentityBoundaryMiddleware:
    """Portal boundaries and immediate invalidation of changed legacy claims."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated:
            try:
                request.effective_role = effective_role(request.user)
                fingerprint = authorization_fingerprint(request.user)
                previous = request.session.get('authorization_fingerprint')
                if previous is not None and previous != fingerprint:
                    logout(request)
                    return HttpResponseForbidden('Your access changed. Please sign in again.')
                request.session['authorization_fingerprint'] = fingerprint
            except PermissionDenied:
                return HttpResponseForbidden('Your role assignments need administrator review.')
        response = self.get_response(request)
        if request.user.is_authenticated:
            patch_cache_control(response, private=True, no_store=True)
        return response

    def process_view(self, request, view_func, view_args, view_kwargs):
        from .route_permissions import check_route
        check_route(request, view_func, view_kwargs)
        module = view_func.__module__
        portal = {'parent_dashboard': 'parent', 'student_profile': 'student',
                  'teacher_dashboard': 'teacher', 'admin_panel': 'admin',
                  'admin_ai': 'admin', 'ai_tutor': 'student'}.get(module.split('.')[0])
        if module in {'edupilot_core.views', 'edupilot_core.crud_views'}:
            portal = {'student_dashboard': 'student', 'teacher_dashboard': 'teacher',
                      'parent_dashboard': 'parent'}.get(view_func.__name__, 'admin')
        if module == 'edupilot_core.voucher_portal':
            portal = view_kwargs.get('portal_role', '').lower() or None
        # Login endpoints remain available; domain checks are additional to this boundary.
        if view_func.__name__ in {'custom_login', 'login_view', 'logout_view'}:
            return None
        if portal:
            if not request.user.is_authenticated:
                return redirect('login')
            if not has_portal(request.user, portal):
                return HttpResponseForbidden('You do not have access to this portal.')
        return None

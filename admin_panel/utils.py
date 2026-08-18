

# # def get_user_role(user):
# #     if user.groups.filter(name='Teacher').exists():
# #         return 'Teacher'
# #     elif user.groups.filter(name='Parent').exists():
# #         return 'Parent'
# #     elif user.groups.filter(name='Student').exists():
# #         return 'Student'
# #     return 'Unknown'
# from django.http import HttpResponseForbidden

# def coreadmin_required(view_func):
#     def _wrapped(request, *args, **kwargs):
#         if not request.user.is_authenticated:
#             return HttpResponseForbidden("Authentication required")
#         if request.user.username.lower() != "coreadmin":
#             return HttpResponseForbidden("Only coreadmin can perform this action")
#         return view_func(request, *args, **kwargs)
#     return _wrapped


# # ===========================================================================
# from .models import Chapter, Topic, SubTopic

# def build_toc_json(book):
#     """
#     Returns nested JSON of Chapters -> Topics -> Subtopics
#     """
#     data = {"chapters": []}
#     for ch in book.chapters.all():
#         ch_dict = {"title": ch.title, "topics": []}
#         for t in ch.topics.all():
#             t_dict = {"title": t.title, "subtopics": []}
#             for st in t.subtopics.all():
#                 t_dict["subtopics"].append({"title": st.title})
#             ch_dict["topics"].append(t_dict)
#         data["chapters"].append(ch_dict)
#     return data


# # ===========================================================================
# from functools import wraps
# from django.core.exceptions import PermissionDenied
# from .models import UserRole

# def has_permission(user, code):
#     """
#     Check if a user has a specific permission based on assigned role.
#     - Superusers are always allowed.
#     - Permissions are stored in Role.permissions (ManyToMany).
#     """
#     if not user.is_authenticated:
#         return False

#     # Superusers bypass all permission checks
#     if user.is_superuser:
#         return True

#     try:
#         user_role = (
#             UserRole.objects
#             .select_related('role')
#             .prefetch_related('role__permissions')
#             .get(user=user)
#         )

#         # Case 1: Check explicit permission code
#         if user_role.role.permissions.filter(code=code).exists():
#             return True

#         # Case 2: (Fallback) Allow direct role name check for simple decorators
#         # Example: @role_required('Teacher')
#         if user_role.role.name.strip().lower() == code.strip().lower():
#             return True

#         return False

#     except UserRole.DoesNotExist:
#         return False


# def role_required(code):
#     """
#     Decorator to restrict view access based on role permission.
#     Usage examples:
#         @role_required('teacher_dashboard')  # Permission-based
#         @role_required('Teacher')             # Role-name based (fallback)
#     """
#     def decorator(view_func):
#         @wraps(view_func)
#         def _wrapped_view(request, *args, **kwargs):
#             if not has_permission(request.user, code):
#                 raise PermissionDenied
#             return view_func(request, *args, **kwargs)
#         return _wrapped_view
#     return decorator

# =============================================================================================================
# admin_panel/utils.py
from functools import wraps
from django.contrib.auth.decorators import permission_required as dj_permission_required
from django.contrib.auth.models import Group
from django.core.exceptions import PermissionDenied
from django.shortcuts import redirect
from django.conf import settings
from django.http import HttpResponseForbidden

def group_required(group_name):
    """
    Decorator: allow only users in a specific Group.
    Example: @group_required('Admin')
    """
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return redirect(settings.LOGIN_URL)
            if request.user.groups.filter(name=group_name).exists() or request.user.is_superuser:
                return view_func(request, *args, **kwargs)
            raise PermissionDenied
        return _wrapped
    return decorator

def role_required(permission_codename):
    """
    Wrapper that emulates your previous @role_required('something') usage.
    It will check user.has_perm('app_label.permission_codename') if the passed value
    contains a dot; otherwise it will try to match permission codes in common apps.
    Use exact permission codes when possible: 'admin_panel.can_approve_admission'
    """
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return redirect(settings.LOGIN_URL)

            # if user is superuser allow
            if request.user.is_superuser:
                return view_func(request, *args, **kwargs)

            # if the permission passed already looks like app_label.codename, use has_perm directly
            if '.' in permission_codename:
                perm = permission_codename
            else:
                # fallback: try common app labels (admin_panel, student_profile, teacher_dashboard)
                candidates = [
                    f"admin_panel.{permission_codename}",
                    f"student_profile.{permission_codename}",
                    f"teacher_dashboard.{permission_codename}",
                ]
                perm = None
                for c in candidates:
                    if request.user.has_perm(c):
                        perm = c
                        break

            # final check
            if perm:
                # if we've already validated via candidates above, proceed
                return view_func(request, *args, **kwargs)
            else:
                # If permission codename has app_label form, check it now
                if request.user.has_perm(permission_codename):
                    return view_func(request, *args, **kwargs)
                # Deny
                raise PermissionDenied
        return _wrapped
    return decorator

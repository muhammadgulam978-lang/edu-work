# admin_panel/context_processors.py
from django.contrib.auth.models import Group

def user_permissions(request):
    """
    Global context processor — adds `user_permissions` and `user_role`
    to all templates automatically.
    
    Works with Django's built-in Group & Permission system.
    """

    if not request.user.is_authenticated:
        return {}

    # ✅ Get user's groups (roles)
    groups = request.user.groups.all()
    role_name = groups.first().name if groups.exists() else None

    # ✅ Get all permissions (from groups + user)
    permissions = list(request.user.get_all_permissions())

    # ✅ Superusers always have all permissions
    if request.user.is_superuser:
        permissions.append("all_permissions")

    return {
        'user_role': role_name,
        'user_permissions': permissions,
    }


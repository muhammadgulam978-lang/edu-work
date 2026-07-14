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


def teacher_fixture_notifications(request):
    if not request.user.is_authenticated:
        return {}

    try:
        from teacher_dashboard.models import Teacher
        from admin_panel.models import TeacherNotification

        teacher = Teacher.objects.filter(user=request.user).first()
        if not teacher:
            return {}

        notifications = TeacherNotification.objects.filter(teacher=teacher).order_by('-created_at')[:8]
        unread_count = TeacherNotification.objects.filter(teacher=teacher, is_read=False).count()
        return {
            'teacher_fixture_notifications': notifications,
            'teacher_fixture_unread_count': unread_count,
        }
    except Exception:
        return {}


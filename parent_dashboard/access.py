"""Current guardian authority, used for pages, delivery, and communication alike."""
from django.db.models import Q
from django.utils import timezone


def accessible_students(parent):
    from student_profile.models import Student
    if parent is None or not parent.user_id or not parent.user.is_active:
        return Student.objects.none()
    now = timezone.now()
    return Student.objects.filter(
        guardian_links__parent=parent,
        guardian_links__portal_access=True,
        guardian_links__verified_at__isnull=False,
    ).filter(Q(guardian_links__expires_at__isnull=True) |
             Q(guardian_links__expires_at__gt=now)).distinct()


def can_access_child(user, student_id):
    parent = getattr(user, 'parent', None)
    return bool(parent and accessible_students(parent).filter(pk=student_id).exists())

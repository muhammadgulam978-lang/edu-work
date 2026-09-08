"""One interpretation of existing identity, independent of profile display labels."""
import hashlib
import json

from django.core.exceptions import PermissionDenied


COMMUNITY = {'teacher', 'student', 'parent'}


def role_names(user):
    if not user.is_authenticated or not user.is_active:
        return []
    return list(user.groups.order_by('name').values_list('name', flat=True))


def effective_role(user):
    names = role_names(user)
    if not user.is_authenticated or not user.is_active:
        return None
    if user.is_superuser:
        return 'Super Admin'
    from .models import RoleAssignment
    from django.db.models import Q
    from django.utils import timezone
    now = timezone.now()
    scoped = RoleAssignment.objects.filter(user=user)
    if scoped.exists():
        active = list(scoped.filter(active=True, role__active=True, role__institution__active=True,
                                  starts_at__lte=now, approved_by__isnull=False).exclude(approved_by=user)
                      .filter(Q(ends_at__isnull=True) | Q(ends_at__gt=now)).select_related('role'))
        primary = [assignment for assignment in active if assignment.is_primary]
        if len(primary) == 1:
            return primary[0].role.name
        if not active:
            return None
        if len(primary) > 1 or len({assignment.role.name for assignment in active}) != 1:
            raise PermissionDenied('An explicit primary scoped role is required.')
        return active[0].role.name
    # UserRole is an explicit primary assignment, never a profile-type guess.
    from admin_panel.models import UserRole
    primary = UserRole.objects.filter(user=user).values_list('role__name', flat=True).first()
    if primary:
        if primary not in names:
            raise PermissionDenied('Role assignments conflict. Contact your administrator.')
        return primary
    if len(names) == 1:
        return names[0]
    if len(names) > 1:
        raise PermissionDenied('An explicit primary role is required.')
    return None


def has_portal(user, portal):
    names = {name.lower() for name in role_names(user)}
    if not names and not (user.is_authenticated and user.is_active and user.is_superuser):
        return False
    selected = effective_role(user)  # Reject contradictory claims on every entry path.
    if selected is None:
        return False
    if portal == 'admin':
        # A custom group name alone must not open the unrestricted legacy admin shell.
        return user.is_superuser or 'admin' in names
    return portal in names and hasattr(user, portal)


def authorization_fingerprint(user):
    """Read claims afresh: Django's in-object permission cache must not survive changes."""
    from django.contrib.auth.models import Permission
    from django.db.models import Q
    from admin_panel.models import UserRole
    permissions = Permission.objects.filter(
        Q(group__user=user) | Q(user=user)
    ).order_by('pk').values_list('pk', flat=True).distinct()
    primary = UserRole.objects.filter(user=user).values_list('role_id', flat=True).first()
    claims = [user.is_active, user.is_superuser, user.is_staff, primary,
              list(user.groups.order_by('pk').values_list('pk', flat=True)), list(permissions)]
    from .models import RoleAssignment, RoleGrant
    assignments = RoleAssignment.objects.filter(user=user).order_by('pk')
    claims.append(list(assignments.values('id', 'role_id', 'campus_id', 'scope', 'active',
                                         'is_primary',
                                         'starts_at', 'ends_at', 'approved_by_id', 'role__active',
                                         'role__requires_mfa', 'role__institution__active')))
    claims.append(list(RoleGrant.objects.filter(role__roleassignment__user=user).order_by('pk').values(
        'id', 'resource', 'action', 'allowed')))
    return hashlib.sha256(json.dumps(claims, default=str, sort_keys=True).encode()).hexdigest()

from django.core.exceptions import PermissionDenied, ValidationError
from django.db.models import Q
from django.utils import timezone

DIMENSIONS = {'department', 'grade', 'class', 'section', 'subject', 'academic_year',
              'student', 'employee', 'workflow', 'self'}


def validate_scope(scope):
    if not isinstance(scope, dict) or set(scope) - DIMENSIONS:
        raise ValidationError('Unknown access scope dimension.')
    if any(not isinstance(values, list) or not values or
           any(type(value) is not int or value <= 0 for value in values)
           for values in scope.values()):
        raise ValidationError('Scope values must be nonempty lists of positive identifiers.')


def assignments_for(user, institution_id):
    from .models import RoleAssignment
    now = timezone.now()
    return RoleAssignment.objects.filter(
        user=user, user__is_active=True, role__institution_id=institution_id,
        role__institution__active=True, role__active=True, active=True,
        approved_by__isnull=False, starts_at__lte=now,
    ).filter(Q(ends_at__isnull=True) | Q(ends_at__gt=now)).select_related('role', 'campus')


def scope_matches(assignment, ownership, user):
    try:
        validate_scope(assignment.scope)
        validate_scope(ownership.dimensions)
    except ValidationError:
        return False
    if assignment.approved_by_id == user.pk:
        return False
    if assignment.campus_id and assignment.campus_id != ownership.campus_id:
        return False
    if ownership.campus_id and ownership.campus.institution_id != ownership.institution_id:
        return False
    if assignment.campus_id and assignment.campus.institution_id != ownership.institution_id:
        return False
    for key, values in assignment.scope.items():
        actual = ownership.dimensions.get(key, [])
        if key == 'self':
            actual = [user.pk] if user.pk in actual else []
        if not set(values).intersection(actual):
            return False
    return True


def permitted_assignment(user, action, ownership, *, mfa_verified=False):
    """An allow and its scope must come from the SAME assignment. No superuser bypass."""
    if not user.is_authenticated or not user.is_active:
        return None
    matches = []
    for assignment in assignments_for(user, ownership.institution_id):
        if not scope_matches(assignment, ownership, user):
            continue
        grant = assignment.role.grants.filter(resource=ownership.resource, action=action).first()
        if grant and not grant.allowed:
            return None
        if grant and (not assignment.role.requires_mfa or mfa_verified):
            matches.append(assignment)
    return matches[0] if matches else None


def require_action(user, action, ownership, **context):
    assignment = permitted_assignment(user, action, ownership, **context)
    if assignment is None:
        raise PermissionDenied('This action is not permitted for this record.')
    return assignment


def scoped_queryset(user, action, queryset, institution_id, **context):
    from .models import RecordScope
    # Explicit ownership is mandatory. Unmapped records are inaccessible here.
    resource = queryset.model._meta.label_lower
    owners = RecordScope.objects.filter(institution_id=institution_id, resource=resource).select_related('campus')
    ids = [o.object_id for o in owners if permitted_assignment(user, action, o, **context)]
    return queryset.filter(pk__in=ids)

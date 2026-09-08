import hashlib
import json

from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.utils import timezone

from .models import ApprovalRequest, AuditEvent
from .policy import require_action


def digest(payload):
    return hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()).hexdigest()


@transaction.atomic
def create_request(user, ownership, operation, reviewer, payload, reason, **context):
    assignment = require_action(user, 'create', ownership, **context)
    if reviewer.pk == user.pk or not reviewer.is_active:
        raise ValidationError('An independent active reviewer is required.')
    request = ApprovalRequest(ownership=ownership, operation=operation, maker=user,
                              reviewer=reviewer, payload=payload, payload_hash=digest(payload), reason=reason)
    request.full_clean()
    request.save()
    AuditEvent.objects.create(actor=user, institution=ownership.institution, assignment=assignment,
                              action='workflow.create', resource=ownership.resource,
                              object_id=str(ownership.object_id), outcome='allowed',
                              evidence={'request': request.pk, 'hash': request.payload_hash})
    return request


@transaction.atomic
def transition(user, request_id, action, expected_version, reason='', **context):
    request = ApprovalRequest.objects.select_for_update().select_related('ownership').get(pk=request_id)
    if request.version != expected_version:
        raise ValidationError('The record changed. Reload before continuing.')
    if digest(request.payload) != request.payload_hash:
        raise ValidationError('The submitted content changed and requires a new approval.')
    if action == 'submit':
        if request.maker_id != user.pk or request.status != 'draft':
            raise PermissionDenied('Only the maker may submit a draft.')
        required, target = 'submit', 'submitted'
    elif action in {'approve', 'reject'}:
        if request.maker_id == user.pk or request.reviewer_id != user.pk:
            raise PermissionDenied('Only the assigned independent reviewer may decide.')
        if request.status != 'submitted' or not reason.strip():
            raise ValidationError('A submitted record and decision reason are required.')
        required, target = 'approve', 'approved' if action == 'approve' else 'rejected'
        request.decided_at = timezone.now()
    else:
        raise ValidationError('Unsupported workflow action.')
    assignment = require_action(user, required, request.ownership, **context)
    request.status, request.reason = target, reason
    request.version += 1
    request.save()
    AuditEvent.objects.create(actor=user, institution=request.ownership.institution,
                              assignment=assignment, action='workflow.' + action,
                              resource=request.ownership.resource, object_id=str(request.ownership.object_id),
                              outcome=target, reason=reason,
                              evidence={'request': request.pk, 'version': request.version, 'hash': request.payload_hash})
    return request


@transaction.atomic
def execute(user, request_id, handler, **context):
    """Only a trusted domain service supplies a handler; never dispatch request strings."""
    request = ApprovalRequest.objects.select_for_update().select_related('ownership').get(pk=request_id)
    if request.status == 'executed':
        require_action(user, 'view', request.ownership, **context)
        return request
    assignment = require_action(user, 'publish', request.ownership, **context)
    if request.status != 'approved' or digest(request.payload) != request.payload_hash:
        raise ValidationError('An unchanged approved request is required.')
    if request.maker_id == request.reviewer_id:
        raise PermissionDenied('Self-approved records cannot execute.')
    handler(request)
    request.status, request.executed_at = 'executed', timezone.now()
    request.version += 1
    request.save()
    AuditEvent.objects.create(actor=user, institution=request.ownership.institution, assignment=assignment,
                              action='workflow.execute', resource=request.ownership.resource,
                              object_id=str(request.ownership.object_id), outcome='executed',
                              evidence={'request': request.pk, 'hash': request.payload_hash})
    return request

from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.utils import timezone

from .models import PurchaseRequest


@transaction.atomic
def save_purchase_request(obj, actor):
    original = PurchaseRequest.objects.select_for_update().filter(pk=obj.pk).first() if obj.pk else None
    if original is None:
        if obj.status not in {'draft', 'pending'}:
            raise ValidationError('New requests must start as draft or pending approval.')
        obj.requested_by, obj.approved_by, obj.approved_at = actor, None, None
    else:
        obj.requested_by_id = original.requested_by_id
        obj.approved_by_id, obj.approved_at = original.approved_by_id, original.approved_at
        allowed = {'draft': {'draft', 'pending'}, 'pending': {'pending', 'approved', 'rejected'},
                   'approved': {'approved', 'ordered'}, 'ordered': {'ordered', 'received'},
                   'received': {'received'}, 'rejected': {'rejected', 'draft'}}
        if obj.status not in allowed.get(original.status, set()):
            raise ValidationError('Invalid procurement workflow transition.')
        material_change = any(getattr(obj, field) != getattr(original, field)
                              for field in ('estimated_cost', 'vendor_id', 'category_id', 'description'))
        if original.status in {'approved', 'ordered', 'received'} and material_change:
            raise ValidationError('Approved purchasing details are locked; submit a new request for changes.')
        if obj.status != original.status and obj.status in {'approved', 'rejected'}:
            if not original.requested_by_id or original.requested_by_id == actor.pk:
                raise PermissionDenied('An independent approver is required.')
            if not actor.has_perm('admin_panel.approve_purchaserequest'):
                raise PermissionDenied('You do not have procurement approval permission.')
            obj.approved_by, obj.approved_at = actor, timezone.now()
        if obj.status in {'ordered', 'received'} and not obj.approved_by_id:
            raise ValidationError('A recorded approval is required before ordering or receiving.')
    if obj.status == 'received' and not obj.received_on:
        obj.received_on = timezone.localdate()
    obj.save()
    from access_control.models import AuditEvent
    AuditEvent.objects.create(actor=actor, action='procurement.save', resource='admin_panel.purchaserequest',
                              object_id=str(obj.pk), outcome=obj.status,
                              evidence={'previous_status': original.status if original else None,
                                        'maker': obj.requested_by_id, 'approver': obj.approved_by_id})
    return obj

import json

from django.contrib.auth.decorators import login_required
from django.core.exceptions import ObjectDoesNotExist, ValidationError
from django.http import Http404, JsonResponse
from django.views.decorators.http import require_POST

from .models import ApprovalRequest
from .policy import require_action
from .workflows import transition
from .payments import record_payment
from .mfa import session_verified


def _body(request):
    try:
        data = json.loads(request.body)
        if not isinstance(data, dict):
            raise ValueError
        return data
    except (ValueError, UnicodeError):
        raise ValidationError('A JSON object is required.')


@login_required
@require_POST
def approval_decision(request, pk):
    try:
        item = ApprovalRequest.objects.select_related('ownership').get(pk=pk)
        require_action(request.user, 'view', item.ownership, mfa_verified=session_verified(request))
        data = _body(request)
        version = data.get('version')
        if type(version) is not int:
            raise ValidationError('The current integer version is required.')
        result = transition(request.user, pk, data.get('action'), version, str(data.get('reason', '')),
                            mfa_verified=session_verified(request))
        return JsonResponse({'id': result.pk, 'status': result.status, 'version': result.version})
    except ObjectDoesNotExist:
        raise Http404
    except ValidationError as exc:
        return JsonResponse({'errors': exc.messages}, status=400)


@login_required
@require_POST
def payment_receipt(request, voucher_id):
    try:
        data = _body(request)
        result = record_payment(request.user, voucher_id, data.get('amount'),
                                data.get('reference'), data.get('method', 'CASH'), mfa_verified=session_verified(request))
        return JsonResponse({'id': result.pk, 'reference': result.reference, 'amount': str(result.amount)})
    except ObjectDoesNotExist:
        raise Http404
    except ValidationError as exc:
        return JsonResponse({'errors': exc.messages}, status=400)

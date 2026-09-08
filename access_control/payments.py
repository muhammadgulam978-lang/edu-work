"""Verified manual receipt posting. Gateway adapters must verify callbacks first."""
from decimal import Decimal, InvalidOperation

from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Sum

from .models import AuditEvent, PaymentReceipt, RecordScope
from .policy import require_action


@transaction.atomic
def record_payment(user, voucher_id, amount, reference, method='CASH', **context):
    from edupilot_core.models import FeeVoucher, StudentBalance, StudentLedger
    if method not in {'CASH', 'CHEQUE', 'BANK'}:
        raise ValidationError('This endpoint records verified finance receipts, not gateway callbacks.')
    if not isinstance(reference, str) or not reference.strip() or len(reference) > 100:
        raise ValidationError('A unique bank or receipt reference is required.')
    try:
        amount = Decimal(str(amount))
    except (InvalidOperation, TypeError, ValueError):
        raise ValidationError('Invalid payment amount.')
    if not amount.is_finite() or amount <= 0 or amount.as_tuple().exponent < -2:
        raise ValidationError('Use a positive amount with at most two decimal places.')
    owner = RecordScope.objects.get(resource='edupilot_core.feevoucher', object_id=voucher_id)
    assignment = require_action(user, 'edit', owner, **context)
    voucher = FeeVoucher.objects.select_for_update().get(pk=voucher_id)
    reference = reference.strip()
    existing = PaymentReceipt.objects.filter(reference=reference).first()
    if existing:
        if existing.voucher_id != voucher.pk or existing.amount != amount or existing.method != method:
            raise ValidationError('This reference has already been used for a different payment.')
        return existing
    received = voucher.verified_receipts.aggregate(total=Sum('amount'))['total'] or Decimal('0')
    if voucher.status in {'PAID', 'PARTIAL'} and received == 0:
        raise ValidationError('Reconcile historical payments before posting another receipt.')
    if amount > voucher.net_amount - received:
        raise ValidationError('Payment exceeds the remaining voucher amount.')
    # The one-to-one balance exists from voucher generation; do not invent a zero balance.
    balance = StudentBalance.objects.select_for_update().get(student_id=voucher.student_id)
    if balance.outstanding_amount < amount:
        raise ValidationError('Reconcile the student balance before posting this payment.')
    receipt = PaymentReceipt.objects.create(voucher=voucher, amount=amount, reference=reference,
                                            method=method, recorded_by=user)
    balance.outstanding_amount -= amount
    balance.save(update_fields=['outstanding_amount'])
    voucher.status = 'PAID' if received + amount == voucher.net_amount else 'PARTIAL'
    voucher.save(update_fields=['status'])
    StudentLedger.objects.create(student_id=voucher.student_id, canonical_student_id=voucher.canonical_student_id,
                                  description=f'Payment received for {voucher.voucher_no}', credit=amount,
                                  balance=balance.outstanding_amount, reference_no=reference[:50])
    AuditEvent.objects.create(actor=user, institution=owner.institution, assignment=assignment,
                              action='payment.record', resource=owner.resource, object_id=str(voucher.pk),
                              outcome='posted', evidence={'receipt': receipt.pk, 'amount': str(amount)})
    return receipt

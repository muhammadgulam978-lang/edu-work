import logging

from django.db.models.signals import post_save
from django.dispatch import receiver

from edupilot_core.models import FeeVoucher, SalaryVoucher, StudentLedger
from admin_panel.models import PurchaseRequest

from .integrations import (post_fee_invoice, post_purchase_receipt, post_salary_accrual,
                           post_salary_payment, post_student_payment, post_student_refund)

logger = logging.getLogger(__name__)


def _safe_post(callback, instance):
    try:
        callback(instance)
    except Exception:
        logger.exception('Finance posting failed for %s:%s', instance._meta.label, instance.pk)


@receiver(post_save, sender=FeeVoucher, dispatch_uid='finance_fee_invoice_posting')
def fee_invoice_posting(sender, instance, created, **kwargs):
    if created:
        _safe_post(post_fee_invoice, instance)


@receiver(post_save, sender=StudentLedger, dispatch_uid='finance_student_payment_posting')
def student_payment_posting(sender, instance, created, **kwargs):
    if created:
        if instance.credit:
            _safe_post(post_student_payment, instance)
        elif instance.debit:
            _safe_post(post_student_refund, instance)


@receiver(post_save, sender=SalaryVoucher, dispatch_uid='finance_salary_accrual_posting')
def salary_accrual_posting(sender, instance, created, **kwargs):
    if created:
        _safe_post(post_salary_accrual, instance)
    if instance.status.upper() == 'PAID':
        _safe_post(post_salary_payment, instance)


@receiver(post_save, sender=PurchaseRequest, dispatch_uid='finance_purchase_receipt_posting')
def purchase_receipt_posting(sender, instance, **kwargs):
    if instance.status == 'received':
        _safe_post(post_purchase_receipt, instance)

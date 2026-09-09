from django.core.management.base import BaseCommand

from admin_panel.models import PurchaseRequest
from edupilot_core.models import FeeVoucher, SalaryVoucher, StudentLedger
from finance.integrations import (post_fee_invoice, post_purchase_receipt, post_salary_accrual,
                                  post_salary_payment, post_student_payment, post_student_refund)


class Command(BaseCommand):
    help = 'Idempotently post existing fee, payment, refund, payroll and procurement records to the General Ledger.'

    def handle(self, *args, **options):
        posted, failed = 0, 0
        callbacks = [
            (FeeVoucher.objects.all().iterator(), post_fee_invoice),
            (StudentLedger.objects.filter(credit__gt=0).iterator(), post_student_payment),
            (StudentLedger.objects.filter(debit__gt=0, description__icontains='refund').iterator(), post_student_refund),
            (SalaryVoucher.objects.all().iterator(), post_salary_accrual),
            (SalaryVoucher.objects.filter(status__iexact='PAID').iterator(), post_salary_payment),
            (PurchaseRequest.objects.filter(status='received').iterator(), post_purchase_receipt),
        ]
        for records, callback in callbacks:
            for record in records:
                try:
                    if callback(record):
                        posted += 1
                except Exception as exc:
                    failed += 1
                    self.stderr.write(f'{record._meta.label} #{record.pk}: {exc}')
        message = f'Finance ledger synchronized. {posted} source records verified; {failed} failed.'
        self.stdout.write(self.style.SUCCESS(message) if not failed else self.style.WARNING(message))

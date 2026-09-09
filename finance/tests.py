from datetime import date
from decimal import Decimal

from django.contrib.auth.models import User
from django.core.exceptions import PermissionDenied, ValidationError
from django.test import TestCase
from django.urls import reverse

from .models import (Account, AccountingPeriod, FinanceAuditEvent, FinanceRequest,
                     FinancialYear, VoucherLine)
from .services import approve_voucher, create_voucher, post_voucher, reverse_voucher, submit_voucher


class LedgerServiceTests(TestCase):
    def setUp(self):
        self.maker = User.objects.create_user('maker', password='TestPass@123')
        self.approver = User.objects.create_superuser('approver', 'approver@example.com', 'TestPass@123')
        self.year = FinancialYear.objects.create(name='2026-27', starts_on=date(2026, 7, 1), ends_on=date(2027, 6, 30))
        self.period = AccountingPeriod.objects.create(financial_year=self.year, name='September 2026',
                                                       starts_on=date(2026, 9, 1), ends_on=date(2026, 9, 30))
        self.cash = Account.objects.create(code='1010-T', name='Cash', account_type='ASSET', normal_balance='DEBIT')
        self.income = Account.objects.create(code='4100-T', name='Income', account_type='INCOME', normal_balance='CREDIT')

    def voucher(self, source='1'):
        return create_voucher(
            voucher_type='RV', narration='Test receipt', maker=self.maker,
            voucher_date=date(2026, 9, 9), source_module='test', source_model='Receipt', source_id=source,
            lines=[
                {'account': self.cash, 'debit': Decimal('100.00'), 'credit': 0},
                {'account': self.income, 'debit': 0, 'credit': Decimal('100.00')},
            ],
        )

    def test_balanced_voucher_posts_and_reverses(self):
        voucher = self.voucher()
        submit_voucher(voucher, self.maker)
        posted = approve_voucher(voucher, self.approver)
        self.assertEqual(posted.status, 'POSTED')
        self.assertEqual(posted.total_debit, posted.total_credit)
        reversal = reverse_voucher(posted, self.approver, 'Incorrect receipt')
        posted.refresh_from_db()
        self.assertEqual(posted.status, 'REVERSED')
        self.assertEqual(reversal.status, 'POSTED')
        self.assertEqual(reversal.total_debit, Decimal('100.00'))
        self.assertTrue(FinanceAuditEvent.objects.filter(voucher=posted, action='REVERSED').exists())

    def test_unbalanced_and_invalid_lines_are_rejected(self):
        with self.assertRaises(ValidationError):
            create_voucher(voucher_type='JV', narration='Bad', maker=self.maker,
                           voucher_date=date(2026, 9, 9),
                           lines=[{'account': self.cash, 'debit': 100, 'credit': 0},
                                  {'account': self.income, 'debit': 0, 'credit': 90}])
        with self.assertRaises(ValidationError):
            create_voucher(voucher_type='JV', narration='Bad line', maker=self.maker,
                           voucher_date=date(2026, 9, 9),
                           lines=[{'account': self.cash, 'debit': 100, 'credit': 100},
                                  {'account': self.income, 'debit': 0, 'credit': 100}])

    def test_source_id_is_idempotent(self):
        first = self.voucher('same')
        second = self.voucher('same')
        self.assertEqual(first.pk, second.pk)
        self.assertEqual(first.lines.count(), 2)

    def test_maker_cannot_approve_and_locked_period_cannot_post(self):
        voucher = self.voucher()
        submit_voucher(voucher, self.maker)
        with self.assertRaises(PermissionDenied):
            approve_voucher(voucher, self.maker)
        self.period.status = 'LOCKED'
        self.period.save()
        voucher.status = 'APPROVED'
        voucher.save(update_fields=['status', 'updated_at'])
        with self.assertRaises(ValidationError):
            post_voucher(voucher, self.approver)

    def test_posted_voucher_and_lines_are_immutable(self):
        voucher = self.voucher()
        submit_voucher(voucher, self.maker)
        voucher = approve_voucher(voucher, self.approver)
        voucher.narration = 'Changed'
        with self.assertRaises(ValidationError):
            voucher.save()
        line = voucher.lines.first()
        line.description = 'Changed'
        with self.assertRaises(ValidationError):
            line.save()
        with self.assertRaises(ValidationError):
            line.delete()

    def test_soft_closed_period_rejects_new_entries(self):
        self.period.status = 'SOFT_CLOSED'
        self.period.save(update_fields=['status', 'updated_at'])
        with self.assertRaises(ValidationError):
            self.voucher('closed')


class FinanceScreenTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_superuser('finance.admin', 'finance@example.com', 'TestPass@123')
        self.client.force_login(self.admin)

    def test_real_application_screens_render(self):
        for name in ('finance:dashboard', 'finance:setup', 'finance:voucher_list',
                     'finance:voucher_create', 'finance:reports', 'finance:audit',
                     'finance:cash_sessions', 'finance:bank_reconciliation', 'finance:budgets',
                     'finance:request_list'):
            response = self.client.get(reverse(name))
            self.assertEqual(response.status_code, 200, name)

    def test_ordinary_user_cannot_open_finance_back_office(self):
        user = User.objects.create_user('ordinary', password='TestPass@123')
        self.client.force_login(user)
        self.assertEqual(self.client.get(reverse('finance:dashboard')).status_code, 403)

    def test_request_approval_posts_balanced_adjustment(self):
        requester = User.objects.create_user('requester', password='TestPass@123')
        item = FinanceRequest.objects.create(request_type='REIMBURSEMENT', requested_by=requester,
                                             amount=Decimal('2500.00'), reason='Approved supplies')
        response = self.client.post(reverse('finance:request_action', args=[item.pk, 'approve']))
        self.assertEqual(response.status_code, 302)
        item.refresh_from_db()
        self.assertEqual(item.status, 'APPROVED')
        self.assertEqual(item.linked_voucher.status, 'POSTED')
        self.assertTrue(item.linked_voucher.is_balanced)

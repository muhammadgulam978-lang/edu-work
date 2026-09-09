from decimal import Decimal
from datetime import date
from calendar import month_name

from .services import create_voucher, ensure_default_chart, post_voucher


def _salary_date(salary_voucher):
    month = next((index for index, name in enumerate(month_name) if name.lower() == salary_voucher.month.lower()), 1)
    return date(salary_voucher.year, month, 1)


def post_fee_invoice(fee_voucher, actor=None):
    accounts = ensure_default_chart()
    student = fee_voucher.canonical_student or getattr(fee_voucher.student, 'canonical_student', None)
    voucher = create_voucher(
        voucher_type='JV', narration=f'Fee invoice {fee_voucher.voucher_no}', maker=actor,
        voucher_date=fee_voucher.issue_date, source_module='edupilot_core',
        source_model='FeeVoucher', source_id=fee_voucher.pk, source_reference=fee_voucher.voucher_no,
        campus=getattr(fee_voucher.student, 'campus', ''),
        lines=[
            {'account': accounts['1100'], 'debit': fee_voucher.net_amount, 'credit': 0, 'student': student,
             'description': 'Student fee receivable'},
            {'account': accounts['4100'], 'debit': 0, 'credit': fee_voucher.net_amount, 'student': student,
             'description': 'Fee income'},
        ],
    )
    return post_voucher(voucher, actor, system=True)


def post_student_payment(ledger_entry, actor=None):
    if not ledger_entry.credit or 'payment' not in ledger_entry.description.lower():
        return None
    accounts = ensure_default_chart()
    student = ledger_entry.canonical_student or getattr(ledger_entry.student, 'canonical_student', None)
    amount = Decimal(str(ledger_entry.credit))
    voucher = create_voucher(
        voucher_type='RV', narration=ledger_entry.description, maker=actor,
        voucher_date=ledger_entry.date, source_module='edupilot_core', source_model='StudentLedgerPayment',
        source_id=ledger_entry.pk, source_reference=ledger_entry.reference_no or '',
        campus=getattr(ledger_entry.student, 'campus', ''),
        lines=[
            {'account': accounts['1010'], 'debit': amount, 'credit': 0, 'student': student, 'description': 'Payment received'},
            {'account': accounts['1100'], 'debit': 0, 'credit': amount, 'student': student, 'description': 'Receivable settled'},
        ],
    )
    return post_voucher(voucher, actor, system=True)


def post_student_refund(ledger_entry, actor=None):
    if not ledger_entry.debit or 'refund' not in ledger_entry.description.lower():
        return None
    accounts = ensure_default_chart()
    student = ledger_entry.canonical_student or getattr(ledger_entry.student, 'canonical_student', None)
    amount = Decimal(str(ledger_entry.debit))
    voucher = create_voucher(
        voucher_type='CN', narration=ledger_entry.description, maker=actor,
        voucher_date=ledger_entry.date, source_module='edupilot_core', source_model='StudentLedgerRefund',
        source_id=ledger_entry.pk, source_reference=ledger_entry.reference_no or '',
        campus=getattr(ledger_entry.student, 'campus', ''),
        lines=[
            {'account': accounts['5300'], 'debit': amount, 'credit': 0, 'student': student,
             'description': 'Approved fee refund'},
            {'account': accounts['1010'], 'debit': 0, 'credit': amount, 'student': student,
             'description': 'Refund paid'},
        ],
    )
    return post_voucher(voucher, actor, system=True)


def post_salary_accrual(salary_voucher, actor=None):
    accounts = ensure_default_chart()
    teacher = salary_voucher.canonical_teacher or getattr(salary_voucher.teacher, 'canonical_teacher', None)
    amount = Decimal(str(salary_voucher.net_salary))
    voucher = create_voucher(
        voucher_type='JV', narration=f'Salary {salary_voucher.month} {salary_voucher.year}', maker=actor,
        voucher_date=_salary_date(salary_voucher),
        source_module='edupilot_core', source_model='SalaryVoucher', source_id=salary_voucher.pk,
        source_reference=f'SAL-{salary_voucher.year}-{salary_voucher.month}-{salary_voucher.pk}',
        lines=[
            {'account': accounts['5100'], 'debit': amount, 'credit': 0, 'teacher': teacher, 'description': 'Salary expense'},
            {'account': accounts['2200'], 'debit': 0, 'credit': amount, 'teacher': teacher, 'description': 'Salary payable'},
        ],
    )
    return post_voucher(voucher, actor, system=True)


def post_salary_payment(salary_voucher, actor=None):
    if salary_voucher.status.upper() != 'PAID':
        return None
    accounts = ensure_default_chart()
    teacher = salary_voucher.canonical_teacher or getattr(salary_voucher.teacher, 'canonical_teacher', None)
    amount = Decimal(str(salary_voucher.net_salary))
    voucher = create_voucher(
        voucher_type='PV', narration=f'Salary payment {salary_voucher.month} {salary_voucher.year}', maker=actor,
        voucher_date=_salary_date(salary_voucher),
        source_module='edupilot_core', source_model='SalaryVoucherPayment', source_id=salary_voucher.pk,
        source_reference=f'SAL-PAY-{salary_voucher.year}-{salary_voucher.month}-{salary_voucher.pk}',
        lines=[
            {'account': accounts['2200'], 'debit': amount, 'credit': 0, 'teacher': teacher,
             'description': 'Salary payable settled'},
            {'account': accounts['1020'], 'debit': 0, 'credit': amount, 'teacher': teacher,
             'description': 'Salary paid from bank'},
        ],
    )
    return post_voucher(voucher, actor, system=True)


def post_purchase_receipt(purchase, actor=None):
    if purchase.status != 'received' or not purchase.estimated_cost:
        return None
    accounts = ensure_default_chart()
    amount = Decimal(str(purchase.estimated_cost))
    voucher = create_voucher(
        voucher_type='JV', narration=f'Purchase received: {purchase.title}', maker=actor,
        voucher_date=purchase.received_on, source_module='admin_panel', source_model='PurchaseRequest',
        source_id=purchase.pk, source_reference=f'PUR-{purchase.pk}',
        lines=[
            {'account': accounts['5200'], 'debit': amount, 'credit': 0, 'vendor': purchase.vendor,
             'description': purchase.title},
            {'account': accounts['2100'], 'debit': 0, 'credit': amount, 'vendor': purchase.vendor,
             'description': 'Vendor payable'},
        ],
    )
    return post_voucher(voucher, actor, system=True)

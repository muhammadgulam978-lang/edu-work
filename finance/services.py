from calendar import monthrange
from datetime import date
from decimal import Decimal

from django.contrib.auth.models import Group
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import IntegrityError, transaction
from django.db.models import Q, Sum
from django.utils import timezone

from .models import (
    Account, AccountingPeriod, ApprovalDecision, ApprovalRule, FinanceAuditEvent,
    FinancialYear, Voucher, VoucherLine,
)


DEFAULT_ACCOUNTS = [
    ('1000', 'Assets', 'ASSET', 'DEBIT', False),
    ('1010', 'Cash in Hand', 'ASSET', 'DEBIT', True),
    ('1020', 'Bank', 'ASSET', 'DEBIT', True),
    ('1100', 'Student Receivables', 'ASSET', 'DEBIT', True),
    ('1200', 'Staff Advances', 'ASSET', 'DEBIT', True),
    ('2000', 'Liabilities', 'LIABILITY', 'CREDIT', False),
    ('2100', 'Vendor Payables', 'LIABILITY', 'CREDIT', True),
    ('2200', 'Salary Payable', 'LIABILITY', 'CREDIT', True),
    ('2210', 'Tax Payable', 'LIABILITY', 'CREDIT', True),
    ('2300', 'Student Advances', 'LIABILITY', 'CREDIT', True),
    ('3000', 'Funds and Equity', 'EQUITY', 'CREDIT', False),
    ('4000', 'Income', 'INCOME', 'CREDIT', False),
    ('4100', 'Tuition Fee Income', 'INCOME', 'CREDIT', True),
    ('4110', 'Admission Fee Income', 'INCOME', 'CREDIT', True),
    ('4120', 'Transport Fee Income', 'INCOME', 'CREDIT', True),
    ('4190', 'Other Fee Income', 'INCOME', 'CREDIT', True),
    ('5000', 'Expenses', 'EXPENSE', 'DEBIT', False),
    ('5100', 'Salary Expense', 'EXPENSE', 'DEBIT', True),
    ('5200', 'Operating Expense', 'EXPENSE', 'DEBIT', True),
    ('5300', 'Fee Concessions and Refunds', 'EXPENSE', 'DEBIT', True),
]


def _year_for(day):
    start_year = day.year if day.month >= 7 else day.year - 1
    starts = date(start_year, 7, 1)
    ends = date(start_year + 1, 6, 30)
    year, _ = FinancialYear.objects.get_or_create(
        name=f'{start_year}-{str(start_year + 1)[-2:]}',
        defaults={'starts_on': starts, 'ends_on': ends, 'is_active': True},
    )
    return year


def period_for(day=None):
    day = day or timezone.localdate()
    period = AccountingPeriod.objects.filter(starts_on__lte=day, ends_on__gte=day).first()
    if period:
        return period
    year = _year_for(day)
    last = monthrange(day.year, day.month)[1]
    period, _ = AccountingPeriod.objects.get_or_create(
        financial_year=year, name=day.strftime('%B %Y'),
        defaults={'starts_on': day.replace(day=1), 'ends_on': day.replace(day=last)},
    )
    return period


def ensure_default_chart():
    accounts = {}
    parent_by_prefix = {'1': None, '2': None, '3': None, '4': None, '5': None}
    for code, name, account_type, normal, postable in DEFAULT_ACCOUNTS:
        parent = parent_by_prefix[code[0]] if code[-3:] != '000' else None
        account, _ = Account.objects.get_or_create(
            code=code,
            defaults={'name': name, 'account_type': account_type, 'normal_balance': normal,
                      'parent': parent, 'allow_direct_posting': postable,
                      'is_control_account': not postable},
        )
        if code[-3:] == '000':
            parent_by_prefix[code[0]] = account
        accounts[code] = account
    return accounts


def next_voucher_number(voucher_type, day=None):
    day = day or timezone.localdate()
    prefix = f'{voucher_type}-{day:%Y%m}'
    last = Voucher.objects.filter(number__startswith=prefix).order_by('-number').values_list('number', flat=True).first()
    sequence = int(last.rsplit('-', 1)[-1]) + 1 if last else 1
    return f'{prefix}-{sequence:06d}'


def _audit(voucher, actor, action, **details):
    FinanceAuditEvent.objects.create(voucher=voucher, actor=actor if getattr(actor, 'pk', None) else None,
                                     action=action, details=details)


def _assert_mutable(voucher):
    if voucher.status in {'POSTED', 'REVERSED'}:
        raise ValidationError('Posted vouchers are immutable. Use a reversal voucher.')


def _recalculate(voucher):
    totals = voucher.lines.aggregate(debit=Sum('debit'), credit=Sum('credit'))
    voucher.total_debit = totals['debit'] or Decimal('0.00')
    voucher.total_credit = totals['credit'] or Decimal('0.00')
    voucher.save(update_fields=['total_debit', 'total_credit', 'updated_at'])
    if not voucher.is_balanced:
        raise ValidationError('Voucher debit and credit totals must be equal and greater than zero.')


@transaction.atomic
def create_voucher(*, voucher_type, narration, lines, maker=None, voucher_date=None,
                   source_module='', source_model='', source_id='', source_reference='',
                   campus='', branch='', cost_center=None, auto_submit=False):
    voucher_date = voucher_date or timezone.localdate()
    period = period_for(voucher_date)
    if period.status != 'OPEN' or period.financial_year.status != 'OPEN':
        raise ValidationError('The selected accounting period is closed for new entries.')
    if source_id:
        existing = Voucher.objects.filter(source_module=source_module, source_model=source_model, source_id=str(source_id)).first()
        if existing:
            return existing
    voucher = None
    for _ in range(5):
        try:
            with transaction.atomic():
                voucher = Voucher.objects.create(
                    number=next_voucher_number(voucher_type, voucher_date), voucher_type=voucher_type,
                    voucher_date=voucher_date, period=period, narration=narration, maker=maker,
                    source_module=source_module, source_model=source_model, source_id=str(source_id or ''),
                    source_reference=source_reference, campus=campus, branch=branch, cost_center=cost_center,
                )
            break
        except IntegrityError:
            if source_id:
                existing = Voucher.objects.filter(source_module=source_module, source_model=source_model,
                                                  source_id=str(source_id)).first()
                if existing:
                    return existing
    if voucher is None:
        raise ValidationError('Could not allocate a unique voucher number. Please retry.')
    for entry in lines:
        line = VoucherLine(voucher=voucher, **entry)
        line.full_clean()
        line.save()
    _recalculate(voucher)
    _audit(voucher, maker, 'CREATED', source_reference=source_reference)
    if auto_submit:
        submit_voucher(voucher, maker)
    return voucher


@transaction.atomic
def submit_voucher(voucher, actor, comment=''):
    voucher = Voucher.objects.select_for_update().get(pk=voucher.pk)
    _assert_mutable(voucher)
    if voucher.status != 'DRAFT':
        raise ValidationError('Only draft vouchers can be submitted.')
    _recalculate(voucher)
    voucher.status = 'SUBMITTED'
    voucher.submitted_at = timezone.now()
    voucher.save(update_fields=['status', 'submitted_at', 'updated_at'])
    ApprovalDecision.objects.create(voucher=voucher, actor=actor, action='SUBMITTED', comment=comment)
    _audit(voucher, actor, 'SUBMITTED', comment=comment)
    return voucher


def required_approval_rules(voucher):
    rules = ApprovalRule.objects.filter(is_active=True, minimum_amount__lte=voucher.total_debit)
    rules = rules.filter(voucher_type__in=['', voucher.voucher_type])
    if voucher.campus:
        rules = rules.filter(campus__in=['', voucher.campus])
    department = voucher.cost_center.department if voucher.cost_center_id else ''
    rules = rules.filter(department__in=['', department]) if department else rules.filter(department='')
    rules = rules.filter(Q(maximum_amount__isnull=True) | Q(maximum_amount__gte=voucher.total_debit))
    return list(rules.order_by('sequence'))


@transaction.atomic
def approve_voucher(voucher, actor, comment='', auto_post=True):
    voucher = Voucher.objects.select_for_update().get(pk=voucher.pk)
    if voucher.status not in {'SUBMITTED', 'UNDER_REVIEW'}:
        raise ValidationError('Only submitted vouchers can be approved.')
    if voucher.maker_id == actor.pk:
        raise PermissionDenied('The maker cannot approve their own voucher.')
    rules = required_approval_rules(voucher)
    approvals = voucher.decisions.filter(action='APPROVED').count()
    if rules:
        rule = rules[min(approvals, len(rules) - 1)]
        if not (actor.is_superuser or actor.groups.filter(pk=rule.required_group_id).exists()):
            raise PermissionDenied(f'Approval requires membership in {rule.required_group.name}.')
    elif not (actor.is_superuser or actor.has_perm('finance.approve_voucher')):
        raise PermissionDenied('You do not have voucher approval permission.')
    sequence = approvals + 1
    ApprovalDecision.objects.create(voucher=voucher, actor=actor, action='APPROVED', sequence=sequence, comment=comment)
    if rules and sequence < len(rules):
        voucher.status = 'UNDER_REVIEW'
        voucher.save(update_fields=['status', 'updated_at'])
        _audit(voucher, actor, 'APPROVAL_STEP', sequence=sequence, comment=comment)
        return voucher
    voucher.status = 'APPROVED'
    voucher.approved_by = actor
    voucher.approved_at = timezone.now()
    voucher.save(update_fields=['status', 'approved_by', 'approved_at', 'updated_at'])
    _audit(voucher, actor, 'APPROVED', comment=comment)
    return post_voucher(voucher, actor) if auto_post else voucher


@transaction.atomic
def post_voucher(voucher, actor=None, system=False):
    voucher = Voucher.objects.select_for_update().select_related('period__financial_year').get(pk=voucher.pk)
    if voucher.status == 'POSTED':
        return voucher
    if voucher.status not in ({'APPROVED'} if not system else {'DRAFT', 'SUBMITTED', 'APPROVED'}):
        raise ValidationError('Voucher must be approved before posting.')
    if voucher.period.status != 'OPEN' or voucher.period.financial_year.status != 'OPEN':
        raise ValidationError('The accounting period is closed for posting.')
    _recalculate(voucher)
    voucher.status = 'POSTED'
    voucher.posted_by = actor
    voucher.posted_at = timezone.now()
    voucher.save(update_fields=['status', 'posted_by', 'posted_at', 'updated_at'])
    if actor:
        ApprovalDecision.objects.create(voucher=voucher, actor=actor, action='POSTED')
    _audit(voucher, actor, 'POSTED', total=str(voucher.total_debit), system=system)
    return voucher


@transaction.atomic
def reverse_voucher(voucher, actor, reason):
    original = Voucher.objects.select_for_update().get(pk=voucher.pk)
    if original.status != 'POSTED':
        raise ValidationError('Only posted vouchers can be reversed.')
    if not reason.strip():
        raise ValidationError('A reversal reason is required.')
    reversal = create_voucher(
        voucher_type='JV', narration=f'Reversal of {original.number}: {reason}', maker=actor,
        voucher_date=timezone.localdate(), source_module='finance', source_model='VoucherReversal',
        source_id=str(original.pk), source_reference=original.number,
        campus=original.campus, branch=original.branch, cost_center=original.cost_center,
        lines=[{'account': line.account, 'debit': line.credit, 'credit': line.debit,
                'description': f'Reversal: {line.description}', 'student': line.student,
                'teacher': line.teacher, 'vendor': line.vendor, 'cost_center': line.cost_center}
               for line in original.lines.select_related('account')],
    )
    reversal = post_voucher(reversal, actor, system=True)
    original.status = 'REVERSED'
    original.reversed_by = reversal
    original.save(update_fields=['status', 'reversed_by', 'updated_at'])
    ApprovalDecision.objects.create(voucher=original, actor=actor, action='REVERSED', comment=reason)
    _audit(original, actor, 'REVERSED', reversal=reversal.number, reason=reason)
    return reversal


def reject_voucher(voucher, actor, comment):
    if voucher.maker_id == actor.pk:
        raise PermissionDenied('The maker cannot reject their own submitted voucher.')
    if not comment.strip():
        raise ValidationError('A rejection reason is required.')
    voucher.status = 'REJECTED'
    voucher.save(update_fields=['status', 'updated_at'])
    ApprovalDecision.objects.create(voucher=voucher, actor=actor, action='REJECTED', comment=comment)
    _audit(voucher, actor, 'REJECTED', comment=comment)
    return voucher


def account_balance(account, through=None):
    lines = account.voucher_lines.filter(voucher__status='POSTED')
    if through:
        lines = lines.filter(voucher__voucher_date__lte=through)
    totals = lines.aggregate(debit=Sum('debit'), credit=Sum('credit'))
    debit, credit = totals['debit'] or Decimal('0'), totals['credit'] or Decimal('0')
    return debit - credit if account.normal_balance == 'DEBIT' else credit - debit

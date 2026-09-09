from decimal import Decimal

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q
from django.utils import timezone


class TimeStampedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class FinancialYear(TimeStampedModel):
    STATUS = [('OPEN', 'Open'), ('SOFT_CLOSED', 'Soft closed'), ('LOCKED', 'Locked')]
    name = models.CharField(max_length=30, unique=True)
    starts_on = models.DateField()
    ends_on = models.DateField()
    status = models.CharField(max_length=15, choices=STATUS, default='OPEN')
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['-starts_on']

    def clean(self):
        if self.ends_on <= self.starts_on:
            raise ValidationError('Financial year end date must be after its start date.')

    def __str__(self):
        return self.name


class AccountingPeriod(TimeStampedModel):
    STATUS = [('OPEN', 'Open'), ('SOFT_CLOSED', 'Soft closed'), ('LOCKED', 'Locked')]
    financial_year = models.ForeignKey(FinancialYear, on_delete=models.PROTECT, related_name='periods')
    name = models.CharField(max_length=30)
    starts_on = models.DateField()
    ends_on = models.DateField()
    status = models.CharField(max_length=15, choices=STATUS, default='OPEN')

    class Meta:
        ordering = ['starts_on']
        constraints = [models.UniqueConstraint(fields=['financial_year', 'name'], name='finance_unique_period_name')]

    def clean(self):
        if self.ends_on < self.starts_on:
            raise ValidationError('Period end date cannot be before its start date.')
        if self.starts_on < self.financial_year.starts_on or self.ends_on > self.financial_year.ends_on:
            raise ValidationError('Period must be inside its financial year.')
        overlap = AccountingPeriod.objects.filter(starts_on__lte=self.ends_on, ends_on__gte=self.starts_on).exclude(pk=self.pk)
        if overlap.exists():
            raise ValidationError('Accounting periods cannot overlap.')

    def __str__(self):
        return f'{self.financial_year.name} - {self.name}'


class CostCenter(TimeStampedModel):
    code = models.CharField(max_length=30, unique=True)
    name = models.CharField(max_length=120)
    campus = models.CharField(max_length=120, blank=True)
    branch = models.CharField(max_length=120, blank=True)
    department = models.CharField(max_length=120, blank=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f'{self.code} - {self.name}'


class Account(TimeStampedModel):
    TYPES = [('ASSET', 'Asset'), ('LIABILITY', 'Liability'), ('INCOME', 'Income'),
             ('EXPENSE', 'Expense'), ('EQUITY', 'Equity / Fund')]
    BALANCES = [('DEBIT', 'Debit'), ('CREDIT', 'Credit')]
    code = models.CharField(max_length=30, unique=True)
    name = models.CharField(max_length=150)
    account_type = models.CharField(max_length=12, choices=TYPES)
    normal_balance = models.CharField(max_length=6, choices=BALANCES)
    parent = models.ForeignKey('self', null=True, blank=True, on_delete=models.PROTECT, related_name='children')
    campus = models.CharField(max_length=120, blank=True)
    tax_treatment = models.CharField(max_length=80, blank=True)
    is_control_account = models.BooleanField(default=False)
    allow_direct_posting = models.BooleanField(default=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['code']

    def clean(self):
        if self.parent_id and self.parent_id == self.pk:
            raise ValidationError('An account cannot be its own parent.')

    def __str__(self):
        return f'{self.code} - {self.name}'


class CashBankAccount(TimeStampedModel):
    TYPES = [('CASH', 'Cash counter'), ('BANK', 'Bank account'), ('WALLET', 'Digital wallet')]
    name = models.CharField(max_length=120)
    account_type = models.CharField(max_length=10, choices=TYPES)
    ledger_account = models.OneToOneField(Account, on_delete=models.PROTECT, related_name='cash_bank_profile')
    account_number_masked = models.CharField(max_length=80, blank=True)
    campus = models.CharField(max_length=120, blank=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.name


class Voucher(TimeStampedModel):
    TYPES = [('RV', 'Receipt Voucher'), ('PV', 'Payment Voucher'), ('JV', 'Journal Voucher'),
             ('CV', 'Contra Voucher'), ('CN', 'Credit Note'), ('DN', 'Debit Note')]
    STATUS = [('DRAFT', 'Draft'), ('SUBMITTED', 'Submitted'), ('UNDER_REVIEW', 'Under review'),
              ('APPROVED', 'Approved'), ('POSTED', 'Posted'), ('REJECTED', 'Rejected'),
              ('CANCELLED', 'Cancelled'), ('REVERSED', 'Reversed')]
    number = models.CharField(max_length=50, unique=True)
    voucher_type = models.CharField(max_length=2, choices=TYPES)
    voucher_date = models.DateField(default=timezone.localdate)
    period = models.ForeignKey(AccountingPeriod, on_delete=models.PROTECT, related_name='vouchers')
    status = models.CharField(max_length=15, choices=STATUS, default='DRAFT')
    narration = models.TextField()
    campus = models.CharField(max_length=120, blank=True)
    branch = models.CharField(max_length=120, blank=True)
    cost_center = models.ForeignKey(CostCenter, null=True, blank=True, on_delete=models.PROTECT)
    source_module = models.CharField(max_length=80, blank=True)
    source_model = models.CharField(max_length=80, blank=True)
    source_id = models.CharField(max_length=100, blank=True)
    source_reference = models.CharField(max_length=160, blank=True, db_index=True)
    currency = models.CharField(max_length=3, default='PKR')
    total_debit = models.DecimalField(max_digits=18, decimal_places=2, default=0)
    total_credit = models.DecimalField(max_digits=18, decimal_places=2, default=0)
    maker = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.PROTECT, related_name='finance_vouchers_made')
    submitted_at = models.DateTimeField(null=True, blank=True)
    approved_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.PROTECT, related_name='finance_vouchers_approved')
    approved_at = models.DateTimeField(null=True, blank=True)
    posted_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.PROTECT, related_name='finance_vouchers_posted')
    posted_at = models.DateTimeField(null=True, blank=True)
    reversed_by = models.OneToOneField('self', null=True, blank=True, on_delete=models.PROTECT, related_name='reversal_of')

    class Meta:
        ordering = ['-voucher_date', '-id']
        constraints = [
            models.UniqueConstraint(fields=['source_module', 'source_model', 'source_id'],
                                    condition=~Q(source_id=''), name='finance_unique_source_event')
        ]
        permissions = [
            ('submit_voucher', 'Can submit vouchers'), ('review_voucher', 'Can review vouchers'),
            ('approve_voucher', 'Can approve vouchers'), ('post_voucher', 'Can post vouchers'),
            ('reverse_voucher', 'Can reverse posted vouchers'), ('close_period', 'Can close accounting periods'),
            ('view_financial_reports', 'Can view financial reports'),
        ]

    @property
    def is_balanced(self):
        return self.total_debit == self.total_credit and self.total_debit > Decimal('0.00')

    def save(self, *args, **kwargs):
        if self.pk:
            previous = Voucher.objects.filter(pk=self.pk).values('status').first()
            if previous and previous['status'] in {'POSTED', 'REVERSED'}:
                allowed = set(kwargs.get('update_fields') or [])
                is_valid_reversal = (previous['status'] == 'POSTED' and self.status == 'REVERSED'
                                     and self.reversed_by_id and allowed
                                     and allowed.issubset({'status', 'reversed_by', 'updated_at'}))
                if not is_valid_reversal:
                    raise ValidationError('Posted vouchers are immutable. Use a reversal voucher.')
        return super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        if self.status in {'POSTED', 'REVERSED'}:
            raise ValidationError('Posted vouchers cannot be deleted. Reverse the voucher instead.')
        return super().delete(*args, **kwargs)

    def __str__(self):
        return self.number


class VoucherLine(models.Model):
    voucher = models.ForeignKey(Voucher, on_delete=models.CASCADE, related_name='lines')
    account = models.ForeignKey(Account, on_delete=models.PROTECT, related_name='voucher_lines')
    description = models.CharField(max_length=255, blank=True)
    debit = models.DecimalField(max_digits=18, decimal_places=2, default=0)
    credit = models.DecimalField(max_digits=18, decimal_places=2, default=0)
    student = models.ForeignKey('student_profile.Student', null=True, blank=True, on_delete=models.PROTECT, related_name='finance_lines')
    teacher = models.ForeignKey('teacher_dashboard.Teacher', null=True, blank=True, on_delete=models.PROTECT, related_name='finance_lines')
    vendor = models.ForeignKey('admin_panel.Vendor', null=True, blank=True, on_delete=models.PROTECT, related_name='finance_lines')
    cost_center = models.ForeignKey(CostCenter, null=True, blank=True, on_delete=models.PROTECT)

    def clean(self):
        debit, credit = self.debit or 0, self.credit or 0
        if debit < 0 or credit < 0 or bool(debit) == bool(credit):
            raise ValidationError('Each line must contain one positive debit or one positive credit.')
        if not self.account.is_active or not self.account.allow_direct_posting:
            raise ValidationError('The selected account does not allow posting.')

    def save(self, *args, **kwargs):
        if self.voucher_id and Voucher.objects.filter(pk=self.voucher_id, status__in=['POSTED', 'REVERSED']).exists():
            raise ValidationError('Lines of a posted voucher are immutable.')
        return super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        if self.voucher.status in {'POSTED', 'REVERSED'}:
            raise ValidationError('Lines of a posted voucher are immutable.')
        return super().delete(*args, **kwargs)


class VoucherAttachment(TimeStampedModel):
    voucher = models.ForeignKey(Voucher, on_delete=models.CASCADE, related_name='attachments')
    file = models.FileField(upload_to='finance/voucher-attachments/%Y/%m/')
    label = models.CharField(max_length=120, blank=True)
    uploaded_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL)


class ApprovalRule(TimeStampedModel):
    voucher_type = models.CharField(max_length=2, choices=Voucher.TYPES, blank=True)
    campus = models.CharField(max_length=120, blank=True)
    department = models.CharField(max_length=120, blank=True)
    minimum_amount = models.DecimalField(max_digits=18, decimal_places=2, default=0)
    maximum_amount = models.DecimalField(max_digits=18, decimal_places=2, null=True, blank=True)
    required_group = models.ForeignKey('auth.Group', on_delete=models.PROTECT)
    sequence = models.PositiveSmallIntegerField(default=1)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['sequence', 'minimum_amount']


class ApprovalDecision(TimeStampedModel):
    ACTIONS = [('SUBMITTED', 'Submitted'), ('APPROVED', 'Approved'), ('REJECTED', 'Rejected'),
               ('POSTED', 'Posted'), ('REVERSED', 'Reversed')]
    voucher = models.ForeignKey(Voucher, on_delete=models.CASCADE, related_name='decisions')
    sequence = models.PositiveSmallIntegerField(default=1)
    action = models.CharField(max_length=12, choices=ACTIONS)
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    comment = models.TextField(blank=True)


class FinanceAuditEvent(models.Model):
    voucher = models.ForeignKey(Voucher, null=True, blank=True, on_delete=models.PROTECT, related_name='audit_events')
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL)
    action = models.CharField(max_length=40)
    details = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']


class Budget(TimeStampedModel):
    STATUS = [('DRAFT', 'Draft'), ('APPROVED', 'Approved'), ('LOCKED', 'Locked')]
    financial_year = models.ForeignKey(FinancialYear, on_delete=models.PROTECT, related_name='budgets')
    name = models.CharField(max_length=120)
    campus = models.CharField(max_length=120, blank=True)
    department = models.CharField(max_length=120, blank=True)
    status = models.CharField(max_length=10, choices=STATUS, default='DRAFT')
    approved_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.PROTECT)

    class Meta:
        constraints = [models.UniqueConstraint(fields=['financial_year', 'name', 'campus', 'department'], name='finance_unique_budget')]


class BudgetLine(models.Model):
    budget = models.ForeignKey(Budget, on_delete=models.CASCADE, related_name='lines')
    account = models.ForeignKey(Account, on_delete=models.PROTECT)
    cost_center = models.ForeignKey(CostCenter, null=True, blank=True, on_delete=models.PROTECT)
    month = models.PositiveSmallIntegerField()
    amount = models.DecimalField(max_digits=18, decimal_places=2)
    committed_amount = models.DecimalField(max_digits=18, decimal_places=2, default=0)

    class Meta:
        constraints = [models.UniqueConstraint(fields=['budget', 'account', 'cost_center', 'month'], name='finance_unique_budget_line')]

    def clean(self):
        if not 1 <= self.month <= 12:
            raise ValidationError('Budget month must be between 1 and 12.')
        if self.amount < 0 or self.committed_amount < 0 or self.committed_amount > self.amount:
            raise ValidationError('Committed amount cannot exceed the approved budget amount.')

    @property
    def available_amount(self):
        return self.amount - self.committed_amount


class CashSession(TimeStampedModel):
    STATUS = [('OPEN', 'Open'), ('SUBMITTED', 'Submitted'), ('CLOSED', 'Closed')]
    cash_account = models.ForeignKey(CashBankAccount, on_delete=models.PROTECT, related_name='sessions', limit_choices_to={'account_type': 'CASH'})
    business_date = models.DateField(default=timezone.localdate)
    opening_balance = models.DecimalField(max_digits=18, decimal_places=2)
    expected_closing = models.DecimalField(max_digits=18, decimal_places=2, default=0)
    physical_closing = models.DecimalField(max_digits=18, decimal_places=2, null=True, blank=True)
    variance_reason = models.TextField(blank=True)
    status = models.CharField(max_length=10, choices=STATUS, default='OPEN')
    cashier = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='cash_sessions')
    approved_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.PROTECT, related_name='cash_sessions_approved')

    class Meta:
        constraints = [models.UniqueConstraint(fields=['cash_account', 'business_date'], name='finance_unique_cash_session')]


class BankStatement(TimeStampedModel):
    STATUS = [('IMPORTED', 'Imported'), ('IN_REVIEW', 'In review'), ('RECONCILED', 'Reconciled')]
    bank_account = models.ForeignKey(CashBankAccount, on_delete=models.PROTECT, related_name='statements', limit_choices_to={'account_type': 'BANK'})
    period = models.ForeignKey(AccountingPeriod, on_delete=models.PROTECT)
    file = models.FileField(upload_to='finance/bank-statements/%Y/%m/')
    status = models.CharField(max_length=12, choices=STATUS, default='IMPORTED')
    imported_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)


class BankStatementLine(models.Model):
    statement = models.ForeignKey(BankStatement, on_delete=models.CASCADE, related_name='lines')
    transaction_date = models.DateField()
    reference = models.CharField(max_length=160, blank=True)
    description = models.CharField(max_length=255, blank=True)
    debit = models.DecimalField(max_digits=18, decimal_places=2, default=0)
    credit = models.DecimalField(max_digits=18, decimal_places=2, default=0)
    is_matched = models.BooleanField(default=False)


class BankMatch(TimeStampedModel):
    statement_line = models.ForeignKey(BankStatementLine, on_delete=models.PROTECT, related_name='matches')
    voucher = models.ForeignKey(Voucher, on_delete=models.PROTECT, related_name='bank_matches')
    amount = models.DecimalField(max_digits=18, decimal_places=2)
    matched_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)

    class Meta:
        constraints = [models.UniqueConstraint(fields=['statement_line', 'voucher'], name='finance_unique_bank_match')]


class FinanceRequest(TimeStampedModel):
    TYPES = [('REFUND', 'Fee refund'), ('CONCESSION', 'Fee concession'), ('REIMBURSEMENT', 'Staff reimbursement'),
             ('EXPENSE', 'Expense request'), ('ADVANCE', 'Salary advance')]
    STATUS = [('DRAFT', 'Draft'), ('SUBMITTED', 'Submitted'), ('APPROVED', 'Approved'),
              ('REJECTED', 'Rejected'), ('PAID', 'Paid')]
    request_type = models.CharField(max_length=20, choices=TYPES)
    requested_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='finance_requests')
    student = models.ForeignKey('student_profile.Student', null=True, blank=True, on_delete=models.PROTECT, related_name='finance_requests')
    teacher = models.ForeignKey('teacher_dashboard.Teacher', null=True, blank=True, on_delete=models.PROTECT, related_name='finance_requests')
    amount = models.DecimalField(max_digits=18, decimal_places=2)
    reason = models.TextField()
    attachment = models.FileField(upload_to='finance/requests/%Y/%m/', null=True, blank=True)
    status = models.CharField(max_length=12, choices=STATUS, default='SUBMITTED')
    decision_reason = models.TextField(blank=True)
    decided_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.PROTECT, related_name='finance_requests_decided')
    decided_at = models.DateTimeField(null=True, blank=True)
    linked_voucher = models.ForeignKey(Voucher, null=True, blank=True, on_delete=models.PROTECT)

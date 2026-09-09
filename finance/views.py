import csv
from datetime import date
from decimal import Decimal
from io import BytesIO, TextIOWrapper

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.db.models import F, Q, Sum
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

from edupilot_core.models import FeeVoucher, SalaryVoucher, StudentLedger

from .forms import (AccountForm, AccountingPeriodForm, ApprovalRuleForm, BankStatementForm,
                    BudgetForm, BudgetLineForm, CashBankAccountForm, CashSessionForm,
                    CostCenterForm, FinanceRequestForm, FinancialYearForm, VoucherForm,
                    VoucherLineFormSet)
from .models import (Account, AccountingPeriod, ApprovalRule, BankMatch, BankStatement, BankStatementLine,
                     Budget, CashBankAccount, CashSession, CostCenter, FinanceAuditEvent,
                     FinanceRequest, FinancialYear, Voucher, VoucherLine)
from .services import (account_balance, approve_voucher, create_voucher, ensure_default_chart,
                       period_for, post_voucher, reject_voucher, reverse_voucher, submit_voucher)


def _finance_staff(user):
    return user.is_authenticated and (user.is_staff or user.is_superuser or user.groups.filter(
        name__in=['Cashier', 'Finance Officer', 'Accountant', 'Finance Manager', 'Principal', 'Auditor', 'Department Head']
    ).exists())


def finance_staff_required(view):
    @login_required(login_url='login_admin')
    def wrapped(request, *args, **kwargs):
        if not _finance_staff(request.user):
            raise PermissionDenied('Finance access is not assigned to this account.')
        return view(request, *args, **kwargs)
    return wrapped


def _can_approve(user):
    return user.is_superuser or user.has_perm('finance.approve_voucher') or user.groups.filter(name__in=['Finance Manager', 'Principal']).exists()


@finance_staff_required
def dashboard(request):
    ensure_default_chart()
    today = timezone.localdate()
    posted = Voucher.objects.filter(status='POSTED')
    receivable = Account.objects.filter(code='1100').first()
    cash_accounts = Account.objects.filter(code__in=['1010', '1020'])
    income = posted.filter(voucher_date__year=today.year, lines__account__account_type='INCOME').aggregate(total=Sum('lines__credit'))['total'] or 0
    expenses = posted.filter(voucher_date__year=today.year, lines__account__account_type='EXPENSE').aggregate(total=Sum('lines__debit'))['total'] or 0
    context = {
        'income': income, 'expenses': expenses,
        'receivables': account_balance(receivable) if receivable else 0,
        'liquidity': sum((account_balance(a) for a in cash_accounts), Decimal('0')),
        'pending': Voucher.objects.filter(status__in=['SUBMITTED', 'UNDER_REVIEW']).count(),
        'unreconciled': BankStatementLine.objects.filter(is_matched=False).count(),
        'recent_vouchers': Voucher.objects.select_related('maker').prefetch_related('lines')[:10],
        'open_period': AccountingPeriod.objects.filter(status='OPEN', starts_on__lte=today, ends_on__gte=today).first(),
    }
    return render(request, 'finance/dashboard.html', context)


@finance_staff_required
def setup(request):
    ensure_default_chart()
    form_classes = {'year': FinancialYearForm, 'period': AccountingPeriodForm, 'account': AccountForm,
                    'cost_center': CostCenterForm, 'cash_bank': CashBankAccountForm, 'approval': ApprovalRuleForm}
    forms = {name: form_class(prefix=name) for name, form_class in form_classes.items()}
    if request.method == 'POST':
        kind = request.POST.get('kind')
        form_class = form_classes.get(kind)
        if not form_class:
            raise ValidationError('Invalid setup form.')
        form = form_class(request.POST, prefix=kind)
        forms[kind] = form
        if form.is_valid():
            form.save()
            messages.success(request, 'Finance setup saved successfully.')
            return redirect('finance:setup')
    return render(request, 'finance/setup.html', {
        'forms': forms, 'years': FinancialYear.objects.all(), 'periods': AccountingPeriod.objects.select_related('financial_year'),
        'accounts': Account.objects.select_related('parent'), 'cost_centers': CostCenter.objects.all(),
        'cash_bank_accounts': CashBankAccount.objects.select_related('ledger_account'),
        'approval_rules': ApprovalRule.objects.select_related('required_group'),
    })


@finance_staff_required
def voucher_list(request):
    vouchers = Voucher.objects.select_related('maker', 'approved_by', 'period')
    status = request.GET.get('status', '')
    voucher_type = request.GET.get('type', '')
    query = request.GET.get('q', '').strip()
    if status:
        vouchers = vouchers.filter(status=status)
    if voucher_type:
        vouchers = vouchers.filter(voucher_type=voucher_type)
    if query:
        vouchers = vouchers.filter(Q(number__icontains=query) | Q(narration__icontains=query) | Q(source_reference__icontains=query))
    return render(request, 'finance/voucher_list.html', {'vouchers': vouchers[:250], 'statuses': Voucher.STATUS, 'types': Voucher.TYPES})


@finance_staff_required
def voucher_create(request):
    ensure_default_chart()
    form = VoucherForm(request.POST or None)
    formset = VoucherLineFormSet(request.POST or None, prefix='lines')
    if request.method == 'POST' and form.is_valid() and formset.is_valid():
        try:
            voucher = create_voucher(maker=request.user, lines=[row for row in formset.cleaned_data if row], **form.cleaned_data)
            messages.success(request, f'Voucher {voucher.number} created as draft.')
            return redirect('finance:voucher_detail', pk=voucher.pk)
        except (ValidationError, PermissionDenied) as exc:
            form.add_error(None, exc)
    return render(request, 'finance/voucher_form.html', {'form': form, 'formset': formset})


@finance_staff_required
def voucher_detail(request, pk):
    voucher = get_object_or_404(Voucher.objects.select_related('period', 'maker', 'approved_by', 'posted_by').prefetch_related('lines__account', 'attachments', 'decisions__actor'), pk=pk)
    return render(request, 'finance/voucher_detail.html', {'voucher': voucher, 'can_approve': _can_approve(request.user)})


@finance_staff_required
@require_POST
def voucher_action(request, pk, action):
    voucher = get_object_or_404(Voucher, pk=pk)
    comment = request.POST.get('comment', '')
    try:
        if action == 'submit':
            submit_voucher(voucher, request.user, comment)
        elif action == 'approve':
            if not _can_approve(request.user):
                raise PermissionDenied
            approve_voucher(voucher, request.user, comment)
        elif action == 'reject':
            if not _can_approve(request.user):
                raise PermissionDenied
            reject_voucher(voucher, request.user, comment)
        elif action == 'reverse':
            if not _can_approve(request.user):
                raise PermissionDenied
            reverse_voucher(voucher, request.user, comment)
        else:
            raise ValidationError('Unknown voucher action.')
        messages.success(request, f'Voucher action {action} completed.')
    except (ValidationError, PermissionDenied) as exc:
        messages.error(request, str(exc) or 'You do not have permission for this action.')
    return redirect('finance:voucher_detail', pk=pk)


@finance_staff_required
def reports(request):
    try:
        through = date.fromisoformat(request.GET.get('through', ''))
    except ValueError:
        through = timezone.localdate()
    report_type = request.GET.get('report', 'trial_balance')
    campus, department = request.GET.get('campus', '').strip(), request.GET.get('department', '').strip()
    lines = VoucherLine.objects.filter(voucher__status='POSTED', voucher__voucher_date__lte=through)
    if campus:
        lines = lines.filter(voucher__campus=campus)
    if department:
        lines = lines.filter(Q(cost_center__department=department) | Q(voucher__cost_center__department=department))
    if report_type == 'general_ledger':
        account_id = request.GET.get('account')
        if account_id:
            lines = lines.filter(account_id=account_id)
        return render(request, 'finance/reports.html', {
            'report_type': report_type, 'ledger_lines': lines.select_related('voucher', 'account', 'student', 'teacher', 'vendor'),
            'accounts': Account.objects.filter(is_active=True), 'through': through, 'campus': campus, 'department': department,
        })
    account_types = {
        'income_statement': ['INCOME', 'EXPENSE'],
        'balance_sheet': ['ASSET', 'LIABILITY', 'EQUITY'],
        'cash_flow': ['ASSET'],
    }.get(report_type)
    if report_type == 'cash_flow':
        lines = lines.filter(account__code__in=['1010', '1020'])
    if account_types:
        lines = lines.filter(account__account_type__in=account_types)
    totals = lines.values('account_id').annotate(debits=Sum('debit'), credits=Sum('credit'))
    by_account = {row['account_id']: row for row in totals}
    accounts = Account.objects.filter(pk__in=by_account).order_by('code')
    rows, debit, credit = [], Decimal('0'), Decimal('0')
    for account in accounts:
        values = by_account[account.pk]
        raw = (values['debits'] or 0) - (values['credits'] or 0)
        debit_value, credit_value = max(raw, 0), max(-raw, 0)
        rows.append({'account': account, 'debit': debit_value, 'credit': credit_value,
                     'balance': raw if account.normal_balance == 'DEBIT' else -raw})
        debit += debit_value
        credit += credit_value
    return render(request, 'finance/reports.html', {
        'rows': rows, 'through': through, 'debit': debit, 'credit': credit, 'report_type': report_type,
        'accounts': Account.objects.filter(is_active=True), 'campus': campus, 'department': department,
    })


@finance_staff_required
@require_POST
def period_action(request, pk, action):
    if not (request.user.is_superuser or request.user.has_perm('finance.close_period')):
        raise PermissionDenied('Period closing permission is required.')
    period = get_object_or_404(AccountingPeriod, pk=pk)
    transitions = {'soft-close': ('OPEN', 'SOFT_CLOSED'), 'reopen': ('SOFT_CLOSED', 'OPEN'),
                   'lock': ('SOFT_CLOSED', 'LOCKED')}
    expected, target = transitions.get(action, (None, None))
    if period.status != expected:
        messages.error(request, 'That period transition is not allowed.')
    else:
        period.status = target
        period.save(update_fields=['status', 'updated_at'])
        FinanceAuditEvent.objects.create(actor=request.user, action=f'PERIOD_{target}', details={'period': period.pk})
        messages.success(request, f'{period.name} is now {period.get_status_display().lower()}.')
    return redirect('finance:setup')


@finance_staff_required
def audit_log(request):
    events = FinanceAuditEvent.objects.select_related('voucher', 'actor')[:300]
    return render(request, 'finance/audit.html', {'events': events})


@finance_staff_required
def cash_sessions(request):
    form = CashSessionForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        session = form.save(commit=False)
        session.cashier = request.user
        session.expected_closing = session.opening_balance
        session.save()
        messages.success(request, 'Cash session opened.')
        return redirect('finance:cash_sessions')
    return render(request, 'finance/operations.html', {'title': 'Daily Cash Sessions', 'form': form, 'objects': CashSession.objects.select_related('cash_account', 'cashier')[:100], 'kind': 'cash'})


@finance_staff_required
@require_POST
def cash_session_action(request, pk, action):
    item = get_object_or_404(CashSession, pk=pk)
    if action == 'submit' and item.status == 'OPEN' and item.cashier_id == request.user.pk:
        movement = VoucherLine.objects.filter(
            voucher__status='POSTED', voucher__voucher_date=item.business_date,
            account=item.cash_account.ledger_account,
        ).aggregate(debit=Sum('debit'), credit=Sum('credit'))
        item.expected_closing = item.opening_balance + (movement['debit'] or 0) - (movement['credit'] or 0)
        item.status = 'SUBMITTED'
        item.save(update_fields=['expected_closing', 'status', 'updated_at'])
    elif action == 'close' and item.status == 'SUBMITTED' and _can_approve(request.user) and item.cashier_id != request.user.pk:
        if item.physical_closing is None or (item.physical_closing != item.expected_closing and not item.variance_reason.strip()):
            messages.error(request, 'Physical closing and a reason for any variance are required.')
            return redirect('finance:cash_sessions')
        item.status, item.approved_by = 'CLOSED', request.user
        item.save(update_fields=['status', 'approved_by', 'updated_at'])
    else:
        raise PermissionDenied('This cash-session action is not allowed.')
    messages.success(request, 'Cash session updated.')
    return redirect('finance:cash_sessions')


@finance_staff_required
def bank_reconciliation(request):
    form = BankStatementForm(request.POST or None, request.FILES or None)
    if request.method == 'POST' and form.is_valid():
        statement = form.save(commit=False)
        statement.imported_by = request.user
        statement.save()
        try:
            wrapper = TextIOWrapper(statement.file.open('rb'), encoding='utf-8-sig')
            for row in csv.DictReader(wrapper):
                bank_line = BankStatementLine.objects.create(
                    statement=statement, transaction_date=row['date'], reference=row.get('reference', ''),
                    description=row.get('description', ''), debit=Decimal(row.get('debit') or 0), credit=Decimal(row.get('credit') or 0),
                )
                amount = bank_line.credit or bank_line.debit
                expected_debit = bool(bank_line.credit)
                candidates = VoucherLine.objects.filter(
                    voucher__status='POSTED', voucher__voucher_date=bank_line.transaction_date,
                    account=statement.bank_account.ledger_account,
                )
                candidates = candidates.filter(debit=amount) if expected_debit else candidates.filter(credit=amount)
                candidate = candidates.exclude(voucher__bank_matches__isnull=False).first()
                if candidate:
                    BankMatch.objects.create(statement_line=bank_line, voucher=candidate.voucher,
                                             amount=amount, matched_by=request.user)
                    bank_line.is_matched = True
                    bank_line.save(update_fields=['is_matched'])
            statement.status = 'IN_REVIEW'
            statement.save(update_fields=['status', 'updated_at'])
        except Exception as exc:
            messages.warning(request, f'Statement saved; rows need manual review because import reported: {exc}')
        return redirect('finance:bank_reconciliation')
    return render(request, 'finance/operations.html', {'title': 'Bank Reconciliation', 'form': form, 'objects': BankStatement.objects.select_related('bank_account', 'period')[:100], 'kind': 'bank'})


@finance_staff_required
def bank_statement_detail(request, pk):
    statement = get_object_or_404(BankStatement.objects.select_related('bank_account', 'period', 'imported_by'), pk=pk)
    return render(request, 'finance/bank_statement_detail.html', {
        'statement': statement,
        'lines': statement.lines.prefetch_related('matches__voucher').order_by('transaction_date', 'pk'),
    })


@finance_staff_required
@require_POST
@transaction.atomic
def bank_line_match(request, pk):
    line = get_object_or_404(BankStatementLine.objects.select_for_update().select_related('statement__bank_account'), pk=pk)
    if line.statement.status == 'RECONCILED':
        raise PermissionDenied('A reconciled statement is immutable.')
    voucher = get_object_or_404(Voucher, number=request.POST.get('voucher_number', '').strip(), status='POSTED')
    try:
        amount = Decimal(request.POST.get('amount', '0'))
    except Exception:
        amount = Decimal('0')
    statement_amount = line.credit or line.debit
    matched = line.matches.aggregate(total=Sum('amount'))['total'] or Decimal('0')
    direction = {'debit__gte': amount} if line.credit else {'credit__gte': amount}
    has_bank_line = voucher.lines.filter(account=line.statement.bank_account.ledger_account, **direction).exists()
    if amount <= 0 or matched + amount > statement_amount or not has_bank_line:
        messages.error(request, 'Match amount or voucher bank movement is invalid.')
    else:
        BankMatch.objects.create(statement_line=line, voucher=voucher, amount=amount, matched_by=request.user)
        line.is_matched = matched + amount == statement_amount
        line.save(update_fields=['is_matched'])
        messages.success(request, 'Statement line matched.')
    return redirect('finance:bank_statement_detail', pk=line.statement_id)


@finance_staff_required
@require_POST
def bank_statement_action(request, pk, action):
    statement = get_object_or_404(BankStatement, pk=pk)
    if action != 'reconcile' or statement.status != 'IN_REVIEW' or not _can_approve(request.user):
        raise PermissionDenied('This reconciliation action is not allowed.')
    if statement.imported_by_id == request.user.pk:
        raise PermissionDenied('The statement importer cannot approve their own reconciliation.')
    if statement.lines.filter(is_matched=False).exists():
        messages.error(request, 'Every statement line must be matched before reconciliation can close.')
    else:
        statement.status = 'RECONCILED'
        statement.save(update_fields=['status', 'updated_at'])
        FinanceAuditEvent.objects.create(actor=request.user, action='BANK_RECONCILED', details={'statement': statement.pk})
        messages.success(request, 'Bank statement reconciled.')
    return redirect('finance:bank_reconciliation')


@finance_staff_required
def budgets(request):
    kind = request.POST.get('kind', 'budget')
    form = BudgetForm(request.POST or None) if kind == 'budget' else BudgetForm()
    line_form = BudgetLineForm(request.POST or None) if kind == 'line' else BudgetLineForm()
    target = form if kind == 'budget' else line_form
    if request.method == 'POST' and target.is_valid():
        target.save()
        messages.success(request, 'Budget information saved.')
        return redirect('finance:budgets')
    return render(request, 'finance/operations.html', {'title': 'Budgets and Commitments', 'form': form,
        'line_form': line_form, 'objects': Budget.objects.select_related('financial_year').prefetch_related('lines')[:100], 'kind': 'budget'})


@finance_staff_required
def request_list(request):
    return render(request, 'finance/request_list.html', {
        'requests': FinanceRequest.objects.select_related('requested_by', 'student', 'teacher', 'decided_by')[:300],
        'can_approve': _can_approve(request.user),
    })


@finance_staff_required
@require_POST
@transaction.atomic
def request_action(request, pk, action):
    if not _can_approve(request.user):
        raise PermissionDenied('Finance approval permission is required.')
    item = get_object_or_404(FinanceRequest.objects.select_for_update(), pk=pk, status='SUBMITTED')
    if item.requested_by_id == request.user.pk:
        raise PermissionDenied('A requester cannot approve their own request.')
    reason = request.POST.get('reason', '').strip()
    if action == 'reject':
        if not reason:
            messages.error(request, 'A rejection reason is required.')
            return redirect('finance:request_list')
        item.status = 'REJECTED'
    elif action == 'approve':
        item.status = 'APPROVED'
        accounts = ensure_default_chart()
        if item.request_type in {'REFUND', 'CONCESSION'}:
            lines = [
                {'account': accounts['5300'], 'debit': item.amount, 'credit': 0, 'student': item.student,
                 'description': item.get_request_type_display()},
                {'account': accounts['1100'], 'debit': 0, 'credit': item.amount, 'student': item.student,
                 'description': 'Student receivable adjustment'},
            ]
            voucher_type = 'CN'
        elif item.request_type == 'ADVANCE':
            lines = [
                {'account': accounts['1200'], 'debit': item.amount, 'credit': 0, 'teacher': item.teacher,
                 'description': 'Staff advance'},
                {'account': accounts['2200'], 'debit': 0, 'credit': item.amount, 'teacher': item.teacher,
                 'description': 'Approved staff amount payable'},
            ]
            voucher_type = 'JV'
        else:
            lines = [
                {'account': accounts['5200'], 'debit': item.amount, 'credit': 0, 'teacher': item.teacher,
                 'description': item.get_request_type_display()},
                {'account': accounts['2200'], 'debit': 0, 'credit': item.amount, 'teacher': item.teacher,
                 'description': 'Approved staff amount payable'},
            ]
            voucher_type = 'JV'
        linked = create_voucher(voucher_type=voucher_type, narration=f'Approved request #{item.pk}: {item.reason}',
                                maker=item.requested_by, source_module='finance', source_model='FinanceRequest',
                                source_id=item.pk, source_reference=f'REQ-{item.pk}', lines=lines)
        item.linked_voucher = post_voucher(linked, request.user, system=True)
    else:
        raise ValidationError('Unknown request action.')
    item.decision_reason, item.decided_by, item.decided_at = reason, request.user, timezone.now()
    item.save(update_fields=['status', 'decision_reason', 'decided_by', 'decided_at', 'linked_voucher', 'updated_at'])
    FinanceAuditEvent.objects.create(actor=request.user, action=f'REQUEST_{item.status}',
                                     details={'request': item.pk, 'amount': str(item.amount)})
    messages.success(request, f'Request {item.get_status_display().lower()}.')
    return redirect('finance:request_list')


def _portal_role(user):
    if hasattr(user, 'parent'):
        return 'PARENT'
    if hasattr(user, 'student'):
        return 'STUDENT'
    if hasattr(user, 'teacher'):
        return 'TEACHER'
    raise PermissionDenied('A parent, student or teacher profile is required.')


@login_required
def portal_dashboard(request):
    role = _portal_role(request.user)
    context = {'portal_role': role, 'requests': FinanceRequest.objects.filter(requested_by=request.user)}
    if role == 'PARENT':
        children = request.user.parent.students.all()
        selected = children.filter(pk=request.GET.get('student')).first() if request.GET.get('student') else children.first()
        context.update({'base_template': 'parent_dashboard/base.html', 'children': children, 'selected_student': selected})
        if selected:
            context['vouchers'] = FeeVoucher.objects.filter(Q(canonical_student=selected) | Q(student__canonical_student=selected)).order_by('-issue_date')
            context['ledger'] = StudentLedger.objects.filter(Q(canonical_student=selected) | Q(student__canonical_student=selected)).order_by('-date')
    elif role == 'STUDENT':
        student = request.user.student
        context.update({'base_template': 'student_profile/bases.html', 'selected_student': student,
                        'vouchers': FeeVoucher.objects.filter(Q(canonical_student=student) | Q(student__canonical_student=student)).order_by('-issue_date'),
                        'ledger': StudentLedger.objects.filter(Q(canonical_student=student) | Q(student__canonical_student=student)).order_by('-date')})
    else:
        teacher = request.user.teacher
        context.update({'base_template': 'teacher_dashboard/bases.html', 'teacher': teacher,
                        'salary_vouchers': SalaryVoucher.objects.filter(Q(canonical_teacher=teacher) | Q(teacher__canonical_teacher=teacher)).order_by('-year', '-id')})
    return render(request, 'finance/portal.html', context)


@login_required
def portal_request(request):
    role = _portal_role(request.user)
    form = FinanceRequestForm(request.POST or None, request.FILES or None, user=request.user)
    if request.method == 'POST' and form.is_valid():
        item = form.save(commit=False)
        item.requested_by = request.user
        if role == 'TEACHER':
            item.teacher = request.user.teacher
        elif role == 'STUDENT':
            item.student = request.user.student
        item.save()
        messages.success(request, 'Finance request submitted for review.')
        return redirect('finance:portal')
    base = {'PARENT': 'parent_dashboard/base.html', 'STUDENT': 'student_profile/bases.html', 'TEACHER': 'teacher_dashboard/bases.html'}[role]
    return render(request, 'finance/request_form.html', {'form': form, 'base_template': base, 'portal_role': role})


def _pdf_response(filename, title, rows):
    stream = BytesIO()
    pdf = canvas.Canvas(stream, pagesize=A4)
    width, height = A4
    pdf.setTitle(title)
    pdf.setFont('Helvetica-Bold', 18)
    pdf.drawString(48, height - 55, 'EduPilot')
    pdf.setFont('Helvetica-Bold', 14)
    pdf.drawString(48, height - 82, title)
    y = height - 120
    for label, value in rows:
        pdf.setFont('Helvetica-Bold', 10)
        pdf.drawString(48, y, str(label))
        pdf.setFont('Helvetica', 10)
        pdf.drawString(180, y, str(value))
        y -= 22
    pdf.setFont('Helvetica', 8)
    pdf.drawString(48, 35, 'System generated document. Verify using the numbered reference above.')
    pdf.save()
    response = HttpResponse(stream.getvalue(), content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    return response


def _student_allowed(user, student):
    if hasattr(user, 'student'):
        return user.student.pk == student.pk
    if hasattr(user, 'parent'):
        return user.parent.students.filter(pk=student.pk).exists()
    return False


@login_required
def fee_document(request, pk):
    voucher = get_object_or_404(FeeVoucher, pk=pk)
    student = voucher.canonical_student or getattr(voucher.student, 'canonical_student', None)
    if not student or not _student_allowed(request.user, student):
        raise PermissionDenied('This fee document does not belong to your account.')
    return _pdf_response(f'{voucher.voucher_no}.pdf', 'Fee Invoice', [
        ('Invoice number', voucher.voucher_no), ('Student', student.name),
        ('Billing period', f'{voucher.month} {voucher.year}'), ('Issue date', voucher.issue_date),
        ('Due date', voucher.due_date), ('Gross amount', f'PKR {voucher.gross_amount:,.2f}'),
        ('Discount', f'PKR {voucher.discount:,.2f}'), ('Fine', f'PKR {voucher.fine:,.2f}'),
        ('Amount payable', f'PKR {voucher.net_amount:,.2f}'), ('Status', voucher.get_status_display()),
    ])


@login_required
def receipt_document(request, pk):
    entry = get_object_or_404(StudentLedger, pk=pk, credit__gt=0)
    student = entry.canonical_student or getattr(entry.student, 'canonical_student', None)
    if not student or not _student_allowed(request.user, student):
        raise PermissionDenied('This receipt does not belong to your account.')
    reference = entry.reference_no or f'REC-{entry.pk:08d}'
    return _pdf_response(f'{reference}.pdf', 'Payment Receipt', [
        ('Receipt number', reference), ('Student', student.name), ('Payment date', entry.date),
        ('Description', entry.description), ('Amount received', f'PKR {entry.credit:,.2f}'),
        ('Outstanding balance', f'PKR {entry.balance:,.2f}'),
    ])


@login_required
def payslip_document(request, pk):
    voucher = get_object_or_404(SalaryVoucher, pk=pk)
    teacher = voucher.canonical_teacher or getattr(voucher.teacher, 'canonical_teacher', None)
    if not hasattr(request.user, 'teacher') or not teacher or request.user.teacher.pk != teacher.pk:
        raise PermissionDenied('This payslip does not belong to your account.')
    structure = getattr(voucher.teacher, 'salarystructure', None)
    deductions = getattr(structure, 'deductions', Decimal('0'))
    return _pdf_response(f'PAY-{voucher.year}-{voucher.month}-{voucher.pk}.pdf', 'Salary Payslip', [
        ('Payslip number', f'PAY-{voucher.year}-{voucher.month}-{voucher.pk}'), ('Teacher', teacher.name),
        ('Salary period', f'{voucher.month} {voucher.year}'),
        ('Gross salary', f'PKR {(voucher.net_salary + deductions):,.2f}'),
        ('Deductions', f'PKR {deductions:,.2f}'), ('Net salary', f'PKR {voucher.net_salary:,.2f}'),
        ('Payment status', voucher.status), ('Generated', voucher.generated_at.date()),
    ])

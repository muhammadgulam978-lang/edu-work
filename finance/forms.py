from django import forms
from django.forms import formset_factory

from .models import (Account, AccountingPeriod, ApprovalRule, BankStatement, Budget, BudgetLine,
                     CashBankAccount, CashSession, CostCenter, FinanceRequest, FinancialYear, Voucher)


class DateInput(forms.DateInput):
    input_type = 'date'


class FinancialYearForm(forms.ModelForm):
    class Meta:
        model = FinancialYear
        fields = ['name', 'starts_on', 'ends_on', 'status', 'is_active']
        widgets = {'starts_on': DateInput(), 'ends_on': DateInput()}


class AccountingPeriodForm(forms.ModelForm):
    class Meta:
        model = AccountingPeriod
        fields = ['financial_year', 'name', 'starts_on', 'ends_on', 'status']
        widgets = {'starts_on': DateInput(), 'ends_on': DateInput()}


class AccountForm(forms.ModelForm):
    class Meta:
        model = Account
        fields = ['code', 'name', 'account_type', 'normal_balance', 'parent', 'campus',
                  'tax_treatment', 'is_control_account', 'allow_direct_posting', 'is_active']


class CostCenterForm(forms.ModelForm):
    class Meta:
        model = CostCenter
        fields = ['code', 'name', 'campus', 'branch', 'department', 'is_active']


class CashBankAccountForm(forms.ModelForm):
    class Meta:
        model = CashBankAccount
        fields = ['name', 'account_type', 'ledger_account', 'account_number_masked', 'campus', 'is_active']


class ApprovalRuleForm(forms.ModelForm):
    class Meta:
        model = ApprovalRule
        fields = ['voucher_type', 'campus', 'department', 'minimum_amount', 'maximum_amount',
                  'required_group', 'sequence', 'is_active']


class VoucherForm(forms.ModelForm):
    class Meta:
        model = Voucher
        fields = ['voucher_type', 'voucher_date', 'narration', 'campus', 'branch', 'cost_center',
                  'source_reference']
        widgets = {'voucher_date': DateInput(), 'narration': forms.Textarea(attrs={'rows': 3})}


class VoucherLineForm(forms.Form):
    account = forms.ModelChoiceField(queryset=Account.objects.none())
    description = forms.CharField(max_length=255, required=False)
    debit = forms.DecimalField(max_digits=18, decimal_places=2, min_value=0, required=False)
    credit = forms.DecimalField(max_digits=18, decimal_places=2, min_value=0, required=False)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['account'].queryset = Account.objects.filter(is_active=True, allow_direct_posting=True)

    def clean(self):
        data = super().clean()
        debit, credit = data.get('debit') or 0, data.get('credit') or 0
        if bool(debit) == bool(credit):
            raise forms.ValidationError('Enter either a debit or a credit amount.')
        return data


VoucherLineFormSet = formset_factory(VoucherLineForm, extra=2, min_num=2, validate_min=True)


class FinanceRequestForm(forms.ModelForm):
    class Meta:
        model = FinanceRequest
        fields = ['request_type', 'student', 'amount', 'reason', 'attachment']
        widgets = {'reason': forms.Textarea(attrs={'rows': 4})}

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        role = 'teacher' if hasattr(user, 'teacher') else 'parent' if hasattr(user, 'parent') else 'student'
        if role == 'teacher':
            self.fields['request_type'].choices = [('REIMBURSEMENT', 'Staff reimbursement'), ('EXPENSE', 'Expense request'), ('ADVANCE', 'Salary advance')]
            self.fields['student'].widget = forms.HiddenInput()
            self.fields['student'].required = False
        else:
            self.fields['request_type'].choices = [('REFUND', 'Fee refund'), ('CONCESSION', 'Fee concession')]
            if role == 'parent':
                self.fields['student'].queryset = user.parent.students.all()
            else:
                self.fields['student'].queryset = self.fields['student'].queryset.filter(user=user)


class CashSessionForm(forms.ModelForm):
    class Meta:
        model = CashSession
        fields = ['cash_account', 'business_date', 'opening_balance', 'physical_closing', 'variance_reason']
        widgets = {'business_date': DateInput(), 'variance_reason': forms.Textarea(attrs={'rows': 3})}


class BankStatementForm(forms.ModelForm):
    class Meta:
        model = BankStatement
        fields = ['bank_account', 'period', 'file']


class BudgetForm(forms.ModelForm):
    class Meta:
        model = Budget
        fields = ['financial_year', 'name', 'campus', 'department', 'status']


class BudgetLineForm(forms.ModelForm):
    class Meta:
        model = BudgetLine
        fields = ['budget', 'account', 'cost_center', 'month', 'amount', 'committed_amount']

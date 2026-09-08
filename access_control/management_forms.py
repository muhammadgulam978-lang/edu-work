from django import forms
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError

from .models import Campus, Institution, RoleAssignment, RoleDefinition


class StyledModelForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.setdefault('class', 'form-control')


class InstitutionForm(StyledModelForm):
    class Meta:
        model = Institution
        fields = ('name', 'code', 'active')


class CampusForm(StyledModelForm):
    class Meta:
        model = Campus
        fields = ('institution', 'name', 'code')


class RoleForm(StyledModelForm):
    class Meta:
        model = RoleDefinition
        fields = ('institution', 'name', 'active', 'requires_mfa')


class AccountForm(StyledModelForm):
    password = forms.CharField(required=False, widget=forms.PasswordInput(attrs={'class': 'form-control'}),
                               help_text='Required for a new account. Leave blank while editing to keep the current password.')

    class Meta:
        model = get_user_model()
        fields = ('username', 'first_name', 'last_name', 'email', 'is_active')

    def clean(self):
        data = super().clean()
        if not self.instance.pk and not data.get('password'):
            self.add_error('password', 'Set an initial password for the new account.')
        return data

    def save(self, commit=True):
        user = super().save(commit=False)
        if self.cleaned_data.get('password'):
            user.set_password(self.cleaned_data['password'])
        if commit:
            user.save()
        return user


class AssignmentForm(StyledModelForm):
    class Meta:
        model = RoleAssignment
        fields = ('user', 'role', 'campus', 'starts_at', 'ends_at', 'active', 'is_primary')
        widgets = {'starts_at': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
                   'ends_at': forms.DateTimeInput(attrs={'type': 'datetime-local'})}

    def clean(self):
        data = super().clean()
        role, campus = data.get('role'), data.get('campus')
        if role and campus and role.institution_id != campus.institution_id:
            raise ValidationError('The campus must belong to the role institution.')
        return data


class StudentCampusMappingForm(forms.Form):
    institution = forms.ModelChoiceField(queryset=Institution.objects.filter(active=True), widget=forms.Select(attrs={'class': 'form-control'}))
    campus = forms.ModelChoiceField(queryset=Campus.objects.none(), widget=forms.Select(attrs={'class': 'form-control'}))
    students = forms.MultipleChoiceField(widget=forms.CheckboxSelectMultiple, required=True)

    def __init__(self, *args, **kwargs):
        students = kwargs.pop('students')
        super().__init__(*args, **kwargs)
        self.fields['students'].choices = [(str(item.pk), f'{item.student_id} — {item.name}') for item in students]
        institution_id = self.data.get('institution') or self.initial.get('institution')
        if institution_id:
            self.fields['campus'].queryset = Campus.objects.filter(institution_id=institution_id)

    def clean(self):
        data = super().clean()
        if data.get('campus') and data.get('institution') and data['campus'].institution_id != data['institution'].pk:
            raise ValidationError('The selected campus belongs to another institution.')
        return data

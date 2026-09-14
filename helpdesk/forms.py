from pathlib import Path

from django import forms
from django.contrib.auth import get_user_model
from django.db.models import Q

from .models import Ticket, TicketCategory, TicketMessage


ALLOWED_EXTENSIONS = {'.pdf', '.png', '.jpg', '.jpeg', '.docx'}


def validate_attachment(file):
    if not file:
        return file
    if file.size > 10 * 1024 * 1024:
        raise forms.ValidationError('Attachment must be 10 MB or smaller.')
    if Path(file.name).suffix.lower() not in ALLOWED_EXTENSIONS:
        raise forms.ValidationError('Allowed files: PDF, PNG, JPG and DOCX.')
    return file


class TicketForm(forms.ModelForm):
    attachment = forms.FileField(required=False)

    class Meta:
        model = Ticket
        fields = ['ticket_type', 'student', 'category', 'subject', 'description', 'priority', 'privacy',
                  'anonymous_to_handlers']
        widgets = {'description': forms.Textarea(attrs={'rows': 6})}

    def __init__(self, *args, user=None, role=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.user, self.role = user, role
        role_filter = {f'{role.lower()}_enabled': True} if role in {'STUDENT', 'PARENT', 'TEACHER'} else {}
        self.fields['category'].queryset = TicketCategory.objects.filter(is_active=True, **role_filter)
        if role == 'PARENT':
            self.fields['student'].queryset = user.parent.students.all()
            self.fields['student'].required = True
        elif role == 'STUDENT':
            self.fields['student'].queryset = self.fields['student'].queryset.filter(user=user)
            self.fields['student'].widget = forms.HiddenInput()
            self.fields['student'].required = False
        else:
            self.fields['student'].widget = forms.HiddenInput()
            self.fields['student'].required = False

    def clean_attachment(self):
        return validate_attachment(self.cleaned_data.get('attachment'))


class MessageForm(forms.ModelForm):
    class Meta:
        model = TicketMessage
        fields = ['body', 'attachment']
        widgets = {'body': forms.Textarea(attrs={'rows': 3, 'placeholder': 'Write a reply…'})}

    def clean_attachment(self):
        return validate_attachment(self.cleaned_data.get('attachment'))


class StaffMessageForm(MessageForm):
    class Meta(MessageForm.Meta):
        fields = ['body', 'is_internal', 'attachment']


class AssignmentForm(forms.ModelForm):
    class Meta:
        model = Ticket
        fields = ['assigned_department', 'assigned_to', 'priority', 'privacy']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        User = get_user_model()
        self.fields['assigned_to'].queryset = User.objects.filter(is_active=True).filter(
            Q(is_staff=True) | Q(groups__name__in=[
                'Admin', 'Support Officer', 'Department Head', 'Principal', 'Finance Officer', 'HR'
            ])).distinct()


class ResolutionForm(forms.Form):
    resolution = forms.CharField(widget=forms.Textarea(attrs={'rows': 4}))


class RatingForm(forms.Form):
    rating = forms.TypedChoiceField(choices=[(i, f'{i} / 5') for i in range(1, 6)], coerce=int)
    comment = forms.CharField(required=False, widget=forms.Textarea(attrs={'rows': 3}))

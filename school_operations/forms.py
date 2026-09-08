from django import forms
from access_control.models import Campus
from student_profile.models import Student
from .models import LibraryBook, LabAsset, HealthCase


class StyledForm(forms.Form):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.setdefault('class', 'form-control')


class BookForm(StyledForm):
    campus = forms.ModelChoiceField(queryset=Campus.objects.none())
    title = forms.CharField(max_length=200)
    author = forms.CharField(max_length=200, required=False)
    isbn = forms.CharField(max_length=32, required=False)
    copies = forms.IntegerField(min_value=1, initial=1)


class LoanForm(StyledForm):
    book = forms.ModelChoiceField(queryset=LibraryBook.objects.none())
    student = forms.ModelChoiceField(queryset=Student.objects.none())
    due_on = forms.DateField(widget=forms.DateInput(attrs={'type': 'date'}))


class AssetForm(StyledForm):
    campus = forms.ModelChoiceField(queryset=Campus.objects.none())
    name = forms.CharField(max_length=200)
    laboratory = forms.CharField(max_length=100)
    inventory_code = forms.CharField(max_length=50)
    quantity = forms.IntegerField(min_value=1, initial=1)
    safety_notes = forms.CharField(widget=forms.Textarea, required=False)


class BookingForm(StyledForm):
    asset = forms.ModelChoiceField(queryset=LabAsset.objects.none())
    starts_at = forms.DateTimeField(widget=forms.DateTimeInput(attrs={'type': 'datetime-local'}))
    ends_at = forms.DateTimeField(widget=forms.DateTimeInput(attrs={'type': 'datetime-local'}))
    purpose = forms.CharField(max_length=255)


class CaseForm(StyledForm):
    campus = forms.ModelChoiceField(queryset=Campus.objects.none())
    student = forms.ModelChoiceField(queryset=Student.objects.none())
    category = forms.ChoiceField(choices=HealthCase._meta.get_field('category').choices)
    notes = forms.CharField(widget=forms.Textarea)
    consent_reference = forms.CharField(max_length=255,
                                        help_text='Reference to verified consent or safeguarding authority.')
    follow_up_on = forms.DateField(required=False, widget=forms.DateInput(attrs={'type': 'date'}))

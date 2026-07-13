# teacher_dashboard/appraisal_forms.py  (UPDATED)

from django import forms
from django.forms import inlineformset_factory, BaseInlineFormSet
from admin_panel.models import TeacherAppraisalSubmission, TeacherActivity, KpiRule


class TeacherAppraisalSubmissionForm(forms.ModelForm):
    class Meta:
        model = TeacherAppraisalSubmission
        fields = ("achievements", "challenges", "improvement_plan")
        widgets = {
            "achievements": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
            "challenges": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
            "improvement_plan": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
        }


class TeacherActivityForm(forms.ModelForm):
    kpi_selector = forms.ChoiceField(
        choices=[],
        required=True,
        widget=forms.Select(attrs={"class": "form-select"})
    )

    class Meta:
        model = TeacherActivity
        fields = ("kpi_selector", "title", "date", "hours", "notes")
        widgets = {
            "title": forms.TextInput(attrs={"class": "form-control"}),
            "date": forms.DateInput(attrs={"class": "form-control", "type": "date"}),
            "hours": forms.NumberInput(attrs={"class": "form-control", "step": "0.5", "min": "0"}),
            "notes": forms.TextInput(attrs={"class": "form-control"}),
        }

    def __init__(self, *args, **kwargs):
        template = kwargs.pop("template", None)
        super().__init__(*args, **kwargs)

        activity_choices = [
            ("ACT:EXTRA", "Extra Curricular"),
            ("ACT:WORKSHOP_ATTEND", "Workshop Attended"),
            ("ACT:TRAINING_GIVEN", "Training Given"),
        ]

        manual_choices = []
        if template:
            rules = template.rules.filter(is_active=True, is_manual=True).order_by("id")
            manual_choices = [(f"MKPI:{r.id}", f"{r.title} (Evidence based scoring)") for r in rules]

        self.fields["kpi_selector"].choices = activity_choices + manual_choices

        # edit mode initial
        if self.instance and self.instance.pk:
            if self.instance.entry_kind == "MANUAL_KPI" and self.instance.manual_rule_id:
                self.fields["kpi_selector"].initial = f"MKPI:{self.instance.manual_rule_id}"
            else:
                self.fields["kpi_selector"].initial = f"ACT:{self.instance.activity_type}"


class TeacherActivityBaseFormSet(BaseInlineFormSet):
    def __init__(self, *args, **kwargs):
        self.template = kwargs.pop("template", None)
        super().__init__(*args, **kwargs)

    def get_form_kwargs(self, index):
        kw = super().get_form_kwargs(index)
        kw["template"] = self.template
        return kw


TeacherActivityFormSet = inlineformset_factory(
    TeacherAppraisalSubmission,
    TeacherActivity,
    form=TeacherActivityForm,
    formset=TeacherActivityBaseFormSet,
    extra=1,
    can_delete=True,
)

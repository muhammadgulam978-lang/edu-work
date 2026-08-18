from django import forms

from .models import (
    CounsellingAppointment,
    CounsellingCase,
    CounsellingReferral,
    CounsellingSession,
    SafeguardingConcern,
    StudentSupportPlan,
)


class CounsellingReferralForm(forms.ModelForm):
    class Meta:
        model = CounsellingReferral
        fields = ["student", "category", "source", "referred_by_name", "description", "priority"]
        widgets = {"description": forms.Textarea(attrs={"rows": 4})}


class CounsellingCaseForm(forms.ModelForm):
    class Meta:
        model = CounsellingCase
        fields = [
            "student", "referral", "reason_for_referral", "priority", "status",
            "assigned_counsellor", "support_goals", "follow_up_date",
        ]
        widgets = {
            "reason_for_referral": forms.Textarea(attrs={"rows": 3}),
            "support_goals": forms.Textarea(attrs={"rows": 3}),
            "follow_up_date": forms.DateInput(attrs={"type": "date"}),
        }


class CaseClosureForm(forms.ModelForm):
    class Meta:
        model = CounsellingCase
        fields = ["outcome", "closure_summary"]
        widgets = {
            "outcome": forms.Textarea(attrs={"rows": 2}),
            "closure_summary": forms.Textarea(attrs={"rows": 3}),
        }


class CounsellingSessionForm(forms.ModelForm):
    class Meta:
        model = CounsellingSession
        fields = ["session_type", "session_datetime", "conducted_by", "notes", "next_steps"]
        widgets = {
            "session_datetime": forms.DateTimeInput(attrs={"type": "datetime-local"}),
            "notes": forms.Textarea(attrs={"rows": 5}),
            "next_steps": forms.Textarea(attrs={"rows": 2}),
        }


class StudentSupportPlanForm(forms.ModelForm):
    class Meta:
        model = StudentSupportPlan
        fields = [
            "main_concern", "student_strengths", "short_term_goals", "long_term_goals",
            "planned_interventions", "responsible_staff", "review_date", "progress_indicators",
        ]
        widgets = {
            "main_concern": forms.Textarea(attrs={"rows": 2}),
            "student_strengths": forms.Textarea(attrs={"rows": 2}),
            "short_term_goals": forms.Textarea(attrs={"rows": 2}),
            "long_term_goals": forms.Textarea(attrs={"rows": 2}),
            "planned_interventions": forms.Textarea(attrs={"rows": 2}),
            "review_date": forms.DateInput(attrs={"type": "date"}),
        }


class CounsellingAppointmentForm(forms.ModelForm):
    class Meta:
        model = CounsellingAppointment
        fields = ["student", "case", "counsellor", "scheduled_datetime", "mode", "status", "notes"]
        widgets = {
            "scheduled_datetime": forms.DateTimeInput(attrs={"type": "datetime-local"}),
            "notes": forms.Textarea(attrs={"rows": 2}),
        }


class SafeguardingConcernForm(forms.ModelForm):
    class Meta:
        model = SafeguardingConcern
        fields = [
            "student", "concern_type", "risk_level", "reported_by_name", "description",
            "immediate_action_taken", "safeguarding_officer", "parent_contact_decision",
            "external_referral_made", "external_referral_details", "safety_plan",
        ]
        widgets = {
            "description": forms.Textarea(attrs={"rows": 4}),
            "immediate_action_taken": forms.Textarea(attrs={"rows": 2}),
            "external_referral_details": forms.Textarea(attrs={"rows": 2}),
            "safety_plan": forms.Textarea(attrs={"rows": 2}),
        }

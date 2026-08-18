from django import forms

from .models import (
    EmergencyCase,
    HealthCheckupCycle,
    HealthCheckupRecord,
    Medicine,
    MedicineBatch,
    MedicalVisit,
    SickBayAdmission,
)


class HealthCheckupCycleForm(forms.ModelForm):
    class Meta:
        model = HealthCheckupCycle
        fields = [
            "title", "campus", "checkup_type", "patient_type",
            "start_date", "end_date", "assigned_doctor", "assigned_nurse",
            "consent_required", "location", "instructions", "follow_up_deadline",
        ]
        widgets = {
            "start_date": forms.DateInput(attrs={"type": "date"}),
            "end_date": forms.DateInput(attrs={"type": "date"}),
            "follow_up_deadline": forms.DateInput(attrs={"type": "date"}),
            "instructions": forms.Textarea(attrs={"rows": 3}),
        }


class HealthCheckupRecordForm(forms.ModelForm):
    class Meta:
        model = HealthCheckupRecord
        fields = [
            "status", "checkup_date", "height_cm", "weight_kg", "temperature_c",
            "pulse_rate", "blood_pressure", "oxygen_saturation",
            "current_symptoms", "general_notes", "outcome", "risk_level",
            "follow_up_date", "examined_by",
        ]
        widgets = {
            "checkup_date": forms.DateInput(attrs={"type": "date"}),
            "follow_up_date": forms.DateInput(attrs={"type": "date"}),
            "current_symptoms": forms.Textarea(attrs={"rows": 2}),
            "general_notes": forms.Textarea(attrs={"rows": 2}),
        }


class MedicalVisitForm(forms.ModelForm):
    class Meta:
        model = MedicalVisit
        fields = [
            "profile", "visit_datetime", "reason", "symptoms", "temperature_c",
            "pulse_rate", "blood_pressure", "assessment", "treatment_given",
            "rest_minutes", "parent_notified", "outcome", "follow_up_date",
            "attended_by", "notes",
        ]
        widgets = {
            "visit_datetime": forms.DateTimeInput(attrs={"type": "datetime-local"}),
            "follow_up_date": forms.DateInput(attrs={"type": "date"}),
            "symptoms": forms.Textarea(attrs={"rows": 2}),
            "assessment": forms.Textarea(attrs={"rows": 2}),
            "treatment_given": forms.Textarea(attrs={"rows": 2}),
            "notes": forms.Textarea(attrs={"rows": 2}),
        }


class EmergencyCaseForm(forms.ModelForm):
    class Meta:
        model = EmergencyCase
        fields = [
            "profile", "unknown_patient_note", "incident_datetime", "location",
            "reported_by", "incident_type", "triage_level", "status",
            "initial_condition", "vital_temperature_c", "vital_pulse",
            "vital_blood_pressure", "vital_oxygen_saturation",
            "first_aid_provided", "medicine_administered",
            "parent_contacted", "principal_informed", "ambulance_contacted",
            "hospital_referred", "hospital_name", "referral_reason",
            "attended_by",
        ]
        widgets = {
            "incident_datetime": forms.DateTimeInput(attrs={"type": "datetime-local"}),
            "initial_condition": forms.Textarea(attrs={"rows": 2}),
            "first_aid_provided": forms.Textarea(attrs={"rows": 2}),
            "referral_reason": forms.Textarea(attrs={"rows": 2}),
        }


class EmergencyClosureForm(forms.ModelForm):
    class Meta:
        model = EmergencyCase
        fields = ["final_outcome", "follow_up_date"]
        widgets = {
            "final_outcome": forms.Textarea(attrs={"rows": 2}),
            "follow_up_date": forms.DateInput(attrs={"type": "date"}),
        }


class SickBayAdmissionForm(forms.ModelForm):
    class Meta:
        model = SickBayAdmission
        fields = [
            "profile", "reason", "admission_time", "bed_number",
            "parent_informed", "isolation_required", "status", "notes",
        ]
        widgets = {
            "admission_time": forms.DateTimeInput(attrs={"type": "datetime-local"}),
            "notes": forms.Textarea(attrs={"rows": 2}),
        }


class MedicineForm(forms.ModelForm):
    class Meta:
        model = Medicine
        fields = [
            "name", "generic_name", "category", "strength", "form",
            "prescription_required", "reorder_level", "storage_location",
        ]


class MedicineBatchForm(forms.ModelForm):
    class Meta:
        model = MedicineBatch
        fields = [
            "medicine", "batch_number", "supplier", "quantity_received",
            "quantity_remaining", "purchase_date", "expiry_date",
        ]
        widgets = {
            "purchase_date": forms.DateInput(attrs={"type": "date"}),
            "expiry_date": forms.DateInput(attrs={"type": "date"}),
        }

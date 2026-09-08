"""
Edupilot Health & Wellness Center
----------------------------------
Standalone Django app. Links to the existing admin_panel app via string
references (admin_panel.Student / admin_panel.Employee) so it can be
developed and migrated independently, then wired into admin_panel later
(sidebar entry + urls include + INSTALLED_APPS).

This first pass covers the Phase 1 (Core Health Records) and Phase 2
(Emergency & Treatment) building blocks from the functional design doc.
Phase 3 (Vaccinations / Chronic Conditions detail / Appointments),
Phase 4 (AI features) and Phase 5 (Advanced Wellness) are intentionally
left as clearly-marked extension points — see README.md.
"""

from django.conf import settings
from django.db import models


PATIENT_TYPE_CHOICES = [
    ("student", "Student"),
    ("staff", "Staff"),
    ("visitor", "Visitor"),
]

RISK_LEVEL_CHOICES = [
    ("low", "Low Risk"),
    ("moderate", "Moderate Risk"),
    ("high", "High Risk"),
    ("urgent", "Urgent Review"),
]


class HealthProfile(models.Model):
    """One profile per student / staff member / visitor."""

    patient_type = models.CharField(max_length=10, choices=PATIENT_TYPE_CHOICES)
    student = models.ForeignKey(
        "admin_panel.Student", on_delete=models.CASCADE,
        null=True, blank=True, related_name="health_profile",
    )
    employee = models.ForeignKey(
        "admin_panel.Employee", on_delete=models.CASCADE,
        null=True, blank=True, related_name="health_profile",
    )
    visitor_name = models.CharField(max_length=150, blank=True)

    blood_group = models.CharField(max_length=5, blank=True)
    emergency_contact_name = models.CharField(max_length=150, blank=True)
    emergency_contact_phone = models.CharField(max_length=20, blank=True)

    risk_level = models.CharField(max_length=10, choices=RISK_LEVEL_CHOICES, default="low")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        permissions = [
            ("view_confidential_health_notes", "Can view confidential health notes"),
        ]

    def __str__(self):
        if self.student_id:
            return f"Health Profile: {self.student}"
        if self.employee_id:
            return f"Health Profile: {self.employee}"
        return f"Health Profile: {self.visitor_name or 'Visitor'}"

    @property
    def display_name(self):
        if self.student_id:
            return self.student.full_name
        if self.employee_id:
            return self.employee.name
        return self.visitor_name or "Unknown"


class AllergyRecord(models.Model):
    profile = models.ForeignKey(HealthProfile, on_delete=models.CASCADE, related_name="allergies")
    allergen = models.CharField(max_length=150)
    severity = models.CharField(
        max_length=10,
        choices=[("mild", "Mild"), ("moderate", "Moderate"), ("severe", "Severe")],
        default="mild",
    )
    notes = models.TextField(blank=True)

    def __str__(self):
        return f"{self.allergen} ({self.get_severity_display()})"


class ChronicCondition(models.Model):
    profile = models.ForeignKey(HealthProfile, on_delete=models.CASCADE, related_name="chronic_conditions")
    condition_name = models.CharField(max_length=150)
    diagnosed_on = models.DateField(null=True, blank=True)
    notes = models.TextField(blank=True)
    action_plan_document = models.FileField(upload_to="health/action_plans/", null=True, blank=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.condition_name


class HealthCheckupCycle(models.Model):
    """A monthly / annual / special checkup drive."""

    CHECKUP_TYPE_CHOICES = [
        ("basic_monthly", "Basic Monthly Checkup"),
        ("detailed_annual", "Detailed Annual Checkup"),
        ("special", "Special Checkup"),
    ]

    title = models.CharField(max_length=200)
    campus = models.CharField(max_length=100, blank=True)
    checkup_type = models.CharField(max_length=20, choices=CHECKUP_TYPE_CHOICES, default="basic_monthly")
    patient_type = models.CharField(max_length=20, default="students_and_staff")
    start_date = models.DateField()
    end_date = models.DateField()
    assigned_doctor = models.ForeignKey(
        "admin_panel.Employee", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="checkup_cycles_as_doctor",
    )
    assigned_nurse = models.ForeignKey(
        "admin_panel.Employee", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="checkup_cycles_as_nurse",
    )
    consent_required = models.BooleanField(default=True)
    location = models.CharField(max_length=150, blank=True)
    instructions = models.TextField(blank=True)
    follow_up_deadline = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title


class HealthCheckupRecord(models.Model):
    STATUS_CHOICES = [
        ("not_scheduled", "Not Scheduled"),
        ("scheduled", "Scheduled"),
        ("consent_pending", "Consent Pending"),
        ("in_progress", "In Progress"),
        ("completed", "Completed"),
        ("completed_observation", "Completed with Observation"),
        ("follow_up_required", "Follow-Up Required"),
        ("referred_doctor", "Referred to Doctor"),
        ("referred_hospital", "Referred to Hospital"),
        ("exempted", "Temporarily Exempted"),
        ("absent", "Absent on Checkup Date"),
        ("rescheduled", "Rescheduled"),
        ("closed", "Record Closed"),
    ]
    OUTCOME_CHOICES = [
        ("normal", "Normal"),
        ("observation", "Observation Required"),
        ("follow_up", "Follow-Up Required"),
        ("parent_consult", "Parent Consultation Required"),
        ("doctor_consult", "Doctor Consultation Required"),
        ("lab_test", "Laboratory Test Required"),
        ("specialist", "Specialist Referral Required"),
        ("urgent", "Urgent Medical Attention Required"),
    ]

    cycle = models.ForeignKey(HealthCheckupCycle, on_delete=models.CASCADE, related_name="records")
    profile = models.ForeignKey(HealthProfile, on_delete=models.CASCADE, related_name="checkups")
    scheduled_date = models.DateField(null=True, blank=True)
    checkup_date = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=25, choices=STATUS_CHOICES, default="not_scheduled")

    # Vital signs
    height_cm = models.DecimalField(max_digits=5, decimal_places=1, null=True, blank=True)
    weight_kg = models.DecimalField(max_digits=5, decimal_places=1, null=True, blank=True)
    bmi = models.DecimalField(max_digits=4, decimal_places=1, null=True, blank=True)
    temperature_c = models.DecimalField(max_digits=4, decimal_places=1, null=True, blank=True)
    pulse_rate = models.PositiveIntegerField(null=True, blank=True)
    blood_pressure = models.CharField(max_length=15, blank=True)
    oxygen_saturation = models.PositiveIntegerField(null=True, blank=True)

    current_symptoms = models.TextField(blank=True)
    general_notes = models.TextField(blank=True)

    outcome = models.CharField(max_length=20, choices=OUTCOME_CHOICES, default="normal")
    risk_level = models.CharField(max_length=10, choices=RISK_LEVEL_CHOICES, default="low")
    follow_up_date = models.DateField(null=True, blank=True)
    parent_or_staff_acknowledged = models.BooleanField(default=False)

    examined_by = models.ForeignKey(
        "admin_panel.Employee", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="checkups_conducted",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("cycle", "profile")

    def __str__(self):
        return f"{self.profile.display_name} — {self.cycle.title}"

    def save(self, *args, **kwargs):
        if self.height_cm and self.weight_kg:
            height_m = float(self.height_cm) / 100
            if height_m > 0:
                self.bmi = round(float(self.weight_kg) / (height_m ** 2), 1)
        super().save(*args, **kwargs)


class MedicalVisit(models.Model):
    """Routine medical room visit (not a full emergency)."""

    OUTCOME_CHOICES = [
        ("returned_class", "Returned to Class"),
        ("returned_work", "Returned to Work"),
        ("sick_bay", "Rested in Sick Bay"),
        ("sent_home", "Sent Home"),
        ("parent_collected", "Parent Collected"),
        ("referred_doctor", "Referred to Doctor"),
        ("referred_hospital", "Referred to Hospital"),
        ("emergency_created", "Emergency Case Created"),
        ("follow_up", "Follow-Up Scheduled"),
    ]

    profile = models.ForeignKey(HealthProfile, on_delete=models.CASCADE, related_name="medical_visits")
    visit_datetime = models.DateTimeField()
    reason = models.CharField(max_length=200)
    symptoms = models.TextField(blank=True)
    temperature_c = models.DecimalField(max_digits=4, decimal_places=1, null=True, blank=True)
    pulse_rate = models.PositiveIntegerField(null=True, blank=True)
    blood_pressure = models.CharField(max_length=15, blank=True)
    assessment = models.TextField(blank=True)
    treatment_given = models.TextField(blank=True)
    rest_minutes = models.PositiveIntegerField(null=True, blank=True)
    parent_notified = models.BooleanField(default=False)
    outcome = models.CharField(max_length=20, choices=OUTCOME_CHOICES, default="returned_class")
    follow_up_date = models.DateField(null=True, blank=True)
    attended_by = models.ForeignKey(
        "admin_panel.Employee", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="medical_visits_attended",
    )
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.profile.display_name} — {self.reason} ({self.visit_datetime:%d %b %Y})"


class EmergencyCase(models.Model):
    TRIAGE_CHOICES = [
        (1, "Level 1 — Minor"),
        (2, "Level 2 — Moderate"),
        (3, "Level 3 — Serious"),
        (4, "Level 4 — Critical"),
    ]
    STATUS_CHOICES = [
        ("open", "Open"),
        ("treatment", "Treatment in Progress"),
        ("referred", "Referred to Hospital"),
        ("closed", "Closed"),
    ]

    case_number = models.CharField(max_length=30, unique=True)
    profile = models.ForeignKey(
        HealthProfile, on_delete=models.SET_NULL, null=True, blank=True, related_name="emergency_cases"
    )
    unknown_patient_note = models.CharField(max_length=200, blank=True)

    incident_datetime = models.DateTimeField()
    location = models.CharField(max_length=150, blank=True)
    reported_by = models.CharField(max_length=150, blank=True)
    incident_type = models.CharField(max_length=50)
    triage_level = models.PositiveSmallIntegerField(choices=TRIAGE_CHOICES, default=1)
    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default="open")

    initial_condition = models.TextField(blank=True)
    vital_temperature_c = models.DecimalField(max_digits=4, decimal_places=1, null=True, blank=True)
    vital_pulse = models.PositiveIntegerField(null=True, blank=True)
    vital_blood_pressure = models.CharField(max_length=15, blank=True)
    vital_oxygen_saturation = models.PositiveIntegerField(null=True, blank=True)

    first_aid_provided = models.TextField(blank=True)
    medicine_administered = models.CharField(max_length=200, blank=True)

    parent_contacted = models.BooleanField(default=False)
    principal_informed = models.BooleanField(default=False)
    ambulance_contacted = models.BooleanField(default=False)

    hospital_referred = models.BooleanField(default=False)
    hospital_name = models.CharField(max_length=150, blank=True)
    referral_reason = models.TextField(blank=True)

    final_outcome = models.TextField(blank=True)
    follow_up_date = models.DateField(null=True, blank=True)
    closed_by = models.ForeignKey(
        "admin_panel.Employee", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="emergency_cases_closed",
    )
    closed_at = models.DateTimeField(null=True, blank=True)

    attended_by = models.ForeignKey(
        "admin_panel.Employee", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="emergency_cases_attended",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.case_number

    def save(self, *args, **kwargs):
        if not self.case_number:
            from django.utils import timezone
            stamp = timezone.now().strftime("%Y%m%d%H%M%S")
            self.case_number = f"EMG-{stamp}"
        super().save(*args, **kwargs)


class SickBayAdmission(models.Model):
    profile = models.ForeignKey(HealthProfile, on_delete=models.CASCADE, related_name="sick_bay_admissions")
    reason = models.CharField(max_length=200)
    admission_time = models.DateTimeField()
    discharge_time = models.DateTimeField(null=True, blank=True)
    bed_number = models.CharField(max_length=20, blank=True)
    parent_informed = models.BooleanField(default=False)
    isolation_required = models.BooleanField(default=False)
    status = models.CharField(
        max_length=20,
        choices=[
            ("resting", "Resting"),
            ("awaiting_parent", "Awaiting Parent"),
            ("discharged", "Discharged"),
        ],
        default="resting",
    )
    notes = models.TextField(blank=True)

    def __str__(self):
        return f"{self.profile.display_name} — {self.get_status_display()}"


class Medicine(models.Model):
    name = models.CharField(max_length=150)
    generic_name = models.CharField(max_length=150, blank=True)
    category = models.CharField(max_length=100, blank=True)
    strength = models.CharField(max_length=50, blank=True)
    form = models.CharField(max_length=50, blank=True)
    prescription_required = models.BooleanField(default=False)
    reorder_level = models.PositiveIntegerField(default=10)
    storage_location = models.CharField(max_length=100, blank=True)

    def __str__(self):
        return self.name

    @property
    def current_balance(self):
        return sum(b.quantity_remaining for b in self.batches.all())


class MedicineBatch(models.Model):
    medicine = models.ForeignKey(Medicine, on_delete=models.CASCADE, related_name="batches")
    batch_number = models.CharField(max_length=50)
    supplier = models.CharField(max_length=150, blank=True)
    quantity_received = models.PositiveIntegerField()
    quantity_remaining = models.PositiveIntegerField()
    purchase_date = models.DateField(null=True, blank=True)
    expiry_date = models.DateField()

    def __str__(self):
        return f"{self.medicine.name} — {self.batch_number}"


class MedicineAdministration(models.Model):
    profile = models.ForeignKey(HealthProfile, on_delete=models.CASCADE, related_name="medicines_administered")
    medicine = models.ForeignKey(Medicine, on_delete=models.PROTECT)
    batch = models.ForeignKey(MedicineBatch, on_delete=models.SET_NULL, null=True, blank=True)
    dosage = models.CharField(max_length=100)
    route = models.CharField(max_length=50, blank=True)
    administered_at = models.DateTimeField()
    administered_by = models.ForeignKey(
        "admin_panel.Employee", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="medicines_given",
    )
    reason = models.CharField(max_length=200, blank=True)
    reaction_after = models.TextField(blank=True)
    parent_notified = models.BooleanField(default=False)
    linked_visit = models.ForeignKey(
        MedicalVisit, on_delete=models.SET_NULL, null=True, blank=True, related_name="medicines"
    )
    linked_emergency = models.ForeignKey(
        EmergencyCase, on_delete=models.SET_NULL, null=True, blank=True, related_name="medicines"
    )

    def __str__(self):
        return f"{self.medicine.name} → {self.profile.display_name}"


class HealthNotification(models.Model):
    profile = models.ForeignKey(HealthProfile, on_delete=models.CASCADE, related_name="notifications")
    message = models.CharField(max_length=255)
    category = models.CharField(max_length=50, blank=True)
    sent_at = models.DateTimeField(auto_now_add=True)
    acknowledged = models.BooleanField(default=False)
    acknowledged_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return self.message

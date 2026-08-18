"""
Edupilot Student Counselling & Wellbeing module.
--------------------------------------------------
Standalone Django app, linked to admin_panel via string FKs
(admin_panel.Student / admin_panel.Employee) so it can be developed
and migrated independently, then wired into admin_panel later.

Confidentiality note: counselling case records, session notes and
safeguarding concerns are sensitive by nature. This first pass models
the data and gives every confidential model its own Django permission
(see Meta.permissions) so access can be restricted to counsellors /
safeguarding officers only, separately from general admin_panel staff
permissions. Wiring those permissions into groups, and enforcing them
in every view, is called out in README.md as a required step before
go-live — do not deploy this module to real students without doing
that access-control pass first.
"""

from django.db import models


PRIORITY_CHOICES = [
    ("low", "Low"),
    ("medium", "Medium"),
    ("high", "High"),
    ("urgent", "Urgent — Immediate Safety Concern"),
]

REFERRAL_CATEGORY_CHOICES = [
    ("academic", "Academic Difficulty"),
    ("attendance", "Attendance Concern"),
    ("behaviour", "Behaviour Change"),
    ("bullying", "Bullying"),
    ("peer_conflict", "Peer Conflict"),
    ("family", "Family Concern"),
    ("stress_anxiety", "Stress or Anxiety"),
    ("grief_loss", "Grief or Loss"),
    ("career", "Career Guidance"),
    ("child_protection", "Child Protection Concern"),
]

REFERRAL_SOURCE_CHOICES = [
    ("self", "Student (Self-Referral)"),
    ("teacher", "Teacher"),
    ("parent", "Parent"),
    ("admin", "Administrator"),
    ("nurse", "Nurse / Medical Staff"),
]


class CounsellingReferral(models.Model):
    """The intake form — becomes a Case once accepted by a counsellor."""

    STATUS_CHOICES = [
        ("new", "New"),
        ("under_review", "Under Review"),
        ("accepted", "Accepted — Case Opened"),
        ("declined", "Declined / Redirected"),
    ]

    student = models.ForeignKey(
        "admin_panel.Student", on_delete=models.CASCADE, related_name="counselling_referrals"
    )
    category = models.CharField(max_length=20, choices=REFERRAL_CATEGORY_CHOICES)
    source = models.CharField(max_length=10, choices=REFERRAL_SOURCE_CHOICES)
    referred_by_name = models.CharField(max_length=150, blank=True)
    description = models.TextField(help_text="What prompted this referral?")
    priority = models.CharField(max_length=10, choices=PRIORITY_CHOICES, default="medium")
    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default="new")
    is_emergency_service = models.BooleanField(
        default=False,
        help_text="This form is NOT an emergency service. Urgent/unsafe situations must go through the Safeguarding workflow immediately.",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Referral: {self.student} — {self.get_category_display()}"


class CounsellingCase(models.Model):
    """Confidential case record — opened from an accepted referral."""

    STATUS_CHOICES = [
        ("open", "Open"),
        ("in_progress", "In Progress"),
        ("monitoring", "Monitoring / Follow-Up"),
        ("closed", "Closed"),
    ]

    case_number = models.CharField(max_length=30, unique=True)
    student = models.ForeignKey(
        "admin_panel.Student", on_delete=models.CASCADE, related_name="counselling_cases"
    )
    referral = models.ForeignKey(
        CounsellingReferral, on_delete=models.SET_NULL, null=True, blank=True, related_name="case"
    )
    reason_for_referral = models.TextField()
    priority = models.CharField(max_length=10, choices=PRIORITY_CHOICES, default="medium")
    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default="open")
    assigned_counsellor = models.ForeignKey(
        "admin_panel.Employee", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="counselling_cases",
    )
    support_goals = models.TextField(blank=True)
    follow_up_date = models.DateField(null=True, blank=True)
    outcome = models.TextField(blank=True)
    closure_summary = models.TextField(blank=True)
    opened_at = models.DateTimeField(auto_now_add=True)
    closed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        permissions = [
            ("view_confidential_case", "Can view confidential counselling case records"),
        ]

    def __str__(self):
        return self.case_number

    def save(self, *args, **kwargs):
        if not self.case_number:
            from django.utils import timezone
            stamp = timezone.now().strftime("%Y%m%d%H%M%S")
            self.case_number = f"CASE-{stamp}"
        super().save(*args, **kwargs)


SESSION_TYPE_CHOICES = [
    ("initial_assessment", "Initial Assessment"),
    ("individual", "Individual Counselling"),
    ("group", "Group Counselling"),
    ("parent_meeting", "Parent Meeting"),
    ("teacher_consultation", "Teacher Consultation"),
    ("crisis_response", "Crisis Response"),
    ("follow_up", "Follow-Up Session"),
    ("case_closure", "Case Closure"),
]


class CounsellingSession(models.Model):
    """Structured, confidential session note. Locked once approved."""

    case = models.ForeignKey(CounsellingCase, on_delete=models.CASCADE, related_name="sessions")
    session_type = models.CharField(max_length=25, choices=SESSION_TYPE_CHOICES)
    session_datetime = models.DateTimeField()
    conducted_by = models.ForeignKey(
        "admin_panel.Employee", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="counselling_sessions_conducted",
    )
    notes = models.TextField()
    next_steps = models.TextField(blank=True)
    is_locked = models.BooleanField(
        default=False, help_text="Once approved/locked, notes should not be edited further."
    )
    created_by = models.ForeignKey(
        "admin_panel.Employee", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="counselling_sessions_created",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        permissions = [
            ("view_confidential_session_note", "Can view confidential counselling session notes"),
        ]
        ordering = ["-session_datetime"]

    def __str__(self):
        return f"{self.get_session_type_display()} — {self.case.case_number}"


class StudentSupportPlan(models.Model):
    case = models.OneToOneField(CounsellingCase, on_delete=models.CASCADE, related_name="support_plan")
    main_concern = models.TextField()
    student_strengths = models.TextField(blank=True)
    short_term_goals = models.TextField(blank=True)
    long_term_goals = models.TextField(blank=True)
    planned_interventions = models.TextField(blank=True)
    responsible_staff = models.CharField(max_length=200, blank=True)
    review_date = models.DateField(null=True, blank=True)
    progress_indicators = models.TextField(blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Support Plan — {self.case.case_number}"


class CounsellingAppointment(models.Model):
    STATUS_CHOICES = [
        ("requested", "Requested"),
        ("confirmed", "Confirmed"),
        ("completed", "Completed"),
        ("missed", "Missed"),
        ("cancelled", "Cancelled"),
        ("rescheduled", "Rescheduled"),
    ]
    MODE_CHOICES = [("in_person", "In Person"), ("online", "Online")]

    student = models.ForeignKey(
        "admin_panel.Student", on_delete=models.CASCADE, related_name="counselling_appointments"
    )
    case = models.ForeignKey(
        CounsellingCase, on_delete=models.SET_NULL, null=True, blank=True, related_name="appointments"
    )
    counsellor = models.ForeignKey(
        "admin_panel.Employee", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="counselling_appointments",
    )
    scheduled_datetime = models.DateTimeField()
    mode = models.CharField(max_length=10, choices=MODE_CHOICES, default="in_person")
    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default="requested")
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.student} — {self.scheduled_datetime:%d %b %Y %H:%M}"


class WellbeingCheckIn(models.Model):
    """Short, age-appropriate self check-in. Screening only — not a diagnosis."""

    student = models.ForeignKey(
        "admin_panel.Student", on_delete=models.CASCADE, related_name="wellbeing_checkins"
    )
    submitted_at = models.DateTimeField(auto_now_add=True)
    mood_rating = models.PositiveSmallIntegerField(help_text="1 (low) – 5 (great)")
    stress_rating = models.PositiveSmallIntegerField(help_text="1 (calm) – 5 (very stressed)")
    feels_safe_at_school = models.BooleanField(default=True)
    sleep_difficulty = models.BooleanField(default=False)
    wants_to_talk_to_someone = models.BooleanField(default=False)
    what_is_affecting_you = models.CharField(max_length=255, blank=True)

    def __str__(self):
        return f"Check-in: {self.student} — {self.submitted_at:%d %b}"


class SafeguardingConcern(models.Model):
    """
    Controlled, restricted-access workflow for bullying, abuse/neglect,
    self-harm, threats, unsafe home situations, etc.

    Urgent cases must go directly to trained staff and must NEVER wait
    for any automated/AI review — this model has no automated triage,
    by design.
    """

    CONCERN_TYPE_CHOICES = [
        ("bullying", "Bullying"),
        ("harassment", "Harassment"),
        ("abuse_neglect", "Abuse or Neglect Concern"),
        ("self_harm", "Self-Harm Concern"),
        ("violence_threat", "Threat of Violence"),
        ("unsafe_home", "Unsafe Home Situation"),
        ("other_safety", "Other Immediate Safety Concern"),
    ]
    RISK_LEVEL_CHOICES = [
        ("low", "Low"),
        ("medium", "Medium"),
        ("high", "High"),
        ("critical", "Critical — Immediate Action"),
    ]
    STATUS_CHOICES = [
        ("reported", "Reported"),
        ("safeguarding_officer_notified", "Safeguarding Officer Notified"),
        ("action_in_progress", "Action In Progress"),
        ("external_referral", "External Referral Made"),
        ("closed", "Closed"),
    ]

    student = models.ForeignKey(
        "admin_panel.Student", on_delete=models.CASCADE, related_name="safeguarding_concerns"
    )
    concern_type = models.CharField(max_length=20, choices=CONCERN_TYPE_CHOICES)
    risk_level = models.CharField(max_length=10, choices=RISK_LEVEL_CHOICES, default="medium")
    status = models.CharField(max_length=35, choices=STATUS_CHOICES, default="reported")
    reported_by_name = models.CharField(max_length=150)
    description = models.TextField()
    immediate_action_taken = models.TextField(blank=True)
    safeguarding_officer = models.ForeignKey(
        "admin_panel.Employee", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="safeguarding_concerns_handled",
    )
    parent_contact_decision = models.CharField(max_length=255, blank=True)
    external_referral_made = models.BooleanField(default=False)
    external_referral_details = models.TextField(blank=True)
    safety_plan = models.TextField(blank=True)
    reported_at = models.DateTimeField(auto_now_add=True)
    closed_at = models.DateTimeField(null=True, blank=True)
    closure_notes = models.TextField(blank=True)

    class Meta:
        permissions = [
            ("view_safeguarding_concern", "Can view safeguarding concerns (restricted)"),
        ]

    def __str__(self):
        return f"Safeguarding: {self.student} — {self.get_concern_type_display()}"


class ExternalReferralContact(models.Model):
    CATEGORY_CHOICES = [
        ("clinical_psychologist", "Clinical Psychologist"),
        ("psychiatrist", "Psychiatrist"),
        ("child_protection", "Child Protection Services"),
        ("speech_therapist", "Speech Therapist"),
        ("occupational_therapist", "Occupational Therapist"),
        ("special_education", "Special Education Professional"),
        ("rehabilitation", "Rehabilitation Centre"),
        ("hospital_emergency", "Hospital / Emergency Services"),
    ]
    name = models.CharField(max_length=150)
    category = models.CharField(max_length=25, choices=CATEGORY_CHOICES)
    phone = models.CharField(max_length=30, blank=True)
    email = models.EmailField(blank=True)
    address = models.CharField(max_length=255, blank=True)
    notes = models.TextField(blank=True)

    def __str__(self):
        return f"{self.name} ({self.get_category_display()})"

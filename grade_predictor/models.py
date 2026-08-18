"""
Grade Predictor models.

Matches your actual EduPilot models:
  - student_profile.models.Student   (fields used: id, name, roll_no, class_fk)
  - admin_panel.models.Subject       (fields used: id, name)
  - admin_panel.models.Class         (fields used: id, class_name)
  - teacher_dashboard.models.Teacher (linked via request.user)
"""

from django.conf import settings
from django.db import models
from django.utils import timezone


# ---------------------------------------------------------------------------
# 17. Admin Configuration
# ---------------------------------------------------------------------------
class GradePredictorConfig(models.Model):
    """
    One row per school (or per campus, if Edupilot is multi-campus).
    Admin -> Examination -> Grade Predictor Settings maps to this model.
    """

    school_name = models.CharField(max_length=255, default="Default Campus")

    # Grading scale, e.g. {"A+": [90,100], "A": [80,89], "B": [70,79], ...}
    grading_scale = models.JSONField(
        default=dict,
        help_text="Grade boundaries — keep grade keys aligned with "
                   "exam_system.CentralizedResult.GRADE_CHOICES (A+, A, B, C, D, F), "
                   "e.g. {'A+': [90,100], 'A': [80,89], 'B': [70,79]}",
    )

    # Assessment category weightages, e.g.
    # {"quiz": 10, "assignment": 15, "class_test": 15, "midterm": 25, "final_exam": 35}
    assessment_weightages = models.JSONField(
        default=dict,
        help_text="Weight (%) per assessment category, must sum to 100",
    )

    minimum_data_requirement = models.PositiveIntegerField(
        default=2,
        help_text="Minimum number of graded assessments before a prediction is shown",
    )

    # Risk thresholds on predicted %, e.g. {"low":70, "moderate":60, "high":50}
    risk_thresholds = models.JSONField(
        default=dict,
        help_text="Predicted-score cutoffs, e.g. {'low':70,'moderate':60,'high':50,'critical':0}",
    )

    # Confidence thresholds based on number of assessments recorded
    confidence_thresholds = models.JSONField(
        default=dict,
        help_text="e.g. {'high':5, 'medium':3, 'low':0} -> min assessment count for each level",
    )

    prediction_refresh_frequency_hours = models.PositiveIntegerField(default=24)

    parent_visibility = models.BooleanField(default=True)
    student_visibility = models.BooleanField(default=True)
    teacher_access = models.BooleanField(default=True)
    alerts_enabled = models.BooleanField(default=True)
    alert_min_change_points = models.PositiveIntegerField(
        default=5, help_text="Suppress alerts for changes smaller than this (spec section 16)"
    )

    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Grade Predictor Configuration"
        verbose_name_plural = "Grade Predictor Configuration"

    def __str__(self):
        return f"Grade Predictor Config — {self.school_name}"


# ---------------------------------------------------------------------------
# 3 / 4 / 6. Subject-level prediction (cached — recalculated by the service)
# ---------------------------------------------------------------------------
class StudentGradePrediction(models.Model):
    TREND_CHOICES = [
        ("rapidly_improving", "Rapidly Improving"),
        ("improving", "Improving"),
        ("stable", "Stable"),
        ("declining", "Declining"),
        ("high_risk", "High Risk"),
    ]
    CONFIDENCE_CHOICES = [
        ("high", "High"),
        ("medium", "Medium"),
        ("low", "Low"),
    ]
    RISK_CHOICES = [
        ("low", "Low"),
        ("moderate", "Moderate"),
        ("high", "High"),
        ("critical", "Critical"),
    ]

    student = models.ForeignKey(
        "student_profile.Student", on_delete=models.CASCADE, related_name="grade_predictions"
    )
    subject = models.ForeignKey(
        "admin_panel.Subject", on_delete=models.CASCADE, related_name="grade_predictions"
    )
    class_room = models.ForeignKey(
        "admin_panel.Class", on_delete=models.CASCADE, related_name="grade_predictions",
        null=True, blank=True,
    )

    current_score = models.FloatField(help_text="Weighted score from graded assessments so far")
    predicted_score = models.FloatField()
    predicted_score_low = models.FloatField(help_text="Lower bound of prediction range")
    predicted_score_high = models.FloatField(help_text="Upper bound of prediction range")
    predicted_grade = models.CharField(max_length=5)

    # Grade probability distribution, e.g. {"A+":18,"A":57,"B":21,"C":4}
    grade_probability = models.JSONField(default=dict)

    confidence_level = models.CharField(max_length=10, choices=CONFIDENCE_CHOICES, default="low")
    confidence_pct = models.FloatField(default=0)

    trend = models.CharField(max_length=20, choices=TREND_CHOICES, default="stable")
    risk_level = models.CharField(max_length=10, choices=RISK_CHOICES, default="low")

    assessments_used = models.PositiveIntegerField(default=0)

    explanation = models.JSONField(
        default=dict,
        help_text="Factor -> qualitative label, e.g. {'Assignments':'Strong','Attendance':'Good'}",
    )
    weak_topics = models.JSONField(default=list)
    strong_topics = models.JSONField(default=list)

    last_calculated = models.DateTimeField(default=timezone.now)

    class Meta:
        unique_together = ("student", "subject")
        ordering = ["student__id", "subject__name"]

    def __str__(self):
        return f"{self.student} — {self.subject}: {self.predicted_grade} ({self.predicted_score:.1f}%)"


# ---------------------------------------------------------------------------
# Trend history points, used to draw the Performance Trend Engine (section 5)
# ---------------------------------------------------------------------------
class PredictionHistory(models.Model):
    prediction = models.ForeignKey(
        StudentGradePrediction, on_delete=models.CASCADE, related_name="history"
    )
    label = models.CharField(max_length=100, help_text="e.g. 'Assessment 1', 'Midterm'")
    score = models.FloatField()
    recorded_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ["recorded_at"]


# ---------------------------------------------------------------------------
# 14. Teacher Intervention
# ---------------------------------------------------------------------------
class GradeRiskIntervention(models.Model):
    STATUS_CHOICES = [
        ("open", "Open"),
        ("in_progress", "In Progress"),
        ("completed", "Completed"),
    ]

    prediction = models.ForeignKey(
        StudentGradePrediction, on_delete=models.CASCADE, related_name="interventions"
    )
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    note = models.TextField(blank=True)
    action = models.CharField(
        max_length=255, help_text="e.g. 'Assign remedial Algebra class'"
    )
    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default="open")
    created_at = models.DateTimeField(auto_now_add=True)
    resolved_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]


# ---------------------------------------------------------------------------
# 16. Prediction alerts
# ---------------------------------------------------------------------------
class PredictionAlert(models.Model):
    ALERT_TYPES = [
        ("improved", "Grade Prediction Improved"),
        ("risk", "Performance Risk"),
        ("target_reached", "Target Within Reach"),
    ]

    prediction = models.ForeignKey(
        StudentGradePrediction, on_delete=models.CASCADE, related_name="alerts"
    )
    alert_type = models.CharField(max_length=20, choices=ALERT_TYPES)
    message = models.CharField(max_length=255)
    old_grade = models.CharField(max_length=5, blank=True)
    new_grade = models.CharField(max_length=5, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    seen = models.BooleanField(default=False)

    class Meta:
        ordering = ["-created_at"]

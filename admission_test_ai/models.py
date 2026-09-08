from django.conf import settings
from django.db import models


# NOTE: Candidate identity is NOT duplicated here. This app deliberately links
# back to admin_panel.Admission (the existing "Student Gateway"/"Student
# Management" candidate record) and admin_panel.Class / admin_panel.Subject,
# so there is one source of truth for who the candidate is.

DIFFICULTY_CHOICES = [
    ("easy", "Easy"),
    ("age_appropriate", "Age Appropriate"),
    ("moderate", "Moderate"),
    ("advanced", "Advanced / Challenging"),
]

BLOOM_CHOICES = [
    ("remember", "Remember"),
    ("understand", "Understand"),
    ("apply", "Apply"),
    ("analyze", "Analyze"),
    ("evaluate", "Evaluate"),
    ("create", "Create"),
]

QUESTION_TYPE_CHOICES = [
    ("mcq", "MCQ"),
    ("true_false", "True / False"),
    ("fill_blank", "Fill in the Blanks"),
    ("matching", "Matching"),
    ("short_answer", "Short Answer"),
    ("long_answer", "Long Answer"),
    ("comprehension", "Comprehension"),
    ("problem_solving", "Problem Solving"),
    ("mental_math", "Mental Mathematics"),
    ("creative_writing", "Creative Writing"),
    ("diagram_based", "Diagram Based"),
    ("scenario", "Scenario Question"),
    ("logical_reasoning", "Logical Reasoning"),
]

PAPER_STATUS_CHOICES = [
    ("ai_generated", "AI Generated"),
    ("subject_teacher_review", "Subject Teacher Review"),
    ("coordinator_review", "Academic Coordinator Review"),
    ("approved", "Approved"),
    ("locked", "Locked / Finalized"),
]

TEST_MODE_CHOICES = [
    ("online", "Online"),
    ("printed", "Printed"),
]

RECOMMENDATION_CHOICES = [
    ("highly_recommended", "Highly Recommended"),
    ("recommended", "Recommended"),
    ("recommended_support", "Recommended with Academic Support"),
    ("further_assessment", "Further Assessment Required"),
    ("not_recommended", "Not Recommended at Present"),
]


class TestBlueprint(models.Model):
    """A saved, reusable admission-test blueprint for a grade/program,
    e.g. Grade 6 admission test: English 20q/25 marks/25 min, etc."""

    name = models.CharField(max_length=150)
    applying_class = models.ForeignKey(
        "admin_panel.Class", on_delete=models.CASCADE, related_name="admission_blueprints"
    )
    curriculum = models.CharField(max_length=100, default="School Standard")
    total_questions = models.PositiveIntegerField(default=0)
    total_marks = models.PositiveIntegerField(default=0)
    total_time_minutes = models.PositiveIntegerField(default=0)
    difficulty_easy_pct = models.PositiveSmallIntegerField(default=30)
    difficulty_age_appropriate_pct = models.PositiveSmallIntegerField(default=40)
    difficulty_moderate_pct = models.PositiveSmallIntegerField(default=20)
    difficulty_advanced_pct = models.PositiveSmallIntegerField(default=10)
    passing_percentage = models.PositiveSmallIntegerField(default=60)
    is_active = models.BooleanField(default=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.name} ({self.applying_class})"

    def recompute_totals(self):
        agg = self.subjects.aggregate(
            q=models.Sum("num_questions"), m=models.Sum("marks"), t=models.Sum("time_minutes")
        )
        self.total_questions = agg["q"] or 0
        self.total_marks = agg["m"] or 0
        self.total_time_minutes = agg["t"] or 0
        self.save(update_fields=["total_questions", "total_marks", "total_time_minutes"])


class BlueprintSubject(models.Model):
    """One row of the blueprint table, e.g. Mathematics: 20 questions / 25 marks / 30 min."""

    blueprint = models.ForeignKey(TestBlueprint, on_delete=models.CASCADE, related_name="subjects")
    subject = models.ForeignKey("admin_panel.Subject", on_delete=models.CASCADE)
    num_questions = models.PositiveIntegerField(default=0)
    marks = models.PositiveIntegerField(default=0)
    time_minutes = models.PositiveIntegerField(default=0)
    topics = models.TextField(blank=True, help_text="Comma-separated topics/chapters to draw from")

    class Meta:
        unique_together = ("blueprint", "subject")
        ordering = ["id"]

    def __str__(self):
        return f"{self.blueprint.name} - {self.subject}"


class AdmissionQuestion(models.Model):
    """A single AI-generated (or manually authored) admission-test question."""

    blueprint_subject = models.ForeignKey(
        BlueprintSubject, on_delete=models.CASCADE, related_name="questions"
    )
    question_text = models.TextField()
    question_type = models.CharField(max_length=30, choices=QUESTION_TYPE_CHOICES, default="mcq")
    options = models.JSONField(blank=True, null=True, help_text="List of options for MCQ/matching")
    correct_answer = models.TextField(blank=True)
    marking_rubric = models.JSONField(
        blank=True, null=True, help_text="Rubric criteria for descriptive/creative questions"
    )
    marks = models.PositiveIntegerField(default=1)
    difficulty = models.CharField(max_length=20, choices=DIFFICULTY_CHOICES, default="age_appropriate")
    bloom_level = models.CharField(max_length=20, choices=BLOOM_CHOICES, default="understand")
    topic = models.CharField(max_length=150, blank=True)
    skill = models.CharField(max_length=150, blank=True)
    is_ai_generated = models.BooleanField(default=True)
    ai_quality_notes = models.JSONField(
        blank=True, null=True, help_text="Language/age-suitability/ambiguity/curriculum quality-check output"
    )
    duplicate_flag = models.CharField(
        max_length=255, blank=True, help_text="Set when AI duplicate-detection finds a similar past question"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.question_text[:60]


class GeneratedPaper(models.Model):
    """A finalized admission test paper (one version, e.g. Paper A) built from a blueprint."""

    blueprint = models.ForeignKey(TestBlueprint, on_delete=models.CASCADE, related_name="papers")
    version_label = models.CharField(max_length=5, default="A", help_text="A, B, C, D ...")
    status = models.CharField(max_length=30, choices=PAPER_STATUS_CHOICES, default="ai_generated")
    questions = models.ManyToManyField(AdmissionQuestion, related_name="papers", blank=True)
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="admission_papers_reviewed",
    )
    review_notes = models.TextField(blank=True)
    generated_at = models.DateTimeField(auto_now_add=True)
    approved_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = ("blueprint", "version_label")
        ordering = ["-generated_at"]

    def __str__(self):
        return f"{self.blueprint.name} - Paper {self.version_label}"

    @property
    def total_marks(self):
        return sum(q.marks for q in self.questions.all())


class TestSchedule(models.Model):
    """When/where a specific candidate sits a specific admission-test paper."""

    candidate = models.ForeignKey(
        "admin_panel.Admission", on_delete=models.CASCADE, related_name="admission_test_schedules"
    )
    paper = models.ForeignKey(GeneratedPaper, on_delete=models.PROTECT, related_name="schedules")
    test_date = models.DateField()
    test_time = models.TimeField()
    campus = models.CharField(max_length=150, blank=True)
    room = models.CharField(max_length=100, blank=True)
    mode = models.CharField(max_length=10, choices=TEST_MODE_CHOICES, default="online")
    invigilator = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True
    )
    parent_notified = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["test_date", "test_time"]

    def __str__(self):
        return f"{self.candidate} - {self.test_date}"


class TestAttempt(models.Model):
    """A candidate's actual attempt at their scheduled paper."""

    STATUS_CHOICES = [
        ("scheduled", "Scheduled"),
        ("in_progress", "In Progress"),
        ("submitted", "Submitted"),
        ("awaiting_evaluation", "Awaiting Evaluation"),
        ("evaluated", "Evaluated"),
    ]

    schedule = models.OneToOneField(TestSchedule, on_delete=models.CASCADE, related_name="attempt")
    status = models.CharField(max_length=25, choices=STATUS_CHOICES, default="scheduled")
    started_at = models.DateTimeField(null=True, blank=True)
    submitted_at = models.DateTimeField(null=True, blank=True)
    overall_score_pct = models.FloatField(null=True, blank=True)

    def __str__(self):
        return f"Attempt: {self.schedule}"


class AttemptAnswer(models.Model):
    attempt = models.ForeignKey(TestAttempt, on_delete=models.CASCADE, related_name="answers")
    question = models.ForeignKey(AdmissionQuestion, on_delete=models.CASCADE)
    answer_text = models.TextField(blank=True)
    is_auto_checked = models.BooleanField(default=False)
    is_correct = models.BooleanField(null=True, blank=True)
    ai_suggested_marks = models.FloatField(null=True, blank=True)
    marks_awarded = models.FloatField(null=True, blank=True)
    teacher_approved = models.BooleanField(default=False)

    class Meta:
        unique_together = ("attempt", "question")


class ReadinessReport(models.Model):
    """Diagnostic subject-wise breakdown + strengths/areas for support, per attempt."""

    attempt = models.OneToOneField(TestAttempt, on_delete=models.CASCADE, related_name="readiness_report")
    subject_scores = models.JSONField(default=dict, blank=True, help_text='{"English": 81, "Mathematics": 68, ...}')
    strengths = models.JSONField(default=list, blank=True)
    areas_for_support = models.JSONField(default=list, blank=True)
    is_borderline = models.BooleanField(default=False)
    borderline_note = models.TextField(blank=True)
    ai_interview_questions = models.JSONField(default=list, blank=True)
    generated_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Readiness report - {self.attempt}"


class AdmissionRecommendation(models.Model):
    """Weighted recommendation combining academic test, previous results, interview, observation."""

    candidate = models.ForeignKey(
        "admin_panel.Admission", on_delete=models.CASCADE, related_name="admission_ai_recommendations"
    )
    readiness_report = models.ForeignKey(
        ReadinessReport, on_delete=models.SET_NULL, null=True, blank=True
    )
    academic_test_weight_pct = models.PositiveSmallIntegerField(default=60)
    previous_results_weight_pct = models.PositiveSmallIntegerField(default=15)
    interview_weight_pct = models.PositiveSmallIntegerField(default=15)
    teacher_observation_weight_pct = models.PositiveSmallIntegerField(default=10)
    computed_score_pct = models.FloatField(null=True, blank=True)
    recommendation = models.CharField(max_length=30, choices=RECOMMENDATION_CHOICES, blank=True)
    ai_notes = models.TextField(blank=True)
    decided_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True
    )
    final_decision = models.CharField(
        max_length=30,
        blank=True,
        choices=[
            ("accepted", "Accepted"),
            ("accepted_conditions", "Accepted with Conditions"),
            ("waitlisted", "Waitlisted"),
            ("reassessment", "Reassessment Required"),
            ("rejected", "Rejected"),
        ],
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Recommendation - {self.candidate}"

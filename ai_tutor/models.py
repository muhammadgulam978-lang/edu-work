from django.db import models
from django.utils import timezone


class AITutorSession(models.Model):
    SESSION_TYPES = [
        ("learn", "Learn"),
        ("revise", "Revise"),
        ("practice", "Practice"),
        ("homework_help", "Homework Help"),
        ("exam_prep", "Exam Preparation"),
        ("ask", "Ask a Question"),
    ]
    STATUS_CHOICES = [
        ("active", "Active"),
        ("closed", "Closed"),
    ]

    student = models.ForeignKey(
        "student_profile.Student",
        on_delete=models.CASCADE,
        related_name="ai_tutor_sessions",
    )
    subject = models.ForeignKey(
        "admin_panel.Subject",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="ai_tutor_sessions",
    )
    topic = models.CharField(max_length=255, blank=True)
    session_type = models.CharField(max_length=30, choices=SESSION_TYPES, default="learn")
    language = models.CharField(max_length=50, default="English")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="active")
    started_at = models.DateTimeField(default=timezone.now)
    ended_at = models.DateTimeField(null=True, blank=True)
    total_messages = models.PositiveIntegerField(default=0)
    total_tokens = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["-started_at"]

    def __str__(self):
        return f"{self.student} - {self.subject or 'General'} - {self.topic}"


class AITutorMessage(models.Model):
    SENDER_TYPES = [
        ("student", "Student"),
        ("assistant", "Assistant"),
        ("system", "System"),
    ]
    SAFETY_STATUS = [
        ("allowed", "Allowed"),
        ("blocked", "Blocked"),
        ("needs_review", "Needs Review"),
        ("error", "Error"),
    ]

    session = models.ForeignKey(
        AITutorSession,
        on_delete=models.CASCADE,
        related_name="messages",
    )
    student = models.ForeignKey(
        "student_profile.Student",
        on_delete=models.CASCADE,
        related_name="ai_tutor_messages",
    )
    sender_type = models.CharField(max_length=20, choices=SENDER_TYPES)
    message_text = models.TextField(blank=True)
    response_text = models.TextField(blank=True)
    intent = models.CharField(max_length=50, blank=True)
    model_name = models.CharField(max_length=100, blank=True)
    safety_status = models.CharField(max_length=20, choices=SAFETY_STATUS, default="allowed")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]

    def __str__(self):
        return f"{self.sender_type} message for session {self.session_id}"


class StudentTopicMastery(models.Model):
    MASTERY_LEVELS = [
        ("not_started", "Not Started"),
        ("introduced", "Introduced"),
        ("developing", "Developing"),
        ("practicing", "Practicing"),
        ("mastered", "Mastered"),
        ("needs_revision", "Needs Revision"),
    ]

    student = models.ForeignKey(
        "student_profile.Student",
        on_delete=models.CASCADE,
        related_name="ai_topic_mastery",
    )
    subject = models.ForeignKey(
        "admin_panel.Subject",
        on_delete=models.CASCADE,
        related_name="ai_topic_mastery",
    )
    topic = models.CharField(max_length=255)
    mastery_level = models.CharField(max_length=30, choices=MASTERY_LEVELS, default="introduced")
    accuracy_percentage = models.FloatField(default=0)
    attempts = models.PositiveIntegerField(default=0)
    last_practiced_at = models.DateTimeField(null=True, blank=True)
    recommended_action = models.TextField(blank=True)

    class Meta:
        unique_together = ("student", "subject", "topic")
        ordering = ["subject__name", "topic"]

    def __str__(self):
        return f"{self.student} - {self.subject} - {self.topic}: {self.mastery_level}"


class AIPracticeAttempt(models.Model):
    student = models.ForeignKey(
        "student_profile.Student",
        on_delete=models.CASCADE,
        related_name="ai_practice_attempts",
    )
    session = models.ForeignKey(
        AITutorSession,
        on_delete=models.CASCADE,
        related_name="practice_attempts",
    )
    subject = models.ForeignKey(
        "admin_panel.Subject",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="ai_practice_attempts",
    )
    topic = models.CharField(max_length=255, blank=True)
    question_text = models.TextField()
    expected_answer = models.TextField(blank=True)
    expected_concepts = models.JSONField(default=list, blank=True)
    student_answer = models.TextField(blank=True)
    is_correct = models.BooleanField(null=True, blank=True)
    score = models.FloatField(null=True, blank=True)
    hint_used = models.BooleanField(default=False)
    attempt_number = models.PositiveIntegerField(default=1)
    feedback = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    answered_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Practice attempt {self.id} - {self.student}"


class StudentAIPreference(models.Model):
    student = models.OneToOneField(
        "student_profile.Student",
        on_delete=models.CASCADE,
        related_name="ai_preference",
    )
    preferred_language = models.CharField(max_length=50, default="English")
    explanation_style = models.CharField(max_length=50, default="simple")
    default_difficulty = models.CharField(max_length=50, default="easy")
    voice_enabled = models.BooleanField(default=False)
    accessibility_preferences = models.JSONField(default=dict, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"AI preferences for {self.student}"


class AIKnowledgeDocument(models.Model):
    DOCUMENT_TYPES = [
        ("curriculum", "Curriculum"),
        ("teacher_note", "Teacher Note"),
        ("book", "Book"),
        ("chapter", "Chapter"),
        ("topic", "Topic"),
        ("lesson_plan", "Lesson Plan"),
        ("worksheet", "Worksheet"),
        ("assignment", "Assignment"),
        ("quiz", "Quiz"),
    ]
    ACCESS_LEVELS = [
        ("student", "Student"),
        ("teacher", "Teacher"),
        ("admin", "Admin"),
    ]
    APPROVAL_STATUS = [
        ("approved", "Approved"),
        ("draft", "Draft"),
        ("archived", "Archived"),
    ]

    title = models.CharField(max_length=255)
    content = models.TextField()
    document_type = models.CharField(max_length=50, choices=DOCUMENT_TYPES)
    class_fk = models.ForeignKey(
        "admin_panel.Class",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="ai_knowledge_documents",
    )
    section = models.ForeignKey(
        "admin_panel.Section",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="ai_knowledge_documents",
    )
    subject = models.ForeignKey(
        "admin_panel.Subject",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="ai_knowledge_documents",
    )
    chapter_title = models.CharField(max_length=255, blank=True)
    topic = models.CharField(max_length=255, blank=True)
    access_level = models.CharField(max_length=30, choices=ACCESS_LEVELS, default="student")
    approval_status = models.CharField(max_length=30, choices=APPROVAL_STATUS, default="approved")
    source_model = models.CharField(max_length=100, blank=True)
    source_id = models.PositiveIntegerField(null=True, blank=True)
    source_reference = models.CharField(max_length=255, blank=True)
    vector_reference = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=["class_fk", "section", "subject", "approval_status", "access_level"]),
            models.Index(fields=["document_type", "source_model", "source_id"]),
        ]
        ordering = ["title"]

    def __str__(self):
        return self.title


class AIAuditLog(models.Model):
    student = models.ForeignKey(
        "student_profile.Student",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="ai_audit_logs",
    )
    session = models.ForeignKey(
        AITutorSession,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="audit_logs",
    )
    action_type = models.CharField(max_length=100)
    model_used = models.CharField(max_length=100, blank=True)
    retrieved_document_ids = models.JSONField(default=list, blank=True)
    safety_flags = models.JSONField(default=list, blank=True)
    access_result = models.CharField(max_length=50, default="allowed")
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.action_type} - {self.access_result}"

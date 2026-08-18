import uuid

from django.conf import settings
from django.db import models
from django.utils import timezone


class AdminAIConversation(models.Model):
    title = models.CharField(max_length=180, default="Admin AI Conversation")
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updated_at"]

    def __str__(self):
        return self.title


class AdminAIMessage(models.Model):
    SENDER_CHOICES = [
        ("admin", "Admin"),
        ("assistant", "Assistant"),
        ("system", "System"),
    ]

    conversation = models.ForeignKey(AdminAIConversation, on_delete=models.CASCADE, related_name="messages")
    sender = models.CharField(max_length=20, choices=SENDER_CHOICES)
    content = models.TextField()
    intent = models.CharField(max_length=80, blank=True, default="")
    tool_name = models.CharField(max_length=120, blank=True, default="")
    payload = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]

    def __str__(self):
        return f"{self.conversation_id} - {self.sender}"


class AdminAIToolAuditLog(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    conversation = models.ForeignKey(AdminAIConversation, on_delete=models.SET_NULL, null=True, blank=True)
    tool_name = models.CharField(max_length=120)
    query = models.TextField(blank=True, default="")
    filters = models.JSONField(default=dict, blank=True)
    result_summary = models.TextField(blank=True, default="")
    status = models.CharField(max_length=30, default="success")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.tool_name} - {self.status}"


class AdminAIReport(models.Model):
    REPORT_TYPES = [
        ("executive", "Executive Summary"),
        ("attendance", "Attendance Report"),
        ("fees", "Fee Collection Report"),
        ("admissions", "Admissions Report"),
        ("fixtures", "Timetable / Fixture Report"),
        ("teacher_workload", "Teacher Workload Report"),
        ("student_risk", "Student Risk Report"),
        ("ai_tutor", "AI Tutor Usage Report"),
        ("full", "Full AI Analytics Report"),
    ]

    SHARE_STATUS_CHOICES = [
        ("not_shared", "Not Shared"),
        ("sent", "Sent"),
        ("failed", "Failed"),
    ]

    uuid = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    title = models.CharField(max_length=180)
    report_type = models.CharField(max_length=40, choices=REPORT_TYPES, default="full")
    generated_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    snapshot_data = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    share_emails = models.JSONField(default=list, blank=True)
    last_shared_at = models.DateTimeField(null=True, blank=True)
    share_status = models.CharField(max_length=30, choices=SHARE_STATUS_CHOICES, default="not_shared")

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.title

    def mark_shared(self, emails):
        self.share_emails = emails
        self.share_status = "sent"
        self.last_shared_at = timezone.now()
        self.save(update_fields=["share_emails", "share_status", "last_shared_at"])


class AdminAIReportShareLog(models.Model):
    CHANNEL_CHOICES = [
        ("email", "Email"),
        ("internal_link", "Internal Link"),
        ("whatsapp", "WhatsApp"),
        ("facebook", "Facebook"),
        ("x", "X / Twitter"),
        ("download", "Download"),
    ]
    STATUS_CHOICES = [
        ("sent", "Sent"),
        ("failed", "Failed"),
        ("copied", "Copied"),
        ("downloaded", "Downloaded"),
    ]

    report = models.ForeignKey(AdminAIReport, on_delete=models.CASCADE, related_name="share_logs")
    shared_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    channel = models.CharField(max_length=30, choices=CHANNEL_CHOICES)
    recipients = models.JSONField(default=list, blank=True)
    status = models.CharField(max_length=30, choices=STATUS_CHOICES)
    message = models.TextField(blank=True, default="")
    error_message = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.report_id} - {self.channel} - {self.status}"


class AdminAIStudentProfileSnapshot(models.Model):
    uuid = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    student_id = models.CharField(max_length=40)
    viewed_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    snapshot_data = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.student_id} - {self.created_at:%Y-%m-%d}"


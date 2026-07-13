from django.contrib import admin

from .models import (
    AIAuditLog,
    AIKnowledgeDocument,
    AIPracticeAttempt,
    AITutorMessage,
    AITutorSession,
    StudentAIPreference,
    StudentTopicMastery,
)


@admin.register(AITutorSession)
class AITutorSessionAdmin(admin.ModelAdmin):
    list_display = ("student", "subject", "topic", "session_type", "language", "status", "started_at")
    list_filter = ("session_type", "language", "status", "subject")
    search_fields = ("student__name", "topic", "subject__name")


@admin.register(AITutorMessage)
class AITutorMessageAdmin(admin.ModelAdmin):
    list_display = ("session", "student", "sender_type", "intent", "safety_status", "model_name", "created_at")
    list_filter = ("sender_type", "intent", "safety_status", "model_name")
    search_fields = ("student__name", "message_text", "response_text")


@admin.register(StudentTopicMastery)
class StudentTopicMasteryAdmin(admin.ModelAdmin):
    list_display = ("student", "subject", "topic", "mastery_level", "accuracy_percentage", "attempts")
    list_filter = ("mastery_level", "subject")
    search_fields = ("student__name", "topic", "subject__name")


@admin.register(AIPracticeAttempt)
class AIPracticeAttemptAdmin(admin.ModelAdmin):
    list_display = ("student", "subject", "topic", "is_correct", "score", "attempt_number", "created_at")
    list_filter = ("is_correct", "subject")
    search_fields = ("student__name", "question_text", "student_answer")


@admin.register(StudentAIPreference)
class StudentAIPreferenceAdmin(admin.ModelAdmin):
    list_display = ("student", "preferred_language", "explanation_style", "default_difficulty", "voice_enabled")
    search_fields = ("student__name",)


@admin.register(AIKnowledgeDocument)
class AIKnowledgeDocumentAdmin(admin.ModelAdmin):
    list_display = ("title", "document_type", "class_fk", "section", "subject", "access_level", "approval_status")
    list_filter = ("document_type", "access_level", "approval_status", "class_fk", "subject")
    search_fields = ("title", "content", "topic", "chapter_title")


@admin.register(AIAuditLog)
class AIAuditLogAdmin(admin.ModelAdmin):
    list_display = ("action_type", "student", "session", "model_used", "access_result", "created_at")
    list_filter = ("action_type", "access_result", "model_used")
    search_fields = ("student__name", "action_type")

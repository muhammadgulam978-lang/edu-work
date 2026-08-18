from django.contrib import admin

from .models import (
    AdmissionQuestion,
    AdmissionRecommendation,
    AttemptAnswer,
    BlueprintSubject,
    GeneratedPaper,
    ReadinessReport,
    TestAttempt,
    TestBlueprint,
    TestSchedule,
)


class BlueprintSubjectInline(admin.TabularInline):
    model = BlueprintSubject
    extra = 1


@admin.register(TestBlueprint)
class TestBlueprintAdmin(admin.ModelAdmin):
    list_display = ("name", "applying_class", "total_questions", "total_marks", "total_time_minutes", "is_active")
    inlines = [BlueprintSubjectInline]


@admin.register(AdmissionQuestion)
class AdmissionQuestionAdmin(admin.ModelAdmin):
    list_display = ("__str__", "question_type", "difficulty", "marks", "is_ai_generated", "duplicate_flag")
    list_filter = ("question_type", "difficulty", "is_ai_generated")


@admin.register(GeneratedPaper)
class GeneratedPaperAdmin(admin.ModelAdmin):
    list_display = ("blueprint", "version_label", "status", "generated_at", "approved_at")
    list_filter = ("status",)


admin.site.register(TestSchedule)
admin.site.register(TestAttempt)
admin.site.register(AttemptAnswer)
admin.site.register(ReadinessReport)
admin.site.register(AdmissionRecommendation)

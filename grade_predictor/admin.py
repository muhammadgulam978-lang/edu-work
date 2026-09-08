from django.contrib import admin

from .models import (
    GradePredictorConfig,
    GradeRiskIntervention,
    PredictionAlert,
    PredictionHistory,
    StudentGradePrediction,
)


@admin.register(GradePredictorConfig)
class GradePredictorConfigAdmin(admin.ModelAdmin):
    list_display = ("school_name", "minimum_data_requirement", "updated_at")


@admin.register(StudentGradePrediction)
class StudentGradePredictionAdmin(admin.ModelAdmin):
    list_display = (
        "student", "subject", "predicted_grade", "predicted_score",
        "risk_level", "confidence_level", "trend", "last_calculated",
    )
    list_filter = ("risk_level", "confidence_level", "trend", "subject", "class_room")
    search_fields = ("student__full_name",)


@admin.register(GradeRiskIntervention)
class GradeRiskInterventionAdmin(admin.ModelAdmin):
    list_display = ("prediction", "action", "status", "created_by", "created_at")
    list_filter = ("status",)


admin.site.register(PredictionHistory)
admin.site.register(PredictionAlert)

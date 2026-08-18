from django.urls import path

from . import views

urlpatterns = [
    path("ai-copilot/", views.admin_ai_copilot, name="admin_ai_copilot"),
    path("ai-copilot/message/", views.admin_ai_copilot_message, name="admin_ai_copilot_message"),
    path("ai-analytics/advanced/", views.ai_analytics_advanced, name="ai_analytics_advanced"),
    path("ai-analytics/advanced/data/", views.ai_analytics_advanced_data, name="ai_analytics_advanced_data"),
    path("ai-analytics/reports/", views.ai_analytics_reports, name="ai_analytics_reports"),
    path("ai-analytics/reports/generate/", views.ai_analytics_report_generate, name="ai_analytics_report_generate"),
    path("ai-analytics/reports/auto-generate/", views.ai_analytics_report_auto_generate, name="ai_analytics_report_auto_generate"),
    path("ai-analytics/reports/<uuid:report_uuid>/", views.ai_analytics_report_detail, name="ai_analytics_report_detail"),
    path("ai-analytics/reports/<uuid:report_uuid>/pdf/", views.ai_analytics_report_pdf, name="ai_analytics_report_pdf"),
    path("ai-analytics/reports/<uuid:report_uuid>/excel/", views.ai_analytics_report_excel, name="ai_analytics_report_excel"),
    path("ai-analytics/reports/<uuid:report_uuid>/share/", views.ai_analytics_report_share, name="ai_analytics_report_share"),
    path("student-intelligence/", views.student_intelligence, name="admin_ai_student_intelligence"),
    path("student-intelligence/<str:student_id>/", views.student_intelligence_detail, name="admin_ai_student_intelligence_detail"),
    path("student-intelligence/<str:student_id>/pdf/", views.student_intelligence_pdf, name="admin_ai_student_intelligence_pdf"),
]

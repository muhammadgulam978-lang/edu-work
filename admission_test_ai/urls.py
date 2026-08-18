from django.urls import path

from . import views

urlpatterns = [
    path("", views.dashboard, name="admission_ai_dashboard"),
    path("blueprints/", views.blueprint_list, name="admission_blueprint_list"),
    path("blueprints/create/", views.blueprint_create, name="admission_blueprint_create"),
    path("blueprints/<int:pk>/", views.blueprint_detail, name="admission_blueprint_detail"),
    path("blueprints/<int:pk>/generate-paper/", views.generate_paper, name="admission_generate_paper"),
    path("papers/", views.paper_list, name="admission_paper_list"),
    path("papers/<int:pk>/", views.paper_detail, name="admission_paper_detail"),
    path("papers/<int:pk>/advance/", views.paper_advance_status, name="admission_paper_advance"),
    path("schedule/", views.schedule_list, name="admission_schedule_list"),
    path("schedule/create/", views.schedule_create, name="admission_schedule_create"),
    path("attempts/<int:attempt_id>/readiness/", views.readiness_report_view, name="admission_readiness_report"),
]

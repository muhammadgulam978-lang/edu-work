from django.urls import path

from . import views

urlpatterns = [
    path("", views.dashboard, name="ai_tutor_dashboard"),
    path("sessions/start/", views.start_session, name="ai_tutor_start_session"),
    path("sessions/", views.sessions, name="ai_tutor_sessions"),
    path("sessions/<int:session_id>/", views.chat, name="ai_tutor_chat"),
    path("sessions/<int:session_id>/message/", views.send_message, name="ai_tutor_send_message"),
    path("sessions/<int:session_id>/practice/", views.create_practice, name="ai_tutor_create_practice"),
    path("practice/<int:attempt_id>/answer/", views.answer_practice, name="ai_tutor_answer_practice"),
    path("progress/", views.progress, name="ai_tutor_progress"),
    path("study-plan/", views.study_plan, name="ai_tutor_study_plan"),
]

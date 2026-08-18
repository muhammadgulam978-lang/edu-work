from django.urls import path

from . import views

app_name = "counsellor_dashboard"

urlpatterns = [
    path("", views.dashboard, name="dashboard"),

    path("referrals/", views.referral_list, name="referral_list"),
    path("referrals/create/", views.referral_create, name="referral_create"),
    path("referrals/<int:referral_id>/accept/", views.referral_accept, name="referral_accept"),

    path("cases/", views.case_list, name="case_list"),
    path("cases/create/", views.case_create, name="case_create"),
    path("cases/<int:case_id>/", views.case_detail, name="case_detail"),
    path("cases/<int:case_id>/sessions/create/", views.session_create, name="session_create"),
    path("cases/<int:case_id>/support-plan/", views.support_plan_edit, name="support_plan_edit"),

    path("appointments/", views.appointment_list, name="appointment_list"),
    path("appointments/create/", views.appointment_create, name="appointment_create"),

    path("safeguarding/", views.safeguarding_list, name="safeguarding_list"),
    path("safeguarding/create/", views.safeguarding_create, name="safeguarding_create"),
]

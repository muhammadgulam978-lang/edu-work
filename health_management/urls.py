from django.urls import path

from . import views

app_name = "health_management"

urlpatterns = [
    path("", views.dashboard, name="dashboard"),

    path("checkup-cycles/", views.checkup_cycle_list, name="checkup_cycle_list"),
    path("checkup-cycles/create/", views.checkup_cycle_create, name="checkup_cycle_create"),
    path("checkup-cycles/<int:cycle_id>/register/", views.checkup_register, name="checkup_register"),
    path("checkup-records/<int:record_id>/edit/", views.checkup_record_edit, name="checkup_record_edit"),

    path("profiles/<int:profile_id>/", views.health_profile_detail, name="health_profile_detail"),

    path("medical-visits/", views.medical_visit_list, name="medical_visit_list"),
    path("medical-visits/create/", views.medical_visit_create, name="medical_visit_create"),

    path("emergencies/", views.emergency_case_list, name="emergency_case_list"),
    path("emergencies/create/", views.emergency_case_create, name="emergency_case_create"),
    path("emergencies/<int:case_id>/", views.emergency_case_detail, name="emergency_case_detail"),

    path("sick-bay/", views.sick_bay_list, name="sick_bay_list"),
    path("sick-bay/create/", views.sick_bay_create, name="sick_bay_create"),

    path("medicines/", views.medicine_inventory_list, name="medicine_inventory_list"),
    path("medicines/create/", views.medicine_create, name="medicine_create"),
    path("medicines/batch/create/", views.medicine_batch_create, name="medicine_batch_create"),
]

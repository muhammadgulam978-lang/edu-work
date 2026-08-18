from django.urls import path

from . import views

app_name = "grade_predictor"

urlpatterns = [
    path("grade-predictor/", views.teacher_grade_predictor_dashboard, name="teacher_dashboard"),
  
    path("grade-predictor/student/<int:prediction_id>/", views.student_prediction_detail, name="prediction_detail"),
    path("grade-predictor/student/<int:prediction_id>/intervene/", views.create_intervention, name="create_intervention"),
]

# In your project's main urls.py, add:
#   path("teacher/", include("grade_predictor.urls")),

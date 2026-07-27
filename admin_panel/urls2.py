from django.urls import path, include
from .import views
from django.contrib.auth import views as auth_views
from admin_panel.views import bulk_upload_students, bulk_upload_teachers, bulk_delete_students,  bulk_delete_teachers
urlpatterns = [
    path('', include('admin_ai.urls')),
    path('', views.admin_panel_dashboard, name='admin_panel_dashboard'),
    path('user_list/', views.user_list, name='user_list'),
    path('register/', views.register_admission, name='registration'),
    path('admission_list/', views.admission_list, name='admission_list'),
    path('admission/<int:pk>/update_status/', views.update_admission_status, name='update_admission_status'),
    path('rejection_reason/<int:admission_id>/', views.reject_reason, name='reject_reason'),
    path('admission/<int:admission_id>/approve-credentials/', views.approve_admission_credentials, name='approve_admission_credentials'),
    path('change_admission_status/<int:admission_id>/', views.change_admission_status, name='change_admission_status'),
    
    
    path('query/', views.query, name='query'),
    path('classes/', views.class_list, name='class_list'),            # Read (List all)
    path('classes/add/', views.class_create, name='class_create'),    # Create 
    path('classes/<int:pk>/students/', views.class_students, name='class_students'),
    path('classes/<int:pk>/edit/', views.class_update, name='class_update'),  # Update
    path('classes/<int:pk>/delete/', views.class_delete, name='class_delete'), # Delete
    path('classes/', views.class_list, name='class_list'),
    path('academic-years/', views.academic_year_list, name='academic_year_list'), #academic_year
    path('academic-years/add/', views.add_academic_year, name='add_academic_year'),
    path('academic-years/update/<int:pk>/', views.update_academic_year, name='update_academic_year'),
    path('academic-years/delete/<int:pk>/', views.delete_academic_year, name='delete_academic_year'),
    path('sections/', views.section_list, name='section_list'),
    path('sections/add/', views.add_section, name='add_section'),
    path('sections/edit/<int:pk>/', views.edit_section, name='edit_section'),
    path('sections/delete/<int:pk>/', views.delete_section, name='delete_section'),
    path('subjects/', views.subject_list, name='subject_list'), #subjects crud
    path('subjects/add/', views.add_subject, name='add_subject'),
    path('subjects/edit/<int:pk>/', views.edit_subject, name='edit_subject'),
    path('subjects/delete/<int:pk>/', views.delete_subject, name='delete_subject'),
    path('teachers/', views.teacher_list, name='teacher_list'),
    path('teachers/add/', views.teacher_create, name='teacher_add'),
    path('teachers/duty-roster/', views.teacher_duty_roster, name='teacher_duty_roster'),
    path('teachers/duty-roster/add/', views.add_teacher_duty, name='add_teacher_duty'),
    path('teachers/duty-roster/<int:pk>/delete/', views.delete_teacher_duty, name='delete_teacher_duty'),
    path('teachers/duty-roster/report/', views.teacher_duty_roster_report, name='teacher_duty_roster_report'),
]

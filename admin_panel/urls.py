from django.urls import path
from .import views
from django.contrib.auth import views as auth_views
from admin_panel.views import bulk_upload_students, bulk_upload_teachers, bulk_delete_students,  bulk_delete_teachers
urlpatterns = [
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
    # path('parents/', views.parent_list, name='parent_list'),
    
    # path('reset/<uidb64>/<token>/', auth_views.PasswordResetConfirmView.as_view(), name='password_reset_confirm'),
    path('teachers/edit/<int:pk>/', views.teacher_update, name='teacher_edit'),
    path('teachers/delete/<int:pk>/', views.teacher_delete, name='teacher_delete'),
    path('periods/', views.period_list_view, name='period_list'),                
    path('periods/create/', views.create_period_view, name='create_period'),       
    path('periods/update/<int:pk>/', views.update_period_view, name='update_period'),  
    path('periods/delete/<int:pk>/', views.delete_period_view, name='delete_period'),  
    path('timetable-automation/', views.timetable_automation, name='timetable_automation'),
    path('header-data/', views.admin_header_data, name='admin_header_data'),
    path('search/', views.admin_search, name='admin_search'),
    path('search-suggestions/', views.admin_search_suggestions, name='admin_search_suggestions'),
    path('profile/', views.admin_profile, name='admin_profile'),
    path('automation-overview-data/', views.automation_overview_data, name='automation_overview_data'),
    path('dashboard-summary-data/', views.dashboard_summary_data, name='dashboard_summary_data'),
    path('timetable/', views.timetable_view, name='timetable_view'),
    path('assign_period/', views.assign_period_view, name='assign_period'),
    path('ajax/subject_periods/', views.ajax_subject_periods, name='ajax_subject_periods'),
    path('ajax/time_slots/', views.ajax_time_slots, name='ajax_time_slots'),
    path('ajax/get_days_for_subject/', views.get_days_for_subject, name='get_days_for_subject'),
    path('ajax/get_subjects_for_class/', views.get_subjects_for_section, name='get_subjects_for_class'),
    path('ajax/get_subjects_for_section/', views.get_subjects_for_section, name='get_subjects_for_section'),
    path('ajax/get_assigned_classes/', views.get_assigned_classes, name='get_assigned_classes'),
    path('ajax/get_sections_for_class/', views.get_sections_for_class, name='get_sections_for_class'),
    path('ajax/delete_assignment/<int:assignment_id>/', views.delete_assignment, name='delete_assignment'),
    path('groups/add/', views.add_class_group, name='add_class_group'),
    path('groups/', views.class_group_list, name='class_group_list'),
    path('edit-group/<int:group_id>/', views.edit_class_group, name='edit_class_group'),
    path('delete-group/<int:group_id>/', views.delete_class_group, name='delete_class_group'),  
    path('class_teachers/', views.class_teacher_list, name='class_teacher_list'),  
    path('class_teachers/create/', views.class_teacher_create, name='class_teacher_create'),
    path('class_teachers/<int:pk>/edit/', views.class_teacher_update, name='class_teacher_update'),
    path('class_teachers/<int:pk>/delete/', views.class_teacher_delete, name='class_teacher_delete'),
    path('ajax/load-sections/', views.ajax_load_sections, name='ajax_load_sections'),
    path('ajax/load-teachers-by-class/', views.ajax_load_teachers_by_class, name='ajax_load_teachers_by_class'),
    path('portfolio-timetable/', views.portfolio_timetable, name='portfolio_timetable'),
    path('get-sections/', views.get_sections, name='get_sections'),
    path('generate-timetable-pdf/', views.timetable_pdf, name='timetable_pdf'),
    path('portfolio_timetable/', views.portfolio_timetable, name='portfolio_timetable'), 
    path('id_cards/', views.student_id_card_list, name='student_id_card_list'),

    path('id_card/<int:student_id>/', views.generate_student_id_card, name='generate_id_card'),
    path('upload-photo/<int:student_id>/', views.upload_student_photo, name='upload_student_photo'),
    path('dashboard/', views.admin_dashboard, name='admin_dashboard'),  
    path('hello/', views.my_view, name='hello'),


    path("streams/", views.stream_list, name="stream_list"),
    path("streams/add/", views.add_stream, name="add_stream"),
    path("streams/edit/<int:pk>/", views.edit_stream, name="edit_stream"),
    path("streams/delete/<int:pk>/", views.delete_stream, name="delete_stream"),

    
    path("formats/", views.format_list, name="format_list"),
    path("formats/<int:format_id>/edit/", views.edit_format, name="edit_format"),
    path("formats/<int:format_id>/delete/", views.delete_format, name="delete_format"),
    path("formats/create/", views.create_format, name="create_format"),
    path("formats/<int:format_id>/questions/", views.format_questions, name="format_questions"),
    path("formats/<int:format_id>/generate/", views.generate_paper_confirm, name="generate_paper_confirm"),
    path("formats/<int:format_id>/generate-pdf/", views.generate_question_paper_pdf, name="generate_question_paper_pdf"),
    
    

    # ---- Questions ----
    path("questions/", views.all_questions, name="all_questions"),

    # ---- Test Page for generator ----
    path("generate-paper/<int:format_id>/", views.generate_question_paper, name="generate_question_paper"),
    
    path('create-role/', views.create_role, name='create_role'),
    path('roles/', views.list_roles, name='list_roles'),
    path('assign-role/', views.assign_role, name='assign_role'),
    
    path('books/upload/', views.upload_book, name='upload_book'),
    path('books/parse/<int:book_id>/', views.parse_book_toc_ml, name='parse_book_toc_ml'),
    path('books/<int:pk>/', views.book_detail, name='book_detail'),

    path('books/', views.book_list, name='book_list'),
    
    path('manage_fixture/', views.manage_fixture, name='manage_fixture'),
    path('get_free_teachers/', views.get_free_teachers, name='get_free_teachers'),

    # ================= HR MODULE =================

    path('departments/', views.department_list, name='department_list'),
    path('departments/create/', views.department_create, name='department_create'),

    path('designations/', views.designation_list, name='designation_list'),
    path('designations/create/', views.designation_create, name='designation_create'),

    path('employees/', views.employee_list, name='employee_list'),
    path('employees/create/', views.employee_create, name='employee_create'),
    path('employees/<int:pk>/edit/', views.employee_edit, name='employee_edit'),
    

    # Staff Category
    path('staff-categories/', views.staff_category_list, name='staff_category_list'),
    path('staff-categories/create/', views.staff_category_create, name='staff_category_create'),

    # Job Type
    path('job-types/', views.job_type_list, name='job_type_list'),
    path('job-types/create/', views.job_type_create, name='job_type_create'),

    # ================= LEAVE MANAGEMENT =================

    path('leaves/', views.leave_list, name='leave_list'),
    path('leaves/apply/', views.leave_create, name='leave_create'),
    path('leaves/<int:pk>/<str:action>/', views.leave_action, name='leave_action'),
    
    path('leave-types/', views.leave_type_list, name='leave_type_list'),
    path('leave-types/create/', views.leave_type_create, name='leave_type_create'),


    # Admin Appraisal URLs
    path("appraisal/admin/kpis/", views.admin_kpi_builder, name="admin_kpi_builder"),
    path("appraisal/admin/submissions/", views.admin_appraisal_list, name="admin_appraisal_list"),
    path("appraisal/admin/submissions/<int:pk>/", views.admin_appraisal_detail, name="admin_appraisal_detail"),


    path("academic-calendar/", views.academic_calendar_page, name="academic_calendar_page"),
    path("academic-calendar/events/", views.academic_calendar_events, name="academic_calendar_events"),
    path("academic-calendar/create/", views.academic_calendar_create, name="academic_calendar_create"),
    path("academic-calendar/<int:event_id>/update/", views.academic_calendar_update, name="academic_calendar_update"),
    path("academic-calendar/<int:event_id>/delete/", views.academic_calendar_delete, name="academic_calendar_delete"),
    path("academic-calendar/export-pdf/", views.academic_calendar_export_pdf, name="academic_calendar_export_pdf"),
    
    path('assignments/', views.admin_view_assignments, name='admin_view_assignments'),
    path('quizzes/', views.admin_view_quizzes, name='admin_view_quizzes'),
    path('diaries/', views.admin_view_diaries, name='admin_view_diaries'),
    path('lecture-notes/', views.admin_view_lecture_notes, name='admin_view_lecture_notes'),
    
    

    ## Students
    path('bulk-upload-students/', views.bulk_upload_students, name='bulk_upload_students'),
    ## Teachers  
    path('bulk-upload-teachers/', views.bulk_upload_teachers, name='bulk_upload_teachers'),
    
    path('students/bulk-delete/', bulk_delete_students, name='bulk_delete_students'),
    path('teachers/bulk-delete/', bulk_delete_teachers, name='bulk_delete_teachers'),
    
    # path('generate-timetable/', views.generate_timetable, name='generate_timetable'),
    
    
    
    
]

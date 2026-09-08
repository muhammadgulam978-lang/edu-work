from django.urls import path, include
from .import views
from access_control import management_views as access_management
from django.contrib.auth import views as auth_views
from django.views.generic import TemplateView
from admin_panel.views import bulk_upload_students, bulk_upload_teachers, bulk_delete_students,  bulk_delete_teachers
from . import admission_views
urlpatterns = [
    path('help-support/report-issue/', TemplateView.as_view(template_name='shared/help_support/report_issue.html', extra_context={'portal_base': 'admin_panel/base.html', 'portal_label': 'Admin', 'portal_kind': 'admin', 'report_route': 'admin_report_issue', 'reports_route': 'admin_requested_reports', 'suggestion_route': 'admin_suggestion_bucket', 'suggestions_route': 'admin_my_suggestions'}), name='admin_report_issue'),
    path('help-support/requested-reports/', TemplateView.as_view(template_name='shared/help_support/requested_reports.html', extra_context={'portal_base': 'admin_panel/base.html', 'portal_label': 'Admin', 'portal_kind': 'admin', 'report_route': 'admin_report_issue', 'reports_route': 'admin_requested_reports', 'suggestion_route': 'admin_suggestion_bucket', 'suggestions_route': 'admin_my_suggestions'}), name='admin_requested_reports'),
    path('help-support/suggestion-bucket/', TemplateView.as_view(template_name='shared/help_support/suggestion_bucket.html', extra_context={'portal_base': 'admin_panel/base.html', 'portal_label': 'Admin', 'portal_kind': 'admin', 'report_route': 'admin_report_issue', 'reports_route': 'admin_requested_reports', 'suggestion_route': 'admin_suggestion_bucket', 'suggestions_route': 'admin_my_suggestions'}), name='admin_suggestion_bucket'),
    path('help-support/my-suggestions/', TemplateView.as_view(template_name='shared/help_support/my_suggestions.html', extra_context={'portal_base': 'admin_panel/base.html', 'portal_label': 'Admin', 'portal_kind': 'admin', 'report_route': 'admin_report_issue', 'reports_route': 'admin_requested_reports', 'suggestion_route': 'admin_suggestion_bucket', 'suggestions_route': 'admin_my_suggestions'}), name='admin_my_suggestions'),
    path('', include('admin_ai.urls')),
    path('', views.admin_panel_dashboard, name='admin_panel_dashboard'),
    path('announcements/', views.announcement_center, name='announcement_center'),
    path('user_list/', views.user_list, name='user_list'),
    path('register/', views.register_admission, name='registration'),
    path('admission_list/', views.admission_list, name='admission_list'),
    path('students/admissions/', admission_views.student_admissions, name='student_admissions'),
    path('students/', views.student_directory, name='student_directory'),
    path('students/<int:pk>/', views.student_directory_detail, name='student_directory_detail'),
    path('students/<int:pk>/edit/', views.student_directory_update, name='student_directory_update'),
    path('students/<int:pk>/delete/', views.student_directory_delete, name='student_directory_delete'),
    path('students/<int:pk>/reset-password/', views.student_directory_reset_password, name='student_directory_reset_password'),
    path('students/admissions/lookups/', admission_views.admission_lookups, name='admission_lookups'),
    path('students/admissions/fee-plans/create/', admission_views.admission_create_fee_plan, name='admission_create_fee_plan'),
    path('students/admissions/<int:pk>/enrollment/', admission_views.admission_enrollment_profile, name='admission_enrollment_profile'),
    path('students/admissions/<int:pk>/retry-voucher/', admission_views.admission_retry_voucher, name='admission_retry_voucher'),
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
    # path('parents/', views.parent_list, name='parent_list'),
    
    # path('reset/<uidb64>/<token>/', auth_views.PasswordResetConfirmView.as_view(), name='password_reset_confirm'),
    path('teachers/<int:pk>/profile/', views.teacher_profile, name='teacher_profile'),
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
    path('ai-analytics/', views.ai_analytics_dashboard, name='ai_analytics_dashboard'),
    path('ai-analytics-data/', views.ai_analytics_data, name='ai_analytics_data'),
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

    path('teachers/duty-roster/', views.teacher_duty_roster, name='teacher_duty_roster'),
    path('teachers/duty-roster/add/', views.add_teacher_duty, name='add_teacher_duty'),
    path('teachers/duty-roster/<int:pk>/delete/', views.delete_teacher_duty, name='delete_teacher_duty'),
    path('teachers/duty-roster/report/', views.teacher_duty_roster_report, name='teacher_duty_roster_report'),

    path('id_card/<int:student_id>/', views.generate_student_id_card, name='generate_id_card'),
    path('id_card/<int:student_id>/download/', views.download_student_id_card, name='download_student_id_card'),
    path('upload-photo/<int:student_id>/', views.upload_student_photo, name='upload_student_photo'),
    path('dashboard/', views.admin_dashboard, name='admin_dashboard'),  
    path('hello/', views.my_view, name='hello'),
    
    path('events/', views.event_list, name='event_list'),
    path('events/create/', views.create_event, name='create_event'),
    path('events/<int:pk>/', views.event_detail, name='event_detail'),
    path('events/<int:pk>/add-duty/', views.add_event_duty, name='add_event_duty'),
    path('events/<int:pk>/delete/', views.delete_event, name='delete_event'),
    path('events/duty/<int:pk>/delete/', views.delete_event_duty, name='delete_event_duty'),
    path('events/<int:pk>/report/', views.event_duty_report, name='event_duty_report'),

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
    
    path('user-role-management/', access_management.security_center, name='user_role_management'),
    path('create-role/', access_management.role_add, name='create_role'),
    path('roles/', access_management.roles, name='list_roles'),
    path('assign-role/', access_management.assignment_add, name='assign_role'),
    
    path('books/upload/', views.upload_book, name='upload_book'),
    path('books/parse/<int:book_id>/', views.parse_book_toc_ml, name='parse_book_toc_ml'),
    path('books/<int:pk>/', views.book_detail, name='book_detail'),

    path('books/', views.book_list, name='book_list'),
    
    path('manage_fixture/', views.manage_fixture, name='manage_fixture'),
    path('get_free_teachers/', views.get_free_teachers, name='get_free_teachers'),

    # ================= HR MODULE =================
    
    path('hr-dashboard/', views.hr_dashboard, name='hr_dashboard'),
    
    path('departments/', views.department_list, name='department_list'),
    path('departments/create/', views.department_create, name='department_create'),

    path('designations/', views.designation_list, name='designation_list'),
    path('designations/create/', views.designation_create, name='designation_create'),

    path('employees/', views.employee_list, name='employee_list'),
    path('employees/create/', views.employee_create, name='employee_create'),
    path('employees/<int:pk>/edit/', views.employee_edit, name='employee_edit'),
    
    path('employees/create-ajax/', views.employee_create_ajax, name='employee_create_ajax'),
    path('employees/<int:pk>/toggle-active/', views.employee_toggle_active, name='employee_toggle_active'),
    path('employees/<int:pk>/delete/', views.employee_delete, name='employee_delete'),

    path('ajax/quick-add/department/', views.ajax_quick_add_department, name='ajax_quick_add_department'),
    path('ajax/quick-add/designation/', views.ajax_quick_add_designation, name='ajax_quick_add_designation'),
    path('ajax/quick-add/job-type/', views.ajax_quick_add_job_type, name='ajax_quick_add_job_type'),
    path('ajax/quick-add/staff-category/', views.ajax_quick_add_staff_category, name='ajax_quick_add_staff_category'),
    
    path('hr-setup/', views.hr_setup, name='hr_setup'),

    path('ajax/delete/department/<int:pk>/', views.ajax_delete_department, name='ajax_delete_department'),
    path('ajax/delete/designation/<int:pk>/', views.ajax_delete_designation, name='ajax_delete_designation'),
    path('ajax/delete/job-type/<int:pk>/', views.ajax_delete_job_type, name='ajax_delete_job_type'),
    path('ajax/delete/staff-category/<int:pk>/', views.ajax_delete_staff_category, name='ajax_delete_staff_category'),
    

    # Staff Category
    path('staff-categories/', views.staff_category_list, name='staff_category_list'),
    path('staff-categories/create/', views.staff_category_create, name='staff_category_create'),
    
    path('employees/<int:pk>/profile/', views.employee_profile, name='employee_profile'),
    path('employees/<int:pk>/profile/pdf/', views.employee_profile_pdf, name='employee_profile_pdf'),

    # Job Type
    path('job-types/', views.job_type_list, name='job_type_list'),
    path('job-types/create/', views.job_type_create, name='job_type_create'),
    path('job-types/<int:pk>/edit/', views.job_type_update, name='job_type_update'),

    # ================= LEAVE MANAGEMENT =================

    path('leaves/', views.leave_list, name='leave_list'),
    path('leaves/apply/', views.leave_create, name='leave_create'),
    path('leaves/<int:pk>/<str:action>/', views.leave_action, name='leave_action'),
    
    path('leave-types/', views.leave_type_list, name='leave_type_list'),
    path('leave-types/create/', views.leave_type_create, name='leave_type_create'),
    path('leave-types/<int:pk>/edit/', views.leave_type_update, name='leave_type_update'),
    path('leave-types/<int:pk>/delete/', views.leave_type_delete, name='leave_type_delete'),
    path('leave-types/<int:pk>/toggle/', views.leave_type_toggle, name='leave_type_toggle'),

    path('leaves/detail/<int:pk>/', views.leave_detail_ajax, name='leave_detail_ajax'),
    path('leaves/balance/', views.leave_employee_balance, name='leave_employee_balance'),
    path('leaves/calendar/events/', views.leave_calendar_events, name='leave_calendar_events'),
    path('leaves/reports/export-pdf/', views.leave_reports_export_pdf, name='leave_reports_export_pdf'),

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
    path('bulk-upload-students/template/', views.bulk_upload_students_template, name='bulk_upload_students_template'),
    path('bulk-upload-students/activity/', views.bulk_upload_students_activity, name='bulk_upload_students_activity'),
    path('bulk-upload-students/progress/', views.bulk_upload_students_progress, name='bulk_upload_students_progress'),
    path('bulk-upload-students/credentials/', views.bulk_upload_students_credentials, name='bulk_upload_students_credentials'),
    path('bulk-upload-students/activate-logins/', views.bulk_upload_students_activate_logins, name='bulk_upload_students_activate_logins'),
    ## Teachers  
    path('bulk-upload-teachers/', views.bulk_upload_teachers, name='bulk_upload_teachers'),
    path('bulk-upload-teachers/progress/', views.bulk_upload_teachers_progress, name='bulk_upload_teachers_progress'),
    path('bulk-upload-teachers/template/', views.bulk_upload_teachers_template, name='bulk_upload_teachers_template'),
    path('bulk-upload-teachers/activity/', views.bulk_upload_teachers_activity, name='bulk_upload_teachers_activity'),
    path('bulk-upload-teachers/credentials/', views.bulk_upload_teachers_credentials, name='bulk_upload_teachers_credentials'),
    
    path('students/bulk-delete/', bulk_delete_students, name='bulk_delete_students'),
    path('teachers/bulk-delete/', bulk_delete_teachers, name='bulk_delete_teachers'),

    # ================= OPERATIONS =================
    path('operations/procurement/', views.operation_procurement_dashboard, name='operation_procurement_dashboard'),
    path('operations/<str:module>/summary-data/', views.operation_summary_data, name='operation_summary_data'),
    path('operations/procurement/categories/', views.operation_procurement_category_list, name='operation_procurement_category_list'),
    path('operations/procurement/categories/add/', views.operation_procurement_category_create, name='operation_procurement_category_create'),
    path('operations/procurement/categories/<int:pk>/edit/', views.operation_procurement_category_edit, name='operation_procurement_category_edit'),
    path('operations/procurement/categories/<int:pk>/delete/', views.operation_procurement_category_delete, name='operation_procurement_category_delete'),
    path('operations/procurement/vendors/', views.operation_vendor_list, name='operation_vendor_list'),
    path('operations/procurement/vendors/add/', views.operation_vendor_create, name='operation_vendor_create'),
    path('operations/procurement/vendors/<int:pk>/edit/', views.operation_vendor_edit, name='operation_vendor_edit'),
    path('operations/procurement/vendors/<int:pk>/delete/', views.operation_vendor_delete, name='operation_vendor_delete'),
    path('operations/procurement/purchase-requests/', views.operation_purchase_request_list, name='operation_purchase_request_list'),
    path('operations/procurement/purchase-requests/add/', views.operation_purchase_request_create, name='operation_purchase_request_create'),
    path('operations/procurement/purchase-requests/<int:pk>/edit/', views.operation_purchase_request_edit, name='operation_purchase_request_edit'),
    path('operations/procurement/purchase-requests/<int:pk>/delete/', views.operation_purchase_request_delete, name='operation_purchase_request_delete'),
    path('operations/procurement/inventory-items/', views.operation_inventory_item_list, name='operation_inventory_item_list'),
    path('operations/procurement/inventory-items/add/', views.operation_inventory_item_create, name='operation_inventory_item_create'),
    path('operations/procurement/inventory-items/<int:pk>/edit/', views.operation_inventory_item_edit, name='operation_inventory_item_edit'),
    path('operations/procurement/inventory-items/<int:pk>/delete/', views.operation_inventory_item_delete, name='operation_inventory_item_delete'),
    path('operations/procurement/stock-movements/', views.operation_stock_movement_list, name='operation_stock_movement_list'),
    path('operations/procurement/stock-movements/add/', views.operation_stock_movement_create, name='operation_stock_movement_create'),
    path('operations/procurement/stock-movements/<int:pk>/edit/', views.operation_stock_movement_edit, name='operation_stock_movement_edit'),
    path('operations/procurement/stock-movements/<int:pk>/delete/', views.operation_stock_movement_delete, name='operation_stock_movement_delete'),

    path('operations/transportation/', views.operation_transportation_dashboard, name='operation_transportation_dashboard'),
    path('operations/transportation/vehicles/', views.operation_vehicle_list, name='operation_vehicle_list'),
    path('operations/transportation/vehicles/add/', views.operation_vehicle_create, name='operation_vehicle_create'),
    path('operations/transportation/vehicles/<int:pk>/edit/', views.operation_vehicle_edit, name='operation_vehicle_edit'),
    path('operations/transportation/vehicles/<int:pk>/delete/', views.operation_vehicle_delete, name='operation_vehicle_delete'),
    path('operations/transportation/routes/', views.operation_transport_route_list, name='operation_transport_route_list'),
    path('operations/transportation/routes/add/', views.operation_transport_route_create, name='operation_transport_route_create'),
    path('operations/transportation/routes/<int:pk>/edit/', views.operation_transport_route_edit, name='operation_transport_route_edit'),
    path('operations/transportation/routes/<int:pk>/delete/', views.operation_transport_route_delete, name='operation_transport_route_delete'),
    path('operations/transportation/route-assignments/', views.operation_route_assignment_list, name='operation_route_assignment_list'),
    path('operations/transportation/route-assignments/add/', views.operation_route_assignment_create, name='operation_route_assignment_create'),
    path('operations/transportation/route-assignments/<int:pk>/edit/', views.operation_route_assignment_edit, name='operation_route_assignment_edit'),
    path('operations/transportation/route-assignments/<int:pk>/delete/', views.operation_route_assignment_delete, name='operation_route_assignment_delete'),
    path('operations/transportation/trips/', views.operation_transport_trip_list, name='operation_transport_trip_list'),
    path('operations/transportation/trips/add/', views.operation_transport_trip_create, name='operation_transport_trip_create'),
    path('operations/transportation/trips/<int:pk>/edit/', views.operation_transport_trip_edit, name='operation_transport_trip_edit'),
    path('operations/transportation/trips/<int:pk>/delete/', views.operation_transport_trip_delete, name='operation_transport_trip_delete'),
    path('operations/transportation/maintenance-records/', views.operation_vehicle_maintenance_list, name='operation_vehicle_maintenance_list'),
    path('operations/transportation/maintenance-records/add/', views.operation_vehicle_maintenance_create, name='operation_vehicle_maintenance_create'),
    path('operations/transportation/maintenance-records/<int:pk>/edit/', views.operation_vehicle_maintenance_edit, name='operation_vehicle_maintenance_edit'),
    path('operations/transportation/maintenance-records/<int:pk>/delete/', views.operation_vehicle_maintenance_delete, name='operation_vehicle_maintenance_delete'),
    
    # path('generate-timetable/', views.generate_timetable, name='generate_timetable'),
    
    path(
    "leave/edit/<int:pk>/",
    views.leave_update,
    name="leave_update",
    ),

    path(
    "leave/delete/<int:pk>/",
    views.leave_delete,
    name="leave_delete",
    ),

    path(
    "leave/action/<int:pk>/<str:action>/",
    views.leave_action,
    name="leave_action",
    ),
    
    
    
    
]

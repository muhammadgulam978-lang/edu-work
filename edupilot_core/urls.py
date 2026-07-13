# from django.contrib import admin
# from django.urls import path
# from django.conf import settings
# from django.conf.urls.static import static

# # Import Views
# from . import views

# # Import APIs
# from .api.serializers import StudentDashboardAPI, ParentDashboardAPI
# from .views import AdminDashboardAPI 

# urlpatterns = [
#     path('admin/', admin.site.urls),
    
#     # Auth
#     path('login/', views.login_view, name='login'),
#     path('logout/', views.logout_view, name='logout'),
    
#     # Dashboard Pages
#     path('admin-dashboard/', views.admin_dashboard_view, name='admin_dashboard'),
#     path('register-student/', views.student_registration_view, name='register_student'),
#     path('student/dashboard/', views.student_dashboard, name='student-dashboard'),
    
#     # Student/Parent/Automation Pages
#     path('parent/dashboard/', views.parent_dashboard, name='parent-dashboard'),
#     path('automation/logs/', views.automation_logs, name='automation-logs'),
    
#     # Automation Action
#     path('admin/edupilot_core/feevoucher/generate-all-fees/', views.generate_fees_view, name='generate_fees_view'),
    
#     # API Endpoints
#     path('api/student/dashboard/', StudentDashboardAPI.as_view(), name='student-dashboard-api'),
#     path('api/parent/dashboard/', ParentDashboardAPI.as_view(), name='parent-dashboard-api'),
#     path('api/admin/dashboard/', AdminDashboardAPI.as_view(), name='admin-dashboard-api'),
# ]

# # Media Files
# if settings.DEBUG:
#     urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)


# from django.contrib import admin
# from django.urls import path
# from django.conf import settings
# from django.conf.urls.static import static

# # Import Views
# from . import views

# # Import APIs
# from .views import AdminDashboardAPI 

# urlpatterns = [
#     path('admin/', admin.site.urls),
    
#     # Auth
#     path('login/', views.login_view, name='login'),
#     path('logout/', views.logout_view, name='logout'),
    
#     # Dashboard Pages
#     path('admin-dashboard/', views.admin_dashboard_view, name='admin_dashboard'),
#     path('register-student/', views.student_registration_view, name='register_student'),
#     path('student/dashboard/', views.student_dashboard, name='student-dashboard'),
#     path('teacher/dashboard/', views.teacher_dashboard, name='teacher-dashboard'),
    
#     # Student/Parent/Automation Pages
#     path('parent/dashboard/', views.parent_dashboard, name='parent-dashboard'),
#     path('automation/logs/', views.automation_logs, name='automation-logs'),
    
#     # Automation Action
#     path('admin/edupilot_core/feevoucher/generate-all-fees/', views.generate_fees_view, name='generate_fees_view'),
    
#     # API Endpoints
#     path('api/admin/dashboard/', AdminDashboardAPI.as_view(), name='admin-dashboard-api'),
# ]

# # Media Files
# if settings.DEBUG:
#     urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

# from django.urls import path
# from . import views
# from .views import AdminDashboardAPI

# urlpatterns = [
#     # Automation Pages
#     path('automation/logs/', views.automation_logs, name='automation-logs'),

#     # Automation Action
#     path('feevoucher/generate-all-fees/', views.generate_fees_view, name='generate_fees_view'),

#     # API Endpoint
#     path('api/dashboard/', AdminDashboardAPI.as_view(), name='edupilot-admin-dashboard-api'),
# ]

from django.urls import path
from . import views
from . import crud_views
from .views import AdminDashboardAPI

urlpatterns = [
    path('', views.automation_dashboard, name='automation-dashboard'),
    path('fee/', views.fee_automation_view, name='fee-automation'),
    path('vouchers/', views.voucher_management_view, name='voucher-management'),
    path('notifications/', views.notification_queue_view, name='notification-queue'),
    path('salary/', views.salary_automation_view, name='salary-automation'),
    path('payslips/', views.payslip_management_view, name='payslip-management'),
    path('logs/', views.automation_logs, name='automation-logs'),
    path('settings/', views.automation_settings_view, name='automation-settings'),

    # --- CRUD Data Management (naye routes) ---
    path('data/<str:model_name>/', crud_views.crud_list_view, name='crud-list'),
    path('data/<str:model_name>/add/', crud_views.crud_create_view, name='crud-create'),
    path('data/<str:model_name>/<int:pk>/edit/', crud_views.crud_update_view, name='crud-update'),
    path('data/<str:model_name>/<int:pk>/delete/', crud_views.crud_delete_view, name='crud-delete'),

    path('feevoucher/generate-all-fees/', views.generate_fees_view, name='generate_fees_view'),
    path('api/dashboard/', AdminDashboardAPI.as_view(), name='edupilot-admin-dashboard-api'),
    path('timetable/', views.timetable_list, name='timetable-list'),
path('periods/', views.create_period, name='create-period'),
path('absence/', views.mark_absence, name='mark-absence'),
path('fixtures/', views.fixture_auto_assign, name='fixtures-list'),
path('teacher/schedule/', views.teacher_schedule, name='teacher-schedule'),
path('timetable/logs/', views.timetable_logs, name='timetable-logs'),
]



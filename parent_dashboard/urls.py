# from django.urls import path
# from .import views

# urlpatterns = [
#     path('home/', views.parent_dashboard_home, name='parent_dashboard_home'),
#     path('dashboard/', views.parent_dashboard, name='parent_dashboard'),
#     path('list/', views.parent_list, name='parent_list'),  # ← ye add karo
# ]







from django.urls import path
from parent_dashboard import views
from edupilot_core import voucher_portal

urlpatterns = [
    path('vouchers/', voucher_portal.portal_vouchers, {'portal_role': 'PARENT'}, name='parent_vouchers'),
    path('vouchers/summary/', voucher_portal.voucher_summary, {'portal_role': 'PARENT'}, name='parent_voucher_summary'),
    path('vouchers/<int:delivery_id>/view/', voucher_portal.voucher_view, {'portal_role': 'PARENT'}, name='parent_voucher_view'),
    path('vouchers/<int:delivery_id>/download/', voucher_portal.voucher_download, {'portal_role': 'PARENT'}, name='parent_voucher_download'),
    path('vouchers/<int:delivery_id>/dismiss/', voucher_portal.voucher_dismiss, {'portal_role': 'PARENT'}, name='parent_voucher_dismiss'),
    path('notifications/<int:notification_id>/read/', voucher_portal.notification_read, {'portal_role': 'PARENT'}, name='parent_notification_read'),
    path("announcements/", views.parent_announcements, name="parent_announcements"),
    path("help-support/report-issue/", views.parent_report_issue, name="parent_report_issue"),
    path("help-support/requested-reports/", views.parent_requested_reports, name="parent_requested_reports"),
    path("help-support/suggestion-bucket/", views.parent_suggestion_bucket, name="parent_suggestion_bucket"),
    path("help-support/my-suggestions/", views.parent_my_suggestions, name="parent_my_suggestions"),
    
    path(
        "home/",
        views.parent_dashboard_home,
        name="parent_dashboard_home"
    ),

    path(
        "",
        views.parent_dashboard,
        name="parent_dashboard"
    ),

    path(
        "list/",
        views.parent_list,
        name="parent_list"
    ),

    path(
        "attendance/",
        views.parent_attendance,
        name="parent_attendance"
    ),
   
    path(
        "result/",
        views.parent_result,
        name="parent_result"
    ),

    path(
        "assignments/",
        views.parent_assignment,
        name="parent_assignment"
    ),

    path(
        "quizzes/",
        views.parent_quizzes,
        name="parent_quizzes"
    ),

    path(
        "diary/",
        views.parent_diary,
        name="parent_diary"
    ),


    path(
        "timetable/",
        views.parent_timetable,
        name="parent_timetable"
    ),

]

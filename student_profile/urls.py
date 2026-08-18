# student_profile/urls.py mein ye URLs add karo
# =====================================================

from django.urls import include, path
from student_profile import views
from edupilot_core import voucher_portal
from django.views.generic import TemplateView

urlpatterns = [
    path('help-support/report-issue/', TemplateView.as_view(template_name='shared/help_support/report_issue.html', extra_context={'portal_base': 'student_profile/base.html', 'portal_label': 'Student', 'portal_kind': 'student', 'report_route': 'student_report_issue', 'reports_route': 'student_requested_reports', 'suggestion_route': 'student_suggestion_bucket', 'suggestions_route': 'student_my_suggestions'}), name='student_report_issue'),
    path('help-support/requested-reports/', TemplateView.as_view(template_name='shared/help_support/requested_reports.html', extra_context={'portal_base': 'student_profile/base.html', 'portal_label': 'Student', 'portal_kind': 'student', 'report_route': 'student_report_issue', 'reports_route': 'student_requested_reports', 'suggestion_route': 'student_suggestion_bucket', 'suggestions_route': 'student_my_suggestions'}), name='student_requested_reports'),
    path('help-support/suggestion-bucket/', TemplateView.as_view(template_name='shared/help_support/suggestion_bucket.html', extra_context={'portal_base': 'student_profile/base.html', 'portal_label': 'Student', 'portal_kind': 'student', 'report_route': 'student_report_issue', 'reports_route': 'student_requested_reports', 'suggestion_route': 'student_suggestion_bucket', 'suggestions_route': 'student_my_suggestions'}), name='student_suggestion_bucket'),
    path('help-support/my-suggestions/', TemplateView.as_view(template_name='shared/help_support/my_suggestions.html', extra_context={'portal_base': 'student_profile/base.html', 'portal_label': 'Student', 'portal_kind': 'student', 'report_route': 'student_report_issue', 'reports_route': 'student_requested_reports', 'suggestion_route': 'student_suggestion_bucket', 'suggestions_route': 'student_my_suggestions'}), name='student_my_suggestions'),
    path('vouchers/', voucher_portal.portal_vouchers, {'portal_role': 'STUDENT'}, name='student_vouchers'),
    path('vouchers/summary/', voucher_portal.voucher_summary, {'portal_role': 'STUDENT'}, name='student_voucher_summary'),
    path('vouchers/<int:delivery_id>/view/', voucher_portal.voucher_view, {'portal_role': 'STUDENT'}, name='student_voucher_view'),
    path('vouchers/<int:delivery_id>/download/', voucher_portal.voucher_download, {'portal_role': 'STUDENT'}, name='student_voucher_download'),
    path('vouchers/<int:delivery_id>/dismiss/', voucher_portal.voucher_dismiss, {'portal_role': 'STUDENT'}, name='student_voucher_dismiss'),
    path('notifications/<int:notification_id>/read/', voucher_portal.notification_read, {'portal_role': 'STUDENT'}, name='student_notification_read'),
    path('announcements/', views.student_announcements, name='student_announcements'),

    # ── Dashboard ──
    path('dashboard/',
         views.student_dashboard,
         name='student_dashboard'),
    path('ai-tutor/', include('ai_tutor.urls')),
    
 

    # ── Admin: Naya student banao (email automatically jaegi) ──
    path('create/',
         views.create_student,
         name='create_student'),

    # ── Admin: Existing student ko dobara credentials email karo ──
    path('<int:student_id>/resend-credentials/',
         views.resend_credentials,
         name='resend_credentials'),

    # ── Assignment submit ──
    path('assignment/<int:assignment_id>/submit/',
         views.submit_assignment,
         name='submit_assignment'),
    
    path('quiz/<int:quiz_id>/submit/', views.submit_quiz, name='submit_quiz'),
    
    
    
    # ── Attendance ──
path(
    'attendance/',
    views.student_attendance,
    name='student_attendance'
),

# ── Result ──
path(
    'result/',
    views.student_result,
    name='student_result'
),

# ── E+ Result: Grade Predictor ──
path(
    'result/grade-predictor/',
    views.student_grade_predictor,
    name='student_grade_predictor'
),

# ── Assignments ──
path(
    'assignments/',
    views.student_assignments,
    name='student_assignments'
),


#── Quizzes ──
path(
    'quizzes/',
    views.student_quizzes,
    name='student_quizzes'
),

# ── Diary ──
path(
    'diary/',
    views.student_diary,
    name='student_diary'
),

# ── Timetable ──
path(
    'timetable/',
    views.student_timetable,
    name='student_timetable'
),
]

# student_profile/urls.py mein ye URLs add karo
# =====================================================

from django.urls import path
from student_profile import views

urlpatterns = [

    # ── Dashboard ──
    path('dashboard/',
         views.student_dashboard,
         name='student_dashboard'),
    
 

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

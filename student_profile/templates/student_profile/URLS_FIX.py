# student_profile/urls.py mein ye URL add karo:
# (lecture_notes wali URL missing thi)

from django.urls import path
from . import views

urlpatterns = [
    # ... tumhare existing URLs ...

    path('assignments/',    views.student_assignments,   name='student_assignments'),
    path('quizzes/',        views.student_quizzes,       name='student_quizzes'),
    path('diary/',          views.student_diary,         name='student_diary'),
    path('lecture-notes/',  views.student_lecture_notes, name='student_lecture_notes'),  # ← NEW
    path('attendance/',     views.student_attendance,    name='student_attendance'),
    path('result/',         views.student_result,        name='student_result'),
    path('timetable/',      views.student_timetable,     name='student_timetable'),
]

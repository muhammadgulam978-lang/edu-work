# ============================================================
# STUDENT VIEWS — FIXED VERSION
# In karo copy: student_profile/views.py mein replace karo
# ============================================================

# Import mein ye add karo (already nahi hai to):
from teacher_dashboard.models import Assignment, Attendance, Quiz, LectureNote
from datetime import date as date_today_cls


# =============================================================
# STUDENT ASSIGNMENTS  (fix: today context add kiya)
# =============================================================
@login_required
def student_assignments(request):
    student = get_object_or_404(Student, user=request.user)

    assignments = Assignment.objects.filter(
        class_fk=student.class_fk,
        section=student.section,        # section filter bhi add kiya
    ).select_related('teacher', 'subject').order_by('-id')

    return render(request, 'student_profile/assignments.html', {
        'assignments': assignments,
        'today': date_today_cls.today(),   # due_date compare ke liye
    })


# =============================================================
# STUDENT QUIZZES  (fix: section + today add)
# =============================================================
@login_required
def student_quizzes(request):
    student = get_object_or_404(Student, user=request.user)

    quizzes = Quiz.objects.filter(
        class_fk=student.class_fk,
        section=student.section,
    ).select_related('teacher', 'subject').order_by('-id')

    return render(request, 'student_profile/quizzes.html', {
        'quizzes': quizzes,
        'today': date_today_cls.today(),
    })


# =============================================================
# STUDENT DIARY  (fix: section add)
# =============================================================
@login_required
def student_diary(request):
    student = get_object_or_404(Student, user=request.user)

    diaries = Diary.objects.filter(
        class_fk=student.class_fk,
        section=student.section,
    ).select_related('teacher', 'subject').order_by('-date')

    return render(request, 'student_profile/diary.html', {
        'diaries': diaries,
    })


# =============================================================
# STUDENT LECTURE NOTES  ← NEW VIEW (pehle tha hi nahi)
# =============================================================
@login_required
def student_lecture_notes(request):
    student = get_object_or_404(Student, user=request.user)

    lecture_notes = LectureNote.objects.filter(
        class_fk=student.class_fk,
        section=student.section,
    ).select_related('teacher', 'subject').order_by('-id')

    return render(request, 'student_profile/lecture_notes.html', {
        'lecture_notes': lecture_notes,
    })

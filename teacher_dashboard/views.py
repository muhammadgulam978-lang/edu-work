from datetime import timedelta, date
from django.shortcuts import render, redirect, get_object_or_404
from django.views.decorators.csrf import csrf_exempt, csrf_protect
from django.views.decorators.http import require_http_methods, require_POST
from django.contrib.auth.models import User
from django.http import JsonResponse
from django.utils.dateparse import parse_date
from django.views.decorators.http import require_GET
import difflib
import json
import requests
from bs4 import BeautifulSoup
# from admin_panel.models import LessonDay, LessonPlanRequest, GuideBook, CurriculumSource
from django.conf import settings
from django.test import RequestFactory
from google import genai
import traceback
from langdetect import detect
import re
# import google.generativeai as genai
from groq import Groq
from django.contrib.auth.decorators import permission_required



# ===================================================
# add near top of teacher_dashboard/views.py (imports area)
from teacher_dashboard.models import Teacher
from django.shortcuts import get_object_or_404

def get_selected_teacher(request):
    """
    Agar admin (is_staff) ne teacher select kiya ho -> woh teacher return kare.
    Warna agar normal teacher logged in ho to uska teacher profile return kare.
    Agar kuch bhi missing ho to None return kare.
    Usage: teacher = get_selected_teacher(request)
    - For admin: pass ?teacher_id=NN in GET or include teacher_id in POST form.
    """
    teacher_id = request.GET.get('teacher_id') or request.POST.get('teacher_id')

    # agar admin ne kisi teacher ko select kia ho
    if request.user.is_staff and teacher_id:
        try:
            return Teacher.objects.get(id=teacher_id)
        except Teacher.DoesNotExist:
            return None

    # agar normal teacher user hai
    try:
        return Teacher.objects.get(user=request.user)
    except Teacher.DoesNotExist:
        return None

# ===================================================

def get_next_school_day(d):
    while d.weekday() > 4:  # Skip Saturday/Sunday
        d += timedelta(days=1)
    return d

# 
# login required
# teacher_dashboard/views.py
from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from admin_panel.utils import role_required
from teacher_dashboard.models import Teacher
from admin_panel.models import AssignedPeriod , ClassTeacher

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from admin_panel.models import AssignedPeriod, ClassTeacher, AcademicYear
from teacher_dashboard.models import Teacher
from datetime import date


# 🔥 Helper - Get active academic year
def get_active_year():
    
    return AcademicYear.objects.filter(is_active=True).first()


@login_required
def teacher_dashboard_view(request):
    
    teacher = get_selected_teacher(request)
    
    if not teacher:
        
        messages.error(request, "Teacher select karo pehle.")
        return redirect('select_teacher_for_action')
  
    # ==========================
    # 1️⃣ Get Active Academic Year
    # ==========================
    academic_year = get_active_year()

    # ==========================
    # 2️⃣ Assigned Regular Periods
    # ==========================
    assigned_periods = AssignedPeriod.objects.filter(teacher=teacher).select_related(
        'class_fk', 'section', 'subject', 'period'
    )

    # ==========================
    # 3️⃣ Get Sections where THIS teacher is Class Teacher
    # ==========================
    class_teacher_set = set(
        ClassTeacher.objects.filter(
            teacher=teacher,
            academic_year=academic_year
        ).values_list('class_fk_id', 'section_id')
    )

    # Apply flag to each period
    for period in assigned_periods:
        period.is_class_teacher = (
            (period.class_fk_id, period.section_id) in class_teacher_set
        )

    # ==========================
    # 4️⃣ Fixture Assignments (if any)
    # ==========================
    today = date.today()
    fixture_list = []  # If you have fixture logic, you can fill it here

    # Example (if required):
    # fixture_list = get_fixture_for_teacher(teacher)

    context = {
        "teacher": teacher,
        "assigned_periods": assigned_periods,
        "fixture_list": fixture_list,
    }

    return render(request, "teacher_dashboard/teacher_dashboard.html", context)

# show students in a class and section
from student_profile.models import Student

@login_required
def view_students(request, class_id, section_id):
    students = Student.objects.filter(
        class_fk_id=class_id,   # direct ForeignKey id filter
        section_id=section_id
    )

    return render(request, 'teacher_dashboard/view_students.html', {
        'students': students
    })
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from student_profile.models import Student
from admin_panel.models import AssignedPeriod
from .models import Attendance
from django.utils import timezone
from django.contrib import messages

@login_required
def mark_attendance(request, assigned_period_id):
    assigned_period = get_object_or_404(AssignedPeriod, pk=assigned_period_id)

    # Correct filtering students by foreign keys, not by class_name string
    students = Student.objects.filter(
        class_fk=assigned_period.class_fk,
        section=assigned_period.section
    )

    if request.method == 'POST':
        date_today = timezone.now().date()

        for student in students:
            status = request.POST.get(f'status_{student.id}')
            if status:
                Attendance.objects.update_or_create(
                    student=student,
                    date=date_today,
                    period=assigned_period,
                    defaults={
                        'status': status.lower(),
                        'class_fk': assigned_period.class_fk,
                        'section': assigned_period.section,
                    }
                )
        messages.success(request, "Attendance marked successfully.")
        return redirect('teacher_dashboard')

    return render(request, 'teacher_dashboard/mark_attendance.html', {
        'students': students,
        'assigned_period': assigned_period,
    })

from datetime import datetime
from django.shortcuts import render, get_object_or_404
from .models import AssignedPeriod, Attendance

@login_required
def view_attendance(request, assigned_period_id):
    assigned_period = get_object_or_404(AssignedPeriod, pk=assigned_period_id)

    # Get date from GET parameters
    date_str = request.GET.get('date')

    if date_str:
        try:
            filter_date = datetime.strptime(date_str, '%Y-%m-%d').date()
        except ValueError:
            filter_date = None
    else:
        # Get the latest attendance date if no date is provided
        latest_attendance = Attendance.objects.filter(period=assigned_period).order_by('-date').first()
        filter_date = latest_attendance.date if latest_attendance else None

    if filter_date:
        attendance_records = Attendance.objects.filter(
            period=assigned_period,
            date=filter_date
        ).select_related('student')
    else:
        attendance_records = Attendance.objects.none()  # No entries if no date exists

    return render(request, 'teacher_dashboard/view_attendance.html', {
        'assigned_period': assigned_period,
        'attendance_records': attendance_records,
        'filter_date': filter_date
    })


@login_required
def attendance_summary(request, assigned_period_id):
    assigned_period = get_object_or_404(AssignedPeriod, pk=assigned_period_id)

    # Step 1: Get all students in the class & section
    students = Student.objects.filter(
        class_fk=assigned_period.class_fk,
        section=assigned_period.section
    )

    summary_data = []

    for student in students:
        total = Attendance.objects.filter(student=student, period=assigned_period).count()
        present = Attendance.objects.filter(student=student, period=assigned_period, status='present').count()
        absent = Attendance.objects.filter(student=student, period=assigned_period, status='absent').count()
        leave = Attendance.objects.filter(student=student, period=assigned_period, status='leave').count()
        percentage = round((present / total) * 100, 2) if total > 0 else 0

        summary_data.append({
            'student': student,
            'present': present,
            'absent': absent,
            'leave': leave,
            'total': total,
            'percentage': percentage,
        })

    return render(request, 'teacher_dashboard/attendance_summary.html', {
        'assigned_period': assigned_period,
        'summary_data': summary_data
    })

# teacher_dashboard/views.py
# teacher_dashboard/views.py
from django.shortcuts import render, redirect
from django.contrib import messages
from admin_panel.models import Class, Section, Subject, ExamResult
from student_profile.models import Student
from django.contrib.auth.decorators import login_required

@login_required
def upload_result(request, class_id, section_id, subject_id):
    teacher = get_selected_teacher(request)
    if not teacher:
        messages.error(request, "Teacher select karo pehle.")
        return redirect('select_teacher_for_action')

    term = request.GET.get('term') or request.POST.get('term') or 'midterm'

    students = Student.objects.filter(class_fk_id=class_id, section_id=section_id)
    subject = Subject.objects.get(id=subject_id)

    existing_results = ExamResult.objects.filter(
        class_fk_id=class_id,
        section_id=section_id,
        subject_id=subject_id,
        term=term
    )

    results_dict = {res.student_id: res for res in existing_results}
    total_marks_value = existing_results.first().total_marks if existing_results.exists() else ""

    if request.method == 'POST':
        total_marks = request.POST.get('total_marks')

        for student in students:
            marks = request.POST.get(f'marks_{student.id}')
            if marks != "":
                ExamResult.objects.update_or_create(
                    student=student,
                    subject_id=subject_id,
                    class_fk_id=class_id,
                    section_id=section_id,
                    term=term,
                    defaults={
                        'marks_obtained': marks,
                        'total_marks': total_marks,
                        'teacher': teacher  # save selected teacher
                    }
                )

        messages.success(request, "Results saved successfully.")
        return redirect(f"{request.path}?term={term}&teacher_id={teacher.id}")

    return render(request, 'teacher_dashboard/upload_result.html', {
        'students': students,
        'subject': subject,
        'term': term,
        'results': results_dict,
        'total_marks_value': total_marks_value,
        'teacher': teacher,
    })


from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from admin_panel.models import ClassTeacher, ExamResult
from student_profile.models import Student
from teacher_dashboard.models import Teacher
from django.contrib.auth.decorators import login_required

@login_required
def merge_result(request, class_id, section_id):
    teacher = get_selected_teacher(request)
    if not teacher:
        messages.error(request, "Teacher select karo pehle.")
        return redirect('select_teacher_for_action')

    term = request.GET.get('term') or request.POST.get('term') or 'midterm'

    is_class_teacher = ClassTeacher.objects.filter(
        teacher=teacher,
        class_fk_id=class_id,
        section_id=section_id
    ).exists()

    if not is_class_teacher:
        messages.error(request, "Selected teacher is not the class teacher for this section.")
        return redirect('teacher_dashboard')

    students = Student.objects.filter(class_fk_id=class_id, section_id=section_id)

    # Get all subjects for which result exists
    subjects = Subject.objects.filter(
        examresult__class_fk_id=class_id,
        examresult__section_id=section_id,
        examresult__term=term
    ).distinct()

    # Build result data
    result_data = []
    for student in students:
        student_row = {
            'student': student,
            'marks': {},
            'remarks': ''
        }

        for subject in subjects:
            result = ExamResult.objects.filter(
                student=student,
                subject=subject,
                class_fk_id=class_id,
                section_id=section_id,
                term=term
            ).first()
            if result:
                student_row['marks'][subject.name] = f"{result.marks_obtained} / {result.total_marks}"
                student_row['remarks'] = result.teacher_remarks or ''
            else:
                student_row['marks'][subject.name] = "-"
        result_data.append(student_row)

    # Save remarks
    if request.method == 'POST':
        for student in students:
            remark_text = request.POST.get(f'remarks_{student.id}', '').strip()
            ExamResult.objects.filter(
                student=student,
                class_fk_id=class_id,
                section_id=section_id,
                term=term
            ).update(teacher_remarks=remark_text)
        messages.success(request, f"Remarks saved for {term.title()} successfully.")
        return redirect(f"{request.path}?term={term}")

    return render(request, 'teacher_dashboard/merge_result.html', {
        'term': term,
        'subjects': subjects,
        'result_data': result_data,
    })

# LMS logic Start here
# views.py
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, get_object_or_404
from admin_panel.models import AssignedPeriod
from teacher_dashboard.models import Teacher
@login_required
def lms_dashboard(request):
    teacher = get_object_or_404(Teacher, user=request.user)
    assigned_periods = AssignedPeriod.objects.filter(teacher=teacher).values(
        'class_fk__id',
        'class_fk__class_name',
        'section__id',
        'section__section_name',
        'subject__id',
        'subject__name',
        'subject__stream__id',
        'subject__stream__stream_name'
    ).distinct()

    return render(request, 'teacher_dashboard/lms_dashboard.html', {
        'assigned_periods': assigned_periods,
        'teacher': teacher,
    })


@login_required
def lms_actions_menu(request, class_id, section_id, subject_id):
    class_obj = get_object_or_404(Class, id=class_id)
    section_obj = get_object_or_404(Section, id=section_id)
    subject_obj = get_object_or_404(Subject, id=subject_id)

    return render(request, 'teacher_dashboard/lms_actions_menu.html', {
        'class_obj': class_obj,
        'section_obj': section_obj,
        'subject_obj': subject_obj,
    })


from teacher_dashboard.models import LectureNote

@login_required
def upload_lecture_note(request, class_id, section_id, subject_id):
    teacher = get_selected_teacher(request)
    if not teacher:
        messages.error(request, "Teacher select karo pehle.")
        return redirect('select_teacher_for_action')

    if request.method == 'POST':
        title = request.POST['title']
        description = request.POST.get('description', '')
        file = request.FILES.get('file')

        LectureNote.objects.create(
            teacher=teacher,
            class_fk_id=class_id,
            section_id=section_id,
            subject_id=subject_id,
            title=title,
            description=description,
            file=file
        )
        messages.success(request, "Lecture uploaded successfully.")
        return redirect(f'/teacher_dashboard/upload_lecture_note/{class_id}/{section_id}/{subject_id}/?teacher_id={teacher.id}')

    lectures = LectureNote.objects.filter(
        teacher=teacher,
        class_fk_id=class_id,
        section_id=section_id,
        subject_id=subject_id
    ).order_by('-id')

    return render(request, 'teacher_dashboard/upload_lecture_note.html', {
        'lectures': lectures,
        'class_id': class_id,
        'section_id': section_id,
        'subject_id': subject_id,
        'teacher': teacher,
    })



from teacher_dashboard.models import Assignment

@login_required
def upload_assignment(request, class_id, section_id, subject_id):
    teacher = get_selected_teacher(request)
    if not teacher:
        messages.error(request, "Teacher select karo pehle.")
        return redirect('select_teacher_for_action')

    if request.method == 'POST':
        title = request.POST['title']
        description = request.POST.get('description', '')
        file = request.FILES.get('file')
        due_date = request.POST.get('due_date')

        Assignment.objects.create(
            teacher=teacher,
            class_fk_id=class_id,
            section_id=section_id,
            subject_id=subject_id,
            title=title,
            description=description,
            file=file,
            due_date=due_date
        )
        messages.success(request, "Assignment uploaded successfully.")
        return redirect(f'/teacher_dashboard/upload_assignment/{class_id}/{section_id}/{subject_id}/?teacher_id={teacher.id}')

    assignments = Assignment.objects.filter(
        teacher=teacher,
        class_fk_id=class_id,
        section_id=section_id,
        subject_id=subject_id
    ).order_by('-id')

    return render(request, 'teacher_dashboard/upload_assignment.html', {
        'assignments': assignments,
        'class_id': class_id,
        'section_id': section_id,
        'subject_id': subject_id,
        'teacher': teacher,
    })



@login_required
def view_assignments(request, class_id, section_id, subject_id):
    teacher = get_object_or_404(Teacher, user=request.user)

    assignments = Assignment.objects.filter(
        teacher=teacher,
        class_fk_id=class_id,
        section_id=section_id,
        subject_id=subject_id
    )

    class_obj = get_object_or_404(Class, id=class_id)
    section_obj = get_object_or_404(Section, id=section_id)
    subject_obj = get_object_or_404(Subject, id=subject_id)

    return render(request, 'teacher_dashboard/view_assignments.html', {
        'assignments': assignments,
        'class_obj': class_obj,
        'section_obj': section_obj,
        'subject_obj': subject_obj,
    })


from teacher_dashboard.models import Quiz

@login_required
def upload_quiz(request, class_id, section_id, subject_id):
    teacher = get_selected_teacher(request)
    if not teacher:
        messages.error(request, "Teacher select karo pehle.")
        return redirect('select_teacher_for_action')

    if request.method == 'POST':
        title = request.POST['title']
        file = request.FILES.get('file')
        due_date = request.POST.get('due_date')

        Quiz.objects.create(
            teacher=teacher,
            class_fk_id=class_id,
            section_id=section_id,
            subject_id=subject_id,
            title=title,
            file=file,
            due_date=due_date
        )
        messages.success(request, "Quiz uploaded successfully.")
        return redirect(f'/teacher_dashboard/upload_quiz/{class_id}/{section_id}/{subject_id}/?teacher_id={teacher.id}')

    quizzes = Quiz.objects.filter(
        teacher=teacher,
        class_fk_id=class_id,
        section_id=section_id,
        subject_id=subject_id
    ).order_by('-id')

    return render(request, 'teacher_dashboard/upload_quiz.html', {
        'quizzes': quizzes,
        'class_id': class_id,
        'section_id': section_id,
        'subject_id': subject_id,
        'teacher': teacher,
    })



# ================================================================
# teacher_dashboard/views.py mein ye 2 functions ADD karo
# ================================================================

from student_profile.models import AssignmentSubmission

@login_required
def view_assignment_submissions(request, class_id, section_id, subject_id):
    teacher = get_object_or_404(Teacher, user=request.user)

    assignments = Assignment.objects.filter(
        teacher=teacher,
        class_fk_id=class_id,
        section_id=section_id,
        subject_id=subject_id
    ).order_by('-id')

    assignments_with_subs = []
    for assignment in assignments:
        submissions = AssignmentSubmission.objects.filter(
            assignment=assignment
        ).select_related('student').order_by('-submitted_at')

        assignments_with_subs.append({
            'assignment': assignment,
            'submissions': submissions,
            'count': submissions.count(),
        })

    return render(request, 'teacher_dashboard/view_assignment_submissions.html', {
        'assignments_with_subs': assignments_with_subs,
        'class_id': class_id,
        'section_id': section_id,
        'subject_id': subject_id,
    })


@login_required
def give_assignment_marks(request, submission_id):
    submission = get_object_or_404(AssignmentSubmission, id=submission_id)

    if request.method == 'POST':
        marks = request.POST.get('marks')
        if marks is not None:
            submission.marks = marks
            submission.save()
            messages.success(request, f"Marks saved for {submission.student.name}.")

    # Back to submissions page
    assignment = submission.assignment
    return redirect(
        'view_assignment_submissions',
        class_id=assignment.class_fk_id,
        section_id=assignment.section_id,
        subject_id=assignment.subject_id,
    )


from django.contrib.auth.decorators import login_required
from django.shortcuts import render, get_object_or_404
from django.contrib import messages
from teacher_dashboard.models import Quiz, Teacher
from student_profile.models import QuizSubmission

@login_required
@login_required
def view_quiz_submissions(request, class_id, section_id, subject_id):
    teacher = get_selected_teacher(request)
    if not teacher:
        messages.error(request, "Teacher select karo pehle.")
        return redirect('select_teacher_for_action')

    # ✅ Get ALL quizzes for this class/section/subject
    quizzes = Quiz.objects.filter(
        teacher=teacher,
        class_fk_id=class_id,
        section_id=section_id,
        subject_id=subject_id
    )

    quizzes_with_submissions = []
    for quiz in quizzes:
        submissions = QuizSubmission.objects.filter(quiz=quiz)
        quizzes_with_submissions.append({
            'quiz': quiz,
            'submissions': submissions,
        })

    if request.method == 'POST':
        quiz_id = request.POST.get('quiz_id')
        quiz = get_object_or_404(Quiz, id=quiz_id, teacher=teacher)
        submissions = QuizSubmission.objects.filter(quiz=quiz)
        for submission in submissions:
            marks = request.POST.get(f'marks_{submission.id}')
            if marks:
                submission.marks = marks
                submission.save()
        messages.success(request, "Marks updated successfully.")
        return redirect(request.path)

    return render(request, 'teacher_dashboard/view_quiz_submissions.html', {
        'quizzes_with_submissions': quizzes_with_submissions,
        'class_id': class_id,
        'section_id': section_id,
        'subject_id': subject_id,
        'teacher': teacher,
    })


@login_required
def submit_diary(request, class_id, section_id, subject_id):
    teacher = get_selected_teacher(request)
    if not teacher:
        messages.error(request, "Teacher select karo pehle.")
        return redirect('select_teacher_for_action')

    if request.method == 'POST':
        content = request.POST['content']
        Diary.objects.create(
            teacher=teacher,
            class_fk_id=class_id,
            section_id=section_id,
            subject_id=subject_id,
            content=content
        )
        messages.success(request, f"Diary {teacher.name} ke naam se submit hogayi.")
        # agar admin ho to redirect back to select page ya same form with teacher_id
        if request.user.is_staff:
            return redirect(f"{request.path}?teacher_id={teacher.id}")
        return redirect('teacher_dashboard')

    diaries = Diary.objects.filter(
        teacher=teacher,
        class_fk_id=class_id,
        section_id=section_id,
        subject_id=subject_id
    ).order_by('-date')

    return render(request, 'teacher_dashboard/submit_diary.html', {
        'diaries': diaries,
        'class_id': class_id,
        'section_id': section_id,
        'subject_id': subject_id,
        'teacher': teacher,
    })



from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from admin_panel.models import Diary
from teacher_dashboard.models import Teacher

@login_required
def view_diary_student(request, class_id, section_id, subject_id):
    teacher = get_object_or_404(Teacher, user=request.user)

    # Get all diaries for this class, section, subject
    diaries = Diary.objects.filter(
        class_fk_id=class_id,
        section_id=section_id,
        subject_id=subject_id
    ).order_by('-date')

    return render(request, 'teacher_dashboard/view_diary.html', {
        'diaries': diaries
    })


# -----------------------------------------------------------------
# -----------------------------------------------------------------
from admin_panel.models import ExamFormat, Question

@login_required
def teacher_select_format(request, class_id, subject_id, section_id):
    formats = ExamFormat.objects.filter(class_obj_id=class_id, subject_id=subject_id)
    sections = Section.objects.filter(class_fk_id=class_id, id=section_id)

    formats_with_sections = []
    for f in formats:
        for s in sections:
            formats_with_sections.append({"format": f, "section": s})

    return render(request, "teacher_dashboard/select_format.html", {
        "formats_with_sections": formats_with_sections
    })


@login_required
def add_question(request, class_id, subject_id, format_id, section_id):
    exam_format = get_object_or_404(ExamFormat, id=format_id)
    section = get_object_or_404(Section, id=section_id)
    class_obj = get_object_or_404(Class, id=class_id)
    subject_obj = get_object_or_404(Subject, id=subject_id)

    if request.method == "POST":
        q_type = request.POST.get("question_type")
        text = request.POST.get("text")

        # Default options None
        option_a = request.POST.get("option_a") if q_type == "MCQ" else None
        option_b = request.POST.get("option_b") if q_type == "MCQ" else None
        option_c = request.POST.get("option_c") if q_type == "MCQ" else None
        option_d = request.POST.get("option_d") if q_type == "MCQ" else None

        Question.objects.create(
            exam_format=exam_format,
            teacher=request.user,
            section=section,
            question_type=q_type,
            text=text,
            option_a=option_a,
            option_b=option_b,
            option_c=option_c,
            option_d=option_d,
        )
        return redirect(
            "my_questions",
            class_id=class_id,
            subject_id=subject_id,
            section_id=section_id
        )

    return render(
        request,
        "teacher_dashboard/add_question.html",
        {
            "exam_format": exam_format,
            "section": section,
            "class_obj": class_obj,
            "subject_obj": subject_obj
        },
    )



@login_required
def my_questions(request, class_id, subject_id, section_id):
    # Teacher ke related formats (sirf unhi subjects/classes/sections ke)
    formats = ExamFormat.objects.filter(
        class_obj_id=class_id,
        subject_id=subject_id
    )

    return render(request, "teacher_dashboard/my_questions.html", {
        "formats": formats,
        "class_id": class_id,
        "subject_id": subject_id,
        "section_id": section_id,
    })


@login_required
def my_questions_by_format(request, class_id, subject_id, section_id, format_id):
    exam_format = get_object_or_404(ExamFormat, id=format_id)

    questions = Question.objects.filter(
        teacher=request.user,
        exam_format=exam_format,
        section_id=section_id
    )

    return render(request, "teacher_dashboard/my_questions_by_format.html", {
        "exam_format": exam_format,
        "questions": questions,
        "class_id": class_id,
        "subject_id": subject_id,
        "section_id": section_id,
    })


@login_required
def format_list(request, class_id, section_id, subject_id):
    class_obj = get_object_or_404(Class, id=class_id)
    section_obj = get_object_or_404(Section, id=section_id)
    subject_obj = get_object_or_404(Subject, id=subject_id)

    formats = ExamFormat.objects.filter(class_obj=class_obj, subject=subject_obj)

    return render(request, "teacher_dashboard/format_list.html", {
        "formats": formats,
        "class_obj": class_obj,
        "section_obj": section_obj,
        "subject_obj": subject_obj,
    })


# teacher_dashboard/views.py
from django.contrib.auth.decorators import login_required, permission_required
from django.shortcuts import render, get_object_or_404, redirect
from admin_panel.models import AssignedPeriod, ClassTeacher, TeacherFixture
from teacher_dashboard.models import Teacher
from django.utils import timezone

@login_required
def teacher_dashboard_view(request):
    teacher = get_selected_teacher(request)
    if not teacher:
        if request.user.is_staff:
            return redirect('select_teacher_for_action')
        teacher = get_object_or_404(Teacher, user=request.user)

    assigned_periods = AssignedPeriod.objects.filter(teacher=teacher)
    fixture_assignments = TeacherFixture.objects.filter(substitute_teacher=teacher)
    today = timezone.now().date()  # ✅ current date

    fixture_list = []
    for f in fixture_assignments:
        original_period = AssignedPeriod.objects.filter(
            teacher=f.absent_teacher,
            class_fk=f.class_fk,
            section=f.section,
            period=f.period
        ).first()
        fixture_list.append({
            "fixture": f,
            "original_period_id": original_period.id if original_period else None,
            "is_expired": f.date < today  # ✅ check if fixture date has passed
        })

    return render(request, "teacher_dashboard/teacher_dashboard.html", {
        "teacher": teacher,
        "assigned_periods": assigned_periods,
        "fixture_list": fixture_list,
    })



from django.shortcuts import render, get_object_or_404, redirect
from django.http import HttpResponse
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from admin_panel.models import AssignedPeriod, TeacherFixture
from student_profile.models import Student
from teacher_dashboard.models import Attendance
import datetime


@login_required
def mark_attendance(request, assigned_period_id):

    assigned_period = get_object_or_404(
        AssignedPeriod,
        id=assigned_period_id
    )

    if assigned_period.teacher.user != request.user:

        fixture = TeacherFixture.objects.filter(
            substitute_teacher__user=request.user,
            absent_teacher=assigned_period.teacher,
            class_fk=assigned_period.class_fk,
            section=assigned_period.section,
            period=assigned_period.period
        ).first()

        if not fixture:
            return HttpResponse(
                "❌ Unauthorized Access: You are not assigned for this period."
            )

    students = Student.objects.filter(
        class_fk=assigned_period.class_fk,
        section=assigned_period.section
    ).order_by("roll_no")

    if request.method == "POST":

        teacher = Teacher.objects.get(user=request.user)

        today = datetime.date.today()

        for student in students:

            status = request.POST.get(
                f"status_{student.id}",
                "absent"
            )

            Attendance.objects.update_or_create(

                student=student,
                date=today,
                period=assigned_period,

                defaults={

                    "status": status,
                    "class_fk": assigned_period.class_fk,
                    "section": assigned_period.section,
                    "marked_by": teacher,

                }
            )

        messages.success(
            request,
            "✅ Attendance marked successfully!"
        )

        return redirect("teacher_dashboard_view")

    return render(
        request,
        "teacher_dashboard/mark_attendance.html",
        {
            "assigned_period": assigned_period,
            "students": students,
        },
    )


from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.utils import timezone
from admin_panel.models import Class, Section, Subject, Diary
from teacher_dashboard.models import Teacher


def submit_diary(request, class_id, section_id, subject_id):
    teacher = get_object_or_404(Teacher, user=request.user)
    class_obj = get_object_or_404(Class, id=class_id)
    section_obj = get_object_or_404(Section, id=section_id)
    subject_obj = get_object_or_404(Subject, id=subject_id)

    if request.method == "POST":
        content = request.POST.get("content", "").strip()

        if not content:
            messages.error(request, "⚠️ Diary content cannot be empty.")
            return redirect(request.path)

        Diary.objects.create(
            teacher=teacher,
            class_fk=class_obj,
            section=section_obj,
            subject=subject_obj,
            content=content,
            date=timezone.now().date()
        )

        messages.success(request, "✅ Diary submitted successfully!")
        return redirect("teacher_dashboard")

    # Agar GET request hai (page open karna hai)
    diaries = Diary.objects.filter(
        teacher=teacher,
        class_fk=class_obj,
        section=section_obj,
        subject=subject_obj
    ).order_by('-date')

    return render(request, 'teacher_dashboard/new_submit_diary.html', {
        'diaries': diaries,
        'class_id': class_id,
        'section_id': section_id,
        'subject_id': subject_id,
        'teacher': teacher,
    })


# teacher_dashboard/views.py
# teacher_dashboard/lesson_planning_views.py

import re

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, get_object_or_404, redirect

from admin_panel.models import (
    Book,
    Chapter,
    Topic,
    SubTopic,
    LessonPlanRequest,
    LessonDay,
    Class,
    Subject,
)

from teacher_dashboard.pdf_parsing import parse_book_toc


# -----------------------------
# AI reply ko structured blocks me todna
# -----------------------------
def parse_ai_reply(day_text: str):
    """
    Groq se aane wale Day content ko
    Objective / Activities / Materials / Assessment / Homework / Worksheet
    blocks me todta hai.
    """
    blocks = {
        "objective": "",
        "activities": "",
        "materials": "",
        "assessment": "",
        "homework": "",
        "worksheet": "",
    }

    current_key = None
    for line in day_text.splitlines():
        clean = line.strip()
        if not clean:
            continue

        lower = clean.lower()
        if lower.startswith("objective"):
            current_key = "objective"
            blocks[current_key] = clean.split(":", 1)[-1].strip()
        elif lower.startswith("activities"):
            current_key = "activities"
            blocks[current_key] = clean.split(":", 1)[-1].strip()
        elif lower.startswith("materials"):
            current_key = "materials"
            blocks[current_key] = clean.split(":", 1)[-1].strip()
        elif lower.startswith("assessment"):
            current_key = "assessment"
            blocks[current_key] = clean.split(":", 1)[-1].strip()
        elif lower.startswith("homework"):
            current_key = "homework"
            blocks[current_key] = clean.split(":", 1)[-1].strip()
        elif lower.startswith("worksheet"):
            current_key = "worksheet"
            blocks[current_key] = clean.split(":", 1)[-1].strip()
        elif current_key:
            # same section continue
            blocks[current_key] += " " + clean

    return blocks


# -----------------------------
# EK topic ke liye AI se lesson plan generate
# -----------------------------
def generate_lesson_plan_for_topic(user, chapter: Chapter, topic: Topic, periods: int):
    chapter_title = chapter.title
    topic_title = topic.title
    subject_title = chapter.book.subject.name
    book_title = chapter.book.title

    # 1) LessonPlanRequest row create
    plan = LessonPlanRequest.objects.create(
        teacher=user,
        chapter=chapter,
        total_periods=periods,
        status="generated"
    )

    # 2) Prompt build
    prompt = f"""
You are an expert school teacher. Create a detailed day-wise lesson plan.

Book: {book_title}
Subject: {subject_title}
Chapter: {chapter_title}
Topic: {topic_title}
Total Days (Periods): {periods}

The topic should be covered over exactly {periods} days. Avoid repeating objectives and activities.

Use this exact structure for each day:

Day X
Objective:
Activities:
Materials:
Assessment:
Homework:

Return only structured text with clearly labelled Day 1, Day 2, etc.
"""

    try:
        # 3) Groq API call
        client = Groq(api_key=settings.GROQ_API_KEY)
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=3000,
        )
        reply = response.choices[0].message.content or ""
    except Exception as e:
        reply = ""

    # 4) Fallback — agar AI reply nahi aya
    if not reply.strip():
        for i in range(1, periods + 1):
            LessonDay.objects.create(
                plan=plan,
                day_number=i,
                learning_objectives=f"Understand the concept of {topic_title}",
                teaching_content=f"Read & discuss main ideas of {topic_title}.",
                practice_work=f"Practice questions on {topic_title}.",
                assessment_tasks=f"Short oral/written quiz on {topic_title}.",
                homework_tasks=f"Review notes and complete textbook questions for {chapter_title}.",
            )
        return plan

    # 5) Reply ko Day wise split karo
    day_sections = re.split(r"\bDay\s+(\d+)\b[:：]?", reply, flags=re.IGNORECASE)
    # format: ["", "1", "content1", "2", "content2", ...]

    if len(day_sections) < 3:
        # Fallback
        for i in range(1, periods + 1):
            LessonDay.objects.create(
                plan=plan,
                day_number=i,
                learning_objectives=f"Understand the concept of {topic_title}",
                teaching_content=f"Read & discuss main ideas of {topic_title}.",
                practice_work=f"Practice questions on {topic_title}.",
                assessment_tasks=f"Short oral/written quiz on {topic_title}.",
                homework_tasks=f"Review notes and complete textbook questions for {chapter_title}.",
            )
        return plan

    # 6) Parse each day
    for idx in range(1, len(day_sections), 2):
        try:
            day_num = int(day_sections[idx])
        except ValueError:
            continue

        day_text = day_sections[idx + 1]
        ai_data = parse_ai_reply(day_text)

        LessonDay.objects.create(
            plan=plan,
            day_number=day_num,
            learning_objectives=ai_data.get("objective", ""),
            teaching_content=ai_data.get("activities", "") + "\n" + ai_data.get("materials", ""),
            practice_work=ai_data.get("worksheet", ""),
            assessment_tasks=ai_data.get("assessment", ""),
            homework_tasks=ai_data.get("homework", ""),
        )

    return plan


# -----------------------------
#  CHAPTER PDF UPLOAD + PARSE
# -----------------------------
from teacher_dashboard.pdf_parsing import parse_chapter_pdf

@login_required
def lesson_upload_chapter(request):
    book_id = request.GET.get("book") or request.POST.get("book_id")
    book = get_object_or_404(Book, id=book_id)

    if request.method == "POST":
        title = request.POST.get("title")
        pdf_file = request.FILES.get("pdf_file")

        chapter = Chapter.objects.create(
            title=title or pdf_file.name,
            pdf_file=pdf_file,
            class_for=book.class_for,
            subject=book.subject,
            book=book,
            uploaded_by=request.user
        )

        parse_chapter_pdf(chapter)

        return redirect("lesson_select_topics", chapter_id=chapter.id)

    return render(
        request,
        "teacher_dashboard/lesson_upload_chapter.html",
        {"book": book}
    )

# -----------------------------
#  TOPICS SELECTION (per chapter)
# -----------------------------
from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required

from admin_panel.models import Chapter, Topic
from teacher_dashboard.lesson_plan_generator import generate_rule_based_lesson_plan
from .lesson_plan_generator import generate_rule_based_lesson_plan

from django.shortcuts import render, redirect, get_object_or_404
from admin_panel.models import LessonPlanRequest, LessonDay
from .lesson_plan_generator import generate_rule_based_lesson_plan
from teacher_dashboard.models import Teacher


@login_required
def lesson_select_topics(request, chapter_id):

    chapter = get_object_or_404(Chapter, id=chapter_id)

    # topics = Topic.objects.filter(
    #     chapter=chapter
    # )
    
    topics = chapter.topics.all()

    if request.method == "POST":

        try:
            selected_topic_ids = request.POST.getlist("topics")

            total_periods = int(
                request.POST.get("total_periods", 1)
            )

        except Exception:
            messages.error(
                request,
                "Invalid total periods."
            )

            return redirect(
                "lesson_select_topics",
                chapter_id=chapter.id
            )

        # ✅ validation
        if not selected_topic_ids:

            messages.error(
                request,
                "Please select at least one topic."
            )

            return redirect(
                "lesson_select_topics",
                chapter_id=chapter.id
            )

        if total_periods < 1:

            messages.error(
                request,
                "Total periods must be greater than 0."
            )

            return redirect(
                "lesson_select_topics",
                chapter_id=chapter.id
            )

        # ✅ get selected topics
        selected_topics = Topic.objects.filter(
            id__in=selected_topic_ids,
            chapter=chapter
        )

        if not selected_topics.exists():

            messages.error(
                request,
                "Selected topics not found."
            )

            return redirect(
                "lesson_select_topics",
                chapter_id=chapter.id
            )

        # ✅ generate lesson plan
        try:

            lesson_plan_data = generate_rule_based_lesson_plan(
                topics=list(selected_topics),
                total_periods=total_periods
            )

            print("LESSON PLAN DATA:")
            print(lesson_plan_data)

        except Exception as e:

            print("LESSON PLAN GENERATION ERROR:", str(e))

            messages.error(
                request,
                f"Lesson plan generation failed: {str(e)}"
            )

            return redirect(
                "lesson_select_topics",
                chapter_id=chapter.id
            )

        # ✅ ensure data exists
        if not lesson_plan_data:

            messages.error(
                request,
                "Lesson plan generate nahi hua. Dobara try karein."
            )

            return redirect(
                "lesson_select_topics",
                chapter_id=chapter.id
            )

        # ✅ create main plan
        lesson_request = LessonPlanRequest.objects.create(
            chapter=chapter,
            teacher=request.user,
            total_periods=total_periods,
            status="generated"
        )

        # ✅ create lesson days
        created_days = 0

        for day in lesson_plan_data:

            try:

                LessonDay.objects.create(

                    plan=lesson_request,

                    day_number=day.get("period", created_days + 1),

                    learning_objectives="\n".join(
                        day.get("learning_objectives", [])
                    ),

                    teaching_content=(
                        day.get("main_teaching_content", "")
                        if isinstance(
                            day.get("main_teaching_content", ""),
                            str
                        )
                        else "\n".join(
                            day.get("main_teaching_content", [])
                        )
                    ),

                    practice_work="\n".join(
                        day.get("practice_work", [])
                    ),

                    assessment_tasks="\n".join(
                        day.get("assessment_tasks", [])
                    ),

                    homework_tasks="\n".join(
                        day.get("homework_tasks", [])
                    ),
                )

                created_days += 1

            except Exception as e:

                print("LESSON DAY SAVE ERROR:", str(e))

        # ✅ final validation
        if created_days == 0:

            lesson_request.delete()

            messages.error(
                request,
                "Lesson plan ke days generate nahi hue."
            )

            return redirect(
                "lesson_select_topics",
                chapter_id=chapter.id
            )

        messages.success(
            request,
            f"{created_days} lesson plan days generated successfully."
        )

        return redirect(
            "lms_chapter_lesson_plans",
            chapter_id=chapter.id
        )

    return render(
        request,
        "teacher_dashboard/lesson_select_topics.html",
        {
            "chapter": chapter,
            "topics": topics,
        }
    )


@login_required
def lms_books_list(request, class_id, section_id, subject_id):
    books = Book.objects.filter(
        class_for_id=class_id,
        subject_id=subject_id
    )

    return render(
        request,
        "teacher_dashboard/lms_books_list.html",
        {
            "books": books,
            "class_id": class_id,
            "section_id": section_id,
            "subject_id": subject_id,
        }
    )


@login_required
def lms_create_book(request, class_id, section_id, subject_id):
    if request.method == "POST":
        title = request.POST.get("title")

        Book.objects.create(
            title=title,
            class_for_id=class_id,
            subject_id=subject_id,
            uploaded_by=request.user
        )

        return redirect(
            "lms_books_list",
            class_id=class_id,
            section_id=section_id,
            subject_id=subject_id
        )

    return render(
        request,
        "teacher_dashboard/lms_create_book.html",
        {
            "class_id": class_id,
            "section_id": section_id,
            "subject_id": subject_id,
        }
    )

from admin_panel.models import Book, Chapter
from django.shortcuts import get_object_or_404, render
from django.contrib.auth.decorators import login_required


@login_required
def lms_book_chapters(request, book_id):
    book = get_object_or_404(Book, id=book_id)

    # ✅ ONLY chapters linked with THIS book
    chapters = Chapter.objects.filter(book=book)

    return render(
        request,
        "teacher_dashboard/lms_book_chapters.html",
        {
            "book": book,
            "chapters": chapters
        }
    )

@login_required
def lms_chapter_lesson_plans(request, chapter_id):
    chapter = get_object_or_404(Chapter, id=chapter_id)

    plans = LessonPlanRequest.objects.filter(chapter=chapter)

    return render(request, "teacher_dashboard/lms_chapter_lesson_plans.html", {
        "chapter": chapter,
        "plans": plans
    })




# -----------------------------
#  TEACHER ke sab Lesson Plans
# -----------------------------
@login_required
def lesson_plans_list(request):
    plans = LessonPlanRequest.objects.filter(
        teacher=request.user
    ).prefetch_related("lessonday_set").order_by("-created_at")

    return render(request, "teacher_dashboard/lesson_plans_list.html", {
        "plans": plans,
    })


@login_required
def lesson_plan_detail(request, plan_id):
    plan = get_object_or_404(LessonPlanRequest, id=plan_id)
    days = plan.lessons.all().order_by("day_number")  # ✅ related_name="lessons"

    return render(
        request,
        "teacher_dashboard/lesson_plan_detail.html",
        {
            "plan": plan,
            "days": days,
        }
    )

# teacher_dashboard/views.py

from django.shortcuts import render, get_object_or_404
from admin_panel.models import Topic


def generate_lesson_plan_view(request, topic_id):
    topic = get_object_or_404(Topic, id=topic_id)

    periods = int(request.POST.get("periods", 1))
    class_level = request.POST.get("class_level")  # optional

    lp = generate_lesson_plan_for_topic(topic, periods=periods, class_level=class_level)
    context = {
        "lesson_plan": lp.to_dict(),
        "topic": topic,
    }
    return render(request, "teacher_dashboard/lesson_plan_detail.html", context)


@login_required
def generate_lesson_plan(request, chapter_id):
    chapter = get_object_or_404(Chapter, id=chapter_id)

    topics = chapter.topics.all()
    if not topics.exists():
        messages.error(request, "Chapter topics not parsed yet")
        return redirect("lms_book_chapters", book_id=chapter.book.id)

    if request.method == "POST":
        topic_id = request.POST.get("topic_id")
        periods = int(request.POST.get("no_of_periods", 1))

        topic = get_object_or_404(Topic, id=topic_id)

        # create request
        plan = LessonPlanRequest.objects.create(
            teacher=request.user,
            chapter_title=chapter.title,
            topic_title=topic.title,
            no_of_periods=periods,
            planning_style="content_based"
        )

        # 🔁 content based split
        content_blocks = list(topic.content_blocks.all())
        chunk_size = max(1, len(content_blocks) // periods)

        for i in range(periods):
            chunk = content_blocks[i*chunk_size:(i+1)*chunk_size]
            text = "\n".join(cb.text for cb in chunk)

            LessonDay.objects.create(
                plan=plan,
                day_number=i+1,
                objective=f"Understand {topic.title}",
                activities=text,
                assessment=text,
                homework=text,
                ai_source="parsed_pdf"
            )

        messages.success(request, "Lesson plan generated successfully")
        return redirect("lms_chapter_lesson_plans", chapter_id=chapter.id)

    return render(request, "teacher_dashboard/generate_lesson_plan.html", {
        "chapter": chapter,
        "topics": topics
    })


from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.timezone import now
from django.core.exceptions import FieldError

from teacher_dashboard.models import Teacher, LectureNote, Assignment, Quiz
from admin_panel.models import (
    AppraisalCycle,
    KpiTemplate,
    KpiRule,
    TeacherAppraisalSubmission,
    AssignedPeriod,
    TeacherFixture,
    ExamResult,
    Diary,
    LessonPlanRequest,
    LessonDay,
)

from .appraisal_forms import TeacherAppraisalSubmissionForm, TeacherActivityFormSet


def _safe_date_filter(qs, field_candidates, start_date, end_date):
    for field in field_candidates:
        try:
            return qs.filter(**{f"{field}__date__gte": start_date, f"{field}__date__lte": end_date})
        except (FieldError, TypeError, ValueError):
            pass
        try:
            return qs.filter(**{f"{field}__gte": start_date, f"{field}__lte": end_date})
        except (FieldError, TypeError, ValueError):
            pass
    return qs


def _compute_manual_score(notes: str, hours: float, date_str: str) -> int:
    notes = (notes or "").strip()
    date_str = (date_str or "").strip()

    score = 0

    if notes:
        ln = len(notes)
        if ln >= 30:
            score += 3
        if ln >= 80:
            score += 2
        if ln >= 150:
            score += 2

    if hours >= 1:
        score += 1
    if hours >= 3:
        score += 1
    if hours >= 6:
        score += 1

    if date_str:
        score += 1

    return max(0, min(10, int(score)))


@login_required
def teacher_appraisal_submit(request):
    teacher = get_object_or_404(Teacher, user=request.user)

    cycle = AppraisalCycle.objects.filter(is_open=True).order_by("-start_date").first()
    if not cycle:
        messages.error(request, "No open appraisal cycle found. Please contact admin.")
        return redirect("teacher_dashboard")

    start = cycle.start_date
    end = cycle.end_date

    template = KpiTemplate.objects.filter(cycle=cycle).order_by("-id").first()

    submission, _ = TeacherAppraisalSubmission.objects.get_or_create(
        teacher=teacher,
        cycle=cycle,
        defaults={"status": "draft"},
    )

    if template and not submission.kpi_template_id:
        submission.kpi_template = template
        submission.save(update_fields=["kpi_template"])

    assignments = (
        AssignedPeriod.objects.filter(teacher=teacher)
        .select_related("class_fk", "section", "subject")
        .order_by("class_fk__class_name", "section__section_name", "subject__name")
    )

    fixtures = {
        # SAHI CODE — date field exist karta hai TeacherFixture mein
"fixtures_absent": TeacherFixture.objects.filter(
    absent_teacher=teacher,
    date__isnull=False,
    date__gte=start,
    date__lte=end
).count(),
"fixtures_substitute": TeacherFixture.objects.filter(
    substitute_teacher=teacher,
    date__isnull=False,
    date__gte=start,
    date__lte=end
).count(),
    }

    results_qs = ExamResult.objects.filter(teacher=teacher).select_related("class_fk", "section", "subject")
    results_qs = _safe_date_filter(results_qs, ["date_uploaded", "created_at", "date"], start, end)

    def grade_band(percent: float) -> str:
        if percent >= 80:
            return "A"
        if percent >= 70:
            return "B"
        if percent >= 60:
            return "C"
        if percent >= 50:
            return "D"
        if percent >= 40:
            return "E"
        return "F"

    by_bucket = {}
    overall_total = overall_pass = overall_ab = overall_a = 0

    for r in results_qs:
        pct = (float(r.marks_obtained) / float(r.total_marks) * 100.0) if r.total_marks else 0.0
        band = grade_band(pct)
        key = f"{r.class_fk.class_name}-{r.section.section_name}-{r.subject.name}"

        by_bucket.setdefault(key, {"A": 0, "B": 0, "C": 0, "D": 0, "E": 0, "F": 0, "total": 0})
        by_bucket[key][band] += 1
        by_bucket[key]["total"] += 1

        overall_total += 1
        if band != "F":
            overall_pass += 1
        if band in ("A", "B"):
            overall_ab += 1
        if band == "A":
            overall_a += 1

    def _pct(num, den):
        return round((num / den) * 100.0, 2) if den else 0.0

    exam_summary = {
        "overall": {"total": overall_total},
        "metrics": {
            "pass_rate": _pct(overall_pass, overall_total),
            "ab_rate": _pct(overall_ab, overall_total),
            "a_rate": _pct(overall_a, overall_total),
            "results_count": overall_total,
        },
        "by_bucket": by_bucket,
    }

    activities_qs = submission.appraisal_activities.all()
    extra_kpis = {
        "workshops_attended": activities_qs.filter(entry_kind="ACTIVITY", activity_type="WORKSHOP_ATTEND").count(),
        "trainings_given": activities_qs.filter(entry_kind="ACTIVITY", activity_type="TRAINING_GIVEN").count(),
        "extra_curricular": activities_qs.filter(entry_kind="ACTIVITY", activity_type="EXTRA").count(),
    }

    extra_kpis["diary_submissions"] = _safe_date_filter(
        Diary.objects.filter(teacher=teacher), ["date", "created_at"], start, end
    ).count()

    extra_kpis["lesson_plans_created"] = _safe_date_filter(
        LessonPlanRequest.objects.filter(teacher=request.user), ["created_at", "updated_at"], start, end
    ).count()

    extra_kpis["lesson_days_created"] = _safe_date_filter(
        LessonDay.objects.filter(plan__teacher=request.user), ["created_at", "updated_at"], start, end
    ).count()

    extra_kpis["lecture_notes_uploaded"] = _safe_date_filter(
        LectureNote.objects.filter(teacher=teacher), ["created_at", "uploaded_at", "date"], start, end
    ).count()

    extra_kpis["assignments_uploaded"] = _safe_date_filter(
        Assignment.objects.filter(teacher=teacher), ["created_at", "uploaded_at", "date"], start, end
    ).count()

    extra_kpis["quizzes_created"] = _safe_date_filter(
        Quiz.objects.filter(teacher=teacher), ["created_at", "uploaded_at", "date"], start, end
    ).count()

    manual_rules = []
    if template:
        manual_rules = list(template.rules.filter(is_active=True, is_manual=True).order_by("id"))

    if request.method == "POST":
        form = TeacherAppraisalSubmissionForm(request.POST, instance=submission)
        formset = TeacherActivityFormSet(request.POST, instance=submission, template=template)

        if form.is_valid() and formset.is_valid():
            with transaction.atomic():
                form.save()

                # handle deletions properly
                # for obj in formset.deleted_objects:
                #     obj.delete()
                
                
                # handle deletions properly
                if hasattr(formset, 'deleted_objects'):
                    for obj in formset.deleted_objects:
                        obj.delete()

                # save each form row with mapping
                instances = formset.save(commit=False)

                for f in formset.forms:
                    if not f.cleaned_data or f.cleaned_data.get("DELETE"):
                        continue

                    obj = f.save(commit=False)
                    selector = (f.cleaned_data.get("kpi_selector") or "").strip()

                    if selector.startswith("MKPI:"):
                        rule_id = int(selector.split(":")[1])
                        obj.entry_kind = "MANUAL_KPI"
                        obj.manual_rule_id = rule_id
                        obj.activity_type = ""
                        score = _compute_manual_score(
                            notes=obj.notes or "",
                            hours=float(obj.hours or 0),
                            date_str=str(obj.date or ""),
                        )
                        obj.system_score = score
                    else:
                        code = selector.split(":")[1] if ":" in selector else ""
                        obj.entry_kind = "ACTIVITY"
                        obj.activity_type = code
                        obj.manual_rule = None
                        obj.system_score = None

                    obj.submission = submission
                    obj.save()

                formset.save_m2m()

                # build manual_ratings dict from saved rows
                manual = submission.manual_ratings or {}

                for r in manual_rules:
                    key = (r.kpi_key or "").strip()
                    best_score = 0

                    evidences = submission.appraisal_activities.filter(
                        entry_kind="MANUAL_KPI",
                        manual_rule=r,
                    )
                    for ev in evidences:
                        # prefer stored system_score, fallback compute
                        ev_score = ev.system_score
                        if ev_score is None:
                            ev_score = _compute_manual_score(
                                notes=ev.notes or "",
                                hours=float(ev.hours or 0),
                                date_str=str(ev.date or ""),
                            )
                        best_score = max(best_score, int(ev_score or 0))

                    manual[key] = best_score

                submission.manual_ratings = manual

                if "submit_final" in request.POST:
                    submission.status = "submitted"
                    submission.submitted_at = now()
                    submission.save(update_fields=["status", "submitted_at", "manual_ratings", "updated_at"])
                    messages.success(request, "Appraisal submitted successfully.")
                else:
                    submission.status = "draft"
                    submission.save(update_fields=["status", "manual_ratings", "updated_at"])
                    messages.success(request, "Appraisal saved (draft).")

            return redirect("teacher_appraisal_submit")

        messages.error(request, "Please fix the errors below.")

    else:
        form = TeacherAppraisalSubmissionForm(instance=submission)
        formset = TeacherActivityFormSet(instance=submission, template=template)

    return render(
        request,
        "teacher_dashboard/appraisal_teacher_submit.html",
        {
            "cycle": cycle,
            "template": template,
            "teacher": teacher,
            "submission": submission,
            "assignments": assignments,
            "fixtures": fixtures,
            "exam_summary": exam_summary,
            "extra_kpis": extra_kpis,
            "manual_rules": manual_rules,
            "form": form,
            "formset": formset,
        },
    )






from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from django.http import HttpResponse, JsonResponse
from django.db import transaction
import json

# Aapke existing imports (already aapke views.py mein hain)
from teacher_dashboard.models import Teacher
from student_profile.models import Student
from admin_panel.models import (
    Class, Section, Subject, AcademicYear,
    AssignedPeriod
)

# Naye exam system ke models
from exam_system.models import (
    QuestionBank, Question,
    ExamPlan, ExamSchedule, PaperBlueprint, BlueprintRule,
    GeneratedPaper, PaperApproval, PaperAccessLog,
    ExamSeatingPlan, InvigilatorDuty,
    ExamAttendance, AnswerSheet, QuestionScore,
    CentralizedResult,
)

# AI service (alag file mein — neeche diya hai)
from exam_system.services import generate_questions_ai, generate_paper_from_blueprint, compile_results


# =============================================================
# HELPER — aapka existing pattern same rakha
# =============================================================

def get_active_year():
    return AcademicYear.objects.filter(is_active=True).first()


# =============================================================
# SECTION 1: QUESTION BANK VIEWS
# (Subject Coordinator / Teacher use karta hai)
# =============================================================

@login_required
def question_bank_list(request):
    """
    Sab question banks dikhao.
    Admin ya coordinator ke liye.
    """
    academic_year = get_active_year()
    banks = QuestionBank.objects.filter(
        academic_year=academic_year
    ).select_related('subject', 'class_fk', 'created_by')

    return render(request, 'exam_system/question_bank_list.html', {
        'banks': banks,
        'academic_year': academic_year,
    })


@login_required
def question_bank_detail(request, bank_id):
    """
    Ek bank ke sab questions.
    Filter by type/difficulty.
    """
    bank = get_object_or_404(QuestionBank, id=bank_id)

    q_type  = request.GET.get('type', '')
    diff    = request.GET.get('difficulty', '')
    approved_only = request.GET.get('approved', '')

    questions = bank.questions.all()

    if q_type:
        questions = questions.filter(question_type=q_type)
    if diff:
        questions = questions.filter(difficulty=diff)
    if approved_only == '1':
        questions = questions.filter(human_approved=True)

    return render(request, 'exam_system/question_bank_detail.html', {
        'bank': bank,
        'questions': questions,
        'q_types': Question.QUESTION_TYPES,
        'difficulties': Question.DIFFICULTY_LEVELS,
    })


@login_required
def add_question_to_bank(request, bank_id):
    """
    Teacher manually question add kare.
    Aapke existing add_question view ki tarah.
    """
    bank = get_object_or_404(QuestionBank, id=bank_id)

    if request.method == 'POST':
        Question.objects.create(
            bank=bank,
            question_type=request.POST.get('question_type'),
            text=request.POST.get('text'),
            marks=request.POST.get('marks', 1),
            difficulty=request.POST.get('difficulty', 'MEDIUM'),
            bloom_level=request.POST.get('bloom_level', 'UNDERSTAND'),
            topic_tag=request.POST.get('topic_tag', ''),
            option_a=request.POST.get('option_a') or None,
            option_b=request.POST.get('option_b') or None,
            option_c=request.POST.get('option_c') or None,
            option_d=request.POST.get('option_d') or None,
            correct_answer=request.POST.get('correct_answer', ''),
            ai_generated=False,
            human_approved=False,
        )
        messages.success(request, "Question added successfully.")
        return redirect('question_bank_detail', bank_id=bank.id)

    return render(request, 'exam_system/add_question.html', {
        'bank': bank,
        'q_types': Question.QUESTION_TYPES,
        'difficulties': Question.DIFFICULTY_LEVELS,
        'bloom_levels': Question.BLOOM_LEVELS,
    })


@login_required
def approve_question(request, question_id):
    """
    Coordinator ya Academic Head question approve kare.
    """
    question = get_object_or_404(Question, id=question_id)

    if request.method == 'POST':
        question.human_approved = True
        question.approved_by = request.user
        question.save()
        messages.success(request, f"Question approved.")
        return redirect('question_bank_detail', bank_id=question.bank.id)

    return render(request, 'exam_system/approve_question.html', {
        'question': question,
    })


@login_required
def ai_generate_questions(request, bank_id):
    """
    AI se questions generate karo.
    Celery task ya synchronous — aapki choice.
    """
    bank = get_object_or_404(QuestionBank, id=bank_id)

    if request.method == 'POST':
        topic       = request.POST.get('topic', '')
        difficulty  = request.POST.get('difficulty', 'MEDIUM')
        q_type      = request.POST.get('question_type', 'MCQ')
        count       = int(request.POST.get('count', 5))

        try:
            generated = generate_questions_ai(
                topic=topic,
                difficulty=difficulty,
                question_type=q_type,
                count=count,
                subject_name=bank.subject.name,
                class_name=bank.class_fk.class_name,
            )

            for q_data in generated:
                Question.objects.create(
                    bank=bank,
                    question_type=q_type,
                    text=q_data.get('question', ''),
                    marks=q_data.get('marks', 1),
                    difficulty=difficulty,
                    correct_answer=q_data.get('answer', ''),
                    option_a=q_data.get('option_a'),
                    option_b=q_data.get('option_b'),
                    option_c=q_data.get('option_c'),
                    option_d=q_data.get('option_d'),
                    topic_tag=topic,
                    ai_generated=True,
                    human_approved=False,   # review baad mein hogi
                )

            messages.success(request, f"{len(generated)} questions AI se generate ho gaye. Review karo.")
        except Exception as e:
            messages.error(request, f"AI generation failed: {str(e)}")

        return redirect('question_bank_detail', bank_id=bank.id)

    return render(request, 'exam_system/ai_generate_questions.html', {
        'bank': bank,
        'difficulties': Question.DIFFICULTY_LEVELS,
        'q_types': Question.QUESTION_TYPES,
    })


# =============================================================
# SECTION 2: EXAM PLAN + BLUEPRINT VIEWS
# (Examination Controller / Head Office)
# =============================================================

@login_required
def exam_plan_list(request):
    """
    Sab exam plans — filter by year/type.
    """
    academic_year = get_active_year()
    plans = ExamPlan.objects.filter(
        academic_year=academic_year
    ).prefetch_related('schedules').order_by('-created_at')

    return render(request, 'exam_system/exam_plan_list.html', {
        'plans': plans,
        'exam_types': ExamPlan.EXAM_TYPES,
    })


@login_required
def create_exam_plan(request):
    """
    Naya exam plan banao.
    Head Office ya Examination Controller.
    """
    academic_year = get_active_year()

    if request.method == 'POST':
        plan = ExamPlan.objects.create(
            title=request.POST.get('title'),
            academic_year=academic_year,
            exam_type=request.POST.get('exam_type'),
            class_fk_id=request.POST.get('class_id'),
            start_date=request.POST.get('start_date'),
            end_date=request.POST.get('end_date'),
            created_by=request.user,
        )
        messages.success(request, f"Exam plan '{plan.title}' create ho gaya.")
        return redirect('exam_plan_detail', plan_id=plan.id)

    classes = Class.objects.all()
    return render(request, 'exam_system/create_exam_plan.html', {
        'classes': classes,
        'exam_types': ExamPlan.EXAM_TYPES,
        'academic_year': academic_year,
    })


@login_required
def exam_plan_detail(request, plan_id):
    """
    Ek plan ka detail — schedules + blueprints.
    """
    plan = get_object_or_404(ExamPlan, id=plan_id)
    schedules = plan.schedules.select_related('subject').all()
    blueprints = plan.blueprints.select_related('subject').prefetch_related('rules').all()

    return render(request, 'exam_system/exam_plan_detail.html', {
        'plan': plan,
        'schedules': schedules,
        'blueprints': blueprints,
    })


@login_required
def add_exam_schedule(request, plan_id):
    """
    Exam plan mein subject ka date/time add karo.
    """
    plan = get_object_or_404(ExamPlan, id=plan_id)

    if request.method == 'POST':
        ExamSchedule.objects.create(
            exam_plan=plan,
            subject_id=request.POST.get('subject_id'),
            exam_date=request.POST.get('exam_date'),
            start_time=request.POST.get('start_time'),
            end_time=request.POST.get('end_time'),
            room=request.POST.get('room', ''),
        )
        messages.success(request, "Schedule add ho gaya.")
        return redirect('exam_plan_detail', plan_id=plan.id)

    # Class ke subjects
    subjects = Subject.objects.filter(
        assignedperiod__class_fk=plan.class_fk
    ).distinct()

    return render(request, 'exam_system/add_schedule.html', {
        'plan': plan,
        'subjects': subjects,
    })


@login_required
def create_blueprint(request, plan_id, subject_id):
    """
    Blueprint banao — marks distribution define karo.
    """
    plan    = get_object_or_404(ExamPlan, id=plan_id)
    subject = get_object_or_404(Subject, id=subject_id)

    blueprint, created = PaperBlueprint.objects.get_or_create(
        exam_plan=plan,
        subject=subject,
        defaults={'created_by': request.user}
    )

    if request.method == 'POST':
        # Total marks update
        blueprint.total_marks   = request.POST.get('total_marks', 100)
        blueprint.passing_marks = request.POST.get('passing_marks', 40)
        blueprint.save()

        # Rules save karo
        blueprint.rules.all().delete()
        q_types = request.POST.getlist('question_type')
        counts  = request.POST.getlist('count')
        marks   = request.POST.getlist('marks_each')
        easy    = request.POST.getlist('easy_percent')
        medium  = request.POST.getlist('medium_percent')
        hard    = request.POST.getlist('hard_percent')

        for i in range(len(q_types)):
            BlueprintRule.objects.create(
                blueprint=blueprint,
                question_type=q_types[i],
                count=int(counts[i]),
                marks_each=int(marks[i]),
                easy_percent=int(easy[i]),
                medium_percent=int(medium[i]),
                hard_percent=int(hard[i]),
            )

        messages.success(request, "Blueprint saved successfully.")
        return redirect('exam_plan_detail', plan_id=plan.id)

    return render(request, 'exam_system/create_blueprint.html', {
        'plan': plan,
        'subject': subject,
        'blueprint': blueprint,
        'q_types': Question.QUESTION_TYPES,
    })


# =============================================================
# SECTION 3: PAPER GENERATION + APPROVAL VIEWS
# =============================================================

@login_required
def generate_paper_view(request, blueprint_id):
    """
    AI ya manual paper generate karo blueprint se.
    Aapke generate_lesson_plan_for_topic ki tarah.
    """
    blueprint = get_object_or_404(PaperBlueprint, id=blueprint_id)

    if request.method == 'POST':
        paper_set = request.POST.get('paper_set', 'SINGLE')
        section_id = request.POST.get('section_id')

        try:
            with transaction.atomic():
                paper = GeneratedPaper.objects.create(
                    blueprint=blueprint,
                    section_id=section_id if section_id else None,
                    paper_set=paper_set,
                    generated_by=request.user,
                    status='DRAFT',
                )

                # Blueprint ke rules se questions select karo
                selected_questions = generate_paper_from_blueprint(blueprint)
                paper.questions.set(selected_questions)

                # Initial approval workflow create karo
                stages = ['TEACHER', 'COORDINATOR', 'ACADEMIC_HEAD', 'CONTROLLER']
                for stage in stages:
                    PaperApproval.objects.create(
                        paper=paper,
                        stage=stage,
                        status='PENDING',
                    )

                messages.success(request, f"Paper Set {paper_set} generate ho gaya. Review ke liye bheja.")
                return redirect('paper_approval_detail', paper_id=paper.id)

        except Exception as e:
            messages.error(request, f"Paper generation failed: {str(e)}")
            return redirect('exam_plan_detail', plan_id=blueprint.exam_plan.id)

    sections = Section.objects.filter(class_fk=blueprint.exam_plan.class_fk)

    return render(request, 'exam_system/generate_paper.html', {
        'blueprint': blueprint,
        'sections': sections,
        'set_choices': GeneratedPaper.SET_CHOICES,
    })


@login_required
def paper_approval_detail(request, paper_id):
    """
    4-level approval workflow.
    Aapke teacher_appraisal_submit ki tarah — stage-wise.
    """
    paper = get_object_or_404(GeneratedPaper, id=paper_id)
    approvals = paper.approvals.all().order_by('stage')
    questions = paper.questions.all().order_by('question_type')

    if request.method == 'POST':
        stage  = request.POST.get('stage')
        action = request.POST.get('action')   # 'approve' or 'reject'
        remarks = request.POST.get('remarks', '')

        approval = get_object_or_404(PaperApproval, paper=paper, stage=stage)
        approval.status      = 'APPROVED' if action == 'approve' else 'REJECTED'
        approval.reviewed_by = request.user
        approval.remarks     = remarks
        approval.save()

        # Agar sab approved to paper LOCKED karo
        if action == 'approve':
            all_approved = paper.approvals.filter(status='APPROVED').count() == 4
            if all_approved:
                paper.status = 'LOCKED'
                paper.save()
                messages.success(request, "Paper fully approved aur locked ho gaya!")
            else:
                paper.status = 'REVIEW'
                paper.save()
                messages.success(request, f"Stage '{stage}' approved. Next reviewer ka wait karo.")
        else:
            paper.status = 'REJECTED'
            paper.save()
            messages.error(request, f"Paper '{stage}' stage pe reject ho gaya.")

        return redirect('paper_approval_detail', paper_id=paper.id)

    return render(request, 'exam_system/paper_approval_detail.html', {
        'paper': paper,
        'approvals': approvals,
        'questions': questions,
    })


@login_required
def download_paper(request, paper_id):
    """
    Secure paper download — sirf unlock time ke baad.
    Aapke PaperAccessLog mein log hoga.
    """
    paper = get_object_or_404(GeneratedPaper, id=paper_id)

    # Access log
    PaperAccessLog.objects.create(
        paper=paper,
        accessed_by=request.user,
        action='DOWNLOAD',
        ip_address=request.META.get('REMOTE_ADDR'),
    )

    # Time lock check
    if not paper.is_unlocked():
        messages.error(
            request,
            f"Paper abhi locked hai. Unlock time: {paper.unlock_time:%d %b %Y %I:%M %p}"
        )
        return redirect('paper_approval_detail', paper_id=paper.id)

    # Status check
    if paper.status != 'LOCKED':
        messages.error(request, "Paper approved nahi hai. Download allowed nahi.")
        return redirect('paper_approval_detail', paper_id=paper.id)

    if paper.pdf_file:
        response = HttpResponse(paper.pdf_file, content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="paper_{paper.id}_{paper.paper_set}.pdf"'
        return response

    messages.error(request, "PDF file available nahi hai.")
    return redirect('paper_approval_detail', paper_id=paper.id)


# =============================================================
# SECTION 4: EXAM CONDUCT VIEWS
# (Campus Admin / Invigilator)
# =============================================================

@login_required
def exam_conduct_dashboard(request, schedule_id):
    """
    Ek exam schedule ka conduct dashboard.
    Invigilator ke liye — seating + attendance.
    """
    schedule = get_object_or_404(ExamSchedule, id=schedule_id)

    seating = ExamSeatingPlan.objects.filter(
        schedule=schedule
    ).select_related('student')

    attendance = ExamAttendance.objects.filter(
        schedule=schedule
    ).select_related('student')

    attended_ids = set(attendance.filter(status='PRESENT').values_list('student_id', flat=True))

    return render(request, 'exam_system/exam_conduct_dashboard.html', {
        'schedule': schedule,
        'seating': seating,
        'attendance': attendance,
        'attended_ids': attended_ids,
    })


@login_required
def mark_exam_attendance(request, schedule_id):
    """
    Exam attendance mark karo.
    Aapke existing mark_attendance view ki tarah.
    """
    schedule = get_object_or_404(ExamSchedule, id=schedule_id)

    # Invigilator check
    teacher = get_object_or_404(Teacher, user=request.user)
    is_invigilator = InvigilatorDuty.objects.filter(
        schedule=schedule, teacher=teacher
    ).exists()

    if not is_invigilator and not request.user.is_staff:
        return HttpResponse("❌ Aap is exam ke invigilator nahi hain.")

    students = Student.objects.filter(
        class_fk=schedule.exam_plan.class_fk
    ).order_by('roll_no')

    if request.method == 'POST':
        for student in students:
            status = request.POST.get(f'status_{student.id}', 'ABSENT')
            ExamAttendance.objects.update_or_create(
                schedule=schedule,
                student=student,
                defaults={
                    'status': status,
                    'marked_by': teacher,
                }
            )
        messages.success(request, "Exam attendance mark ho gayi.")
        return redirect('exam_conduct_dashboard', schedule_id=schedule.id)

    # Existing attendance (agar pehle se mark ki ho)
    existing = {
        ea.student_id: ea.status
        for ea in ExamAttendance.objects.filter(schedule=schedule)
    }

    return render(request, 'exam_system/mark_exam_attendance.html', {
        'schedule': schedule,
        'students': students,
        'existing': existing,
    })


@login_required
def auto_generate_seating(request, schedule_id):
    """
    Auto seating plan generate karo.
    Students ko roll_no se sort karke seat assign karo.
    """
    schedule = get_object_or_404(ExamSchedule, id=schedule_id)

    if not request.user.is_staff:
        messages.error(request, "Sirf admin seating generate kar sakta hai.")
        return redirect('exam_conduct_dashboard', schedule_id=schedule.id)

    students = Student.objects.filter(
        class_fk=schedule.exam_plan.class_fk
    ).order_by('roll_no')

    ExamSeatingPlan.objects.filter(schedule=schedule).delete()

    for i, student in enumerate(students, start=1):
        ExamSeatingPlan.objects.create(
            schedule=schedule,
            student=student,
            seat_number=f"S{i:03d}",
            room=schedule.room,
        )

    messages.success(request, f"{students.count()} students ki seating plan ban gayi.")
    return redirect('exam_conduct_dashboard', schedule_id=schedule.id)


# =============================================================
# SECTION 5: MARKING VIEWS
# (Teacher / AI)
# =============================================================

@login_required
def answer_sheet_list(request, schedule_id):
    """
    Ek schedule ke sab answer sheets.
    Teacher in pe marks dega.
    """
    schedule = get_object_or_404(ExamSchedule, id=schedule_id)
    sheets = AnswerSheet.objects.filter(
        schedule=schedule
    ).select_related('student').prefetch_related('scores')

    return render(request, 'exam_system/answer_sheet_list.html', {
        'schedule': schedule,
        'sheets': sheets,
    })


@login_required
def mark_answer_sheet(request, sheet_id):
    """
    Teacher ek student ka answer sheet mark kare.
    AI score pehle se aata hai — teacher verify/override kare.
    Aapke upload_result view ki tarah.
    """
    sheet = get_object_or_404(AnswerSheet, id=sheet_id)
    questions = sheet.paper.questions.all() if sheet.paper else []

    # Existing scores
    scores_dict = {
        s.question_id: s
        for s in QuestionScore.objects.filter(answer_sheet=sheet)
    }

    if request.method == 'POST':
        with transaction.atomic():
            for question in questions:
                teacher_score = request.POST.get(f'score_{question.id}')
                remarks       = request.POST.get(f'remarks_{question.id}', '')

                if teacher_score is not None and teacher_score != '':
                    score_obj, _ = QuestionScore.objects.get_or_create(
                        answer_sheet=sheet,
                        question=question,
                    )
                    score_obj.teacher_score   = teacher_score
                    score_obj.teacher_remarks = remarks
                    score_obj.verified_by     = request.user
                    score_obj.save()

        messages.success(request, f"{sheet.student.name} ka result save ho gaya.")
        return redirect('answer_sheet_list', schedule_id=sheet.schedule.id)

    return render(request, 'exam_system/mark_answer_sheet.html', {
        'sheet': sheet,
        'questions': questions,
        'scores_dict': scores_dict,
    })


# =============================================================
# SECTION 6: RESULT COMPILATION + ANALYTICS
# =============================================================

@login_required
def compile_exam_results(request, schedule_id):
    """
    Sab answer sheets ke scores aggregate karo.
    CentralizedResult model mein save karo.
    Admin / Exam Controller ke liye.
    """
    schedule = get_object_or_404(ExamSchedule, id=schedule_id)

    if not request.user.is_staff:
        messages.error(request, "Sirf admin results compile kar sakta hai.")
        return redirect('answer_sheet_list', schedule_id=schedule.id)

    if request.method == 'POST':
        try:
            compiled_count = compile_results(schedule)
            messages.success(request, f"{compiled_count} students ke results compile ho gaye.")
        except Exception as e:
            messages.error(request, f"Result compilation failed: {str(e)}")

        return redirect('exam_results_list', schedule_id=schedule.id)

    return render(request, 'exam_system/compile_results_confirm.html', {
        'schedule': schedule,
    })


@login_required
def exam_results_list(request, schedule_id):
    """
    Compiled results dikhao with ranking.
    Aapke merge_result view ki tarah.
    """
    schedule = get_object_or_404(ExamSchedule, id=schedule_id)
    results = CentralizedResult.objects.filter(
        answer_sheet__schedule=schedule
    ).select_related(
        'answer_sheet__student'
    ).order_by('class_position')

    pass_count = results.filter(is_pass=True).count()
    fail_count = results.filter(is_pass=False).count()
    total = results.count()

    return render(request, 'exam_system/exam_results_list.html', {
        'schedule': schedule,
        'results': results,
        'pass_count': pass_count,
        'fail_count': fail_count,
        'total': total,
        'pass_rate': round((pass_count / total * 100), 1) if total else 0,
    })


@login_required
def analytics_dashboard(request):
    """
    Head Office analytics — campus-wise comparison.
    Aapke appraisal dashboard ki tarah — aggregated data.
    """
    academic_year = get_active_year()

    plans = ExamPlan.objects.filter(
        academic_year=academic_year,
        is_published=True,
    ).prefetch_related('schedules__exam_attendance')

    # Subject-wise pass rates
    from django.db.models import Count, Avg

    subject_stats = CentralizedResult.objects.filter(
        answer_sheet__schedule__exam_plan__academic_year=academic_year
    ).values(
        'answer_sheet__schedule__subject__name'
    ).annotate(
        avg_pct=Avg('percentage'),
        total=Count('id'),
    ).order_by('-avg_pct')

    # Grade distribution
    grade_dist = CentralizedResult.objects.filter(
        answer_sheet__schedule__exam_plan__academic_year=academic_year
    ).values('grade').annotate(count=Count('id')).order_by('grade')

    return render(request, 'exam_system/analytics_dashboard.html', {
        'academic_year': academic_year,
        'plans': plans,
        'subject_stats': subject_stats,
        'grade_dist': grade_dist,
    })



# ============================================================
# TEACHER TIMETABLE VIEW — student_timetable jaisi style
# teacher_dashboard/views.py ke END mein ADD karo
# ============================================================

from admin_panel.models import CreatePeriod

@login_required
def teacher_timetable_view(request):
    teacher = get_selected_teacher(request)

    if not teacher:
        if request.user.is_staff:
            return redirect('select_teacher_for_action')
        messages.error(request, "Teacher profile nahi mila.")
        return redirect('teacher_dashboard')

    # Period order — Monday ko base banao (student_timetable jaisa)
    all_periods  = CreatePeriod.objects.all().order_by('day', 'start_time')
    monday       = all_periods.filter(day='Monday')
    period_order = [p.period_name for p in monday]

    for p in all_periods:
        if p.period_name not in period_order:
            period_order.append(p.period_name)

    days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday']

    slots = {}
    for day in days:
        assigned = AssignedPeriod.objects.filter(
            teacher=teacher,
            day=day
        ).select_related('period', 'subject', 'class_fk', 'section')

        assigned_map = {ap.period.period_name: ap for ap in assigned}
        day_slots = {}

        for pname in period_order:
            ap = assigned_map.get(pname)
            if ap:
                day_slots[pname] = (
                    f"{ap.subject.name}<br>"
                    f"<small>{ap.class_fk.class_name} - {ap.section.section_name}</small><br>"
                    f"<small>{ap.period.start_time.strftime('%I:%M %p')} - "
                    f"{ap.period.end_time.strftime('%I:%M %p')}</small>"
                )
            else:
                day_slots[pname] = "---"

        slots[day] = day_slots

    return render(request, 'teacher_dashboard/timetable.html', {
        'teacher':      teacher,
        'period_order': period_order,
        'slots':        slots,
        'days':         days,
    })









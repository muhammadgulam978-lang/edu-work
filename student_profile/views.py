# student_profile/views.py

from django.contrib.auth.models    import User, Group
from django.contrib.auth.password_validation import validate_password
from django.contrib                 import messages
from django.shortcuts               import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.utils                   import timezone
from django.db import transaction
import uuid

from .models                        import Student, AssignmentSubmission
from admin_panel.models             import Subject, ExamResult, Diary
from teacher_dashboard.models       import Assignment, Attendance, Quiz, LectureNote
from student_profile.models         import QuizSubmission
from student_profile.email_utils    import (
    send_student_credentials_email,
    send_password_reset_email,
)
from datetime import date as date_today_cls


from django.db.models import Count, Q
from teacher_dashboard.models import Attendance


# =============================================================
# STUDENT DASHBOARD
# =============================================================
@login_required
def student_dashboard(request):
    print("=== student_dashboard view reached ===")
    user = request.user
    print("Logged in user:", user.username)

    try:
        student = Student.objects.get(user=user)
    except Student.DoesNotExist:
        return render(request, 'student_profile/error.html', {
            'message': 'Student profile not found.'
        })

    if not student.class_fk:
        return render(request, 'student_profile/error.html', {
            'message': 'Student is not assigned to any class.'
        })

    subjects = Subject.objects.filter(class_fk=student.class_fk)

    return render(request, 'student_profile/dashboard.html', {
        'student':    student,
        'class_name': student.class_fk.class_name,
        'subjects':   subjects,
    })


# =============================================================
# CREATE STUDENT + SEND EMAIL
# =============================================================
@login_required
def create_student(request):
    if not request.user.is_staff:
        messages.error(request, "❌ Sirf admin student account bana sakta hai.")
        return redirect('student_dashboard')

    if request.method == 'POST':
        name        = request.POST.get('name', '').strip()
        email       = request.POST.get('email', '').strip()
        class_id    = request.POST.get('class_id')
        roll_no     = request.POST.get('roll_no', '').strip()
        father_name = request.POST.get('father_name', '').strip()
        phone       = request.POST.get('phone', '').strip()
        address     = request.POST.get('address', '').strip()

        if not name or not email:
            messages.error(request, "❌ Name aur Email zaroori hain.")
            return redirect('create_student')

        if User.objects.filter(email=email).exists():
            messages.error(request, f"❌ Ye email '{email}' pehle se registered hai.")
            return redirect('create_student')

        base_username = name.split()[0].lower() + (roll_no or str(uuid.uuid4().hex[:4]))
        username = base_username
        counter  = 1
        while User.objects.filter(username=username).exists():
            username = f"{base_username}{counter}"
            counter += 1

        raw_password = User.objects.make_random_password(length=10)

        try:
            user = User.objects.create_user(
                username=username,
                email=email,
                password=raw_password,
                first_name=name,
            )

            student_data = {
                'user':        user,
                'name':        name,
                'email':       email,
                'class_fk_id': class_id if class_id else None,
            }
            if roll_no:
                student_data['roll_no'] = roll_no
            if father_name and hasattr(Student, 'father_name'):
                student_data['father_name'] = father_name
            if phone and hasattr(Student, 'phone'):
                student_data['phone'] = phone
            if address and hasattr(Student, 'address'):
                student_data['address'] = address

            student = Student.objects.create(**student_data)

            email_ok, email_msg = send_student_credentials_email(student, raw_password)

            if email_ok:
                messages.success(
                    request,
                    f"✅ Student '{name}' ka account ban gaya! "
                    f"Login credentials {email} par send ho gaye."
                )
            else:
                messages.warning(
                    request,
                    f"✅ Student account ban gaya lekin email send nahi hui: {email_msg}\n"
                    f"Manually dein — Username: {username} | Password: {raw_password}"
                )

        except Exception as e:
            messages.error(request, f"❌ Student account nahi bana: {str(e)}")
            return redirect('create_student')

        return redirect('student_list')

    from admin_panel.models import Class
    classes = Class.objects.all().order_by('class_name')
    return render(request, 'student_profile/create_student.html', {'classes': classes})


@login_required
def create_student(request):
    if not request.user.is_staff:
        messages.error(request, "Only admin can create student accounts.")
        return redirect('student_dashboard')

    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        email = request.POST.get('email', '').strip()
        login_id = request.POST.get('login_id', '').strip()
        password = request.POST.get('password', '')
        confirm_password = request.POST.get('confirm_password', '')
        student_id = request.POST.get('student_id', '').strip()
        class_id = request.POST.get('class_id')
        section_id = request.POST.get('section_id') or None
        roll_no = request.POST.get('roll_no', '').strip()
        father_name = request.POST.get('father_name', '').strip()
        mother_name = request.POST.get('mother_name', '').strip()
        gender = request.POST.get('gender', 'Male')
        date_of_birth = request.POST.get('date_of_birth')
        phone = request.POST.get('phone', '').strip()

        required_values = [
            name, email, login_id, password, confirm_password, student_id,
            roll_no, father_name, mother_name, date_of_birth,
        ]
        if not all(required_values):
            messages.error(request, "Name, email, login ID, password, student ID, roll no, family details, and date of birth are required.")
            return redirect('create_student')

        if User.objects.filter(email=email).exists():
            messages.error(request, f"This email '{email}' is already registered.")
            return redirect('create_student')
        if User.objects.filter(username__iexact=login_id).exists():
            messages.error(request, f"This login ID '{login_id}' already exists.")
            return redirect('create_student')
        if Student.objects.filter(student_id=student_id).exists():
            messages.error(request, f"This student ID '{student_id}' already exists.")
            return redirect('create_student')
        if password != confirm_password:
            messages.error(request, "Password and confirm password do not match.")
            return redirect('create_student')

        try:
            validate_password(password)
        except Exception as password_error:
            messages.error(request, " ".join(password_error.messages))
            return redirect('create_student')

        try:
            with transaction.atomic():
                user = User.objects.create_user(
                    username=login_id,
                    email=email,
                    password=password,
                    first_name=name,
                )
                student_group, _ = Group.objects.get_or_create(name="Student")
                user.groups.set([student_group])

                student = Student.objects.create(
                    user=user,
                    student_id=student_id,
                    name=name,
                    father_name=father_name,
                    mother_name=mother_name,
                    class_fk_id=class_id if class_id else None,
                    section_id=section_id,
                    roll_no=roll_no,
                    phone=phone or None,
                    gender=gender,
                    date_of_birth=date_of_birth,
                    email=email,
                )

            email_ok, email_msg = send_student_credentials_email(student, password)
            if email_ok:
                messages.success(request, f"Student '{name}' account created. Login credentials were sent to {email}.")
            else:
                messages.warning(request, f"Student account created but email was not sent: {email_msg}. Login ID: {login_id}")
        except Exception as e:
            messages.error(request, f"Student account was not created: {str(e)}")
            return redirect('create_student')

        return redirect('admission_list')

    from admin_panel.models import Class, Section
    classes = Class.objects.all().order_by('class_name')
    sections = Section.objects.select_related("class_fk").all().order_by("class_fk__class_name", "section_name")
    return render(request, 'student_profile/create_student.html', {
        'classes': classes,
        'sections': sections,
    })


# =============================================================
# RESEND CREDENTIALS EMAIL
# =============================================================
@login_required
def resend_credentials(request, student_id):
    if not request.user.is_staff:
        messages.error(request, "❌ Permission denied.")
        return redirect('student_dashboard')

    student = get_object_or_404(Student, id=student_id)

    if not student.email:
        messages.error(request, f"❌ {student.name} ka email address nahi hai.")
        return redirect('student_list')

    new_password = User.objects.make_random_password(length=10)
    student.user.set_password(new_password)
    student.user.save()

    ok, msg = send_password_reset_email(student, new_password)

    if ok:
        messages.success(request, f"✅ {student.name} ko naya password email kar diya: {student.email}")
    else:
        messages.warning(
            request,
            f"⚠️ Password reset hua lekin email nahi gayi: {msg}\n"
            f"Manually dein — Username: {student.user.username} | Password: {new_password}"
        )

    return redirect('student_list')


# =============================================================
# STUDENT ATTENDANCE
# =============================================================
# @login_required
# def student_attendance(request):
#     student    = get_object_or_404(Student, user=request.user)
#     attendance = Attendance.objects.filter(student=student)
#     return render(request, 'student_profile/attendance.html', {'attendance': attendance})


@login_required
def student_attendance(request):
    student = get_object_or_404(Student, user=request.user)

    attendance_records = (
        Attendance.objects
        .filter(student=student)
        .select_related("period__subject", "period__teacher")
    )

    attendance = []

    subjects = Subject.objects.filter(class_fk=student.class_fk)

    for subject in subjects:

        subject_records = attendance_records.filter(period__subject=subject)

        present = subject_records.filter(status="present").count()
        absent = subject_records.filter(status="absent").count()
        leave = subject_records.filter(status="leave").count()

        total = present + absent + leave

        percentage = round((present / total) * 100, 2) if total else 0

        teacher_name = "-"

        first_record = subject_records.first()

        if first_record and first_record.period and first_record.period.teacher:
            teacher_name = first_record.period.teacher.name

        attendance.append({
            "title": subject.name,
            "class": student.class_fk.class_name,
            "teacher": teacher_name,
            "present": present,
            "absent": absent,
            "total": total,
            "percentage": percentage,
        })

    return render(
        request,
        "student_profile/attendance.html",
        {
            "attendance": attendance
        }
    )


# =============================================================
# STUDENT RESULT  (single clean version)
# =============================================================
@login_required
def student_result(request):
    user = request.user

    try:
        student = Student.objects.get(user=user)
    except Student.DoesNotExist:
        return render(request, "student_profile/error.html", {
            "message": "Student profile not found."
        })

    subjects = Subject.objects.filter(class_fk=student.class_fk)
    term     = request.GET.get("term", "midterm")

    results  = ExamResult.objects.filter(
        student=student,
        term=term
    ).select_related("subject")

    result_dict   = {res.subject_id: res for res in results}
    comments_dict = {res.subject_id: res.teacher_remarks for res in results}

    return render(request, "student_profile/result.html", {
        "student":       student,
        "subjects":      subjects,
        "result_dict":   result_dict,
        "comments_dict": comments_dict,
        "term":          term,
    })


# =============================================================
# STUDENT ASSIGNMENTS
# =============================================================
@login_required
def student_assignments(request):
    student     = Student.objects.get(user=request.user)
    assignments = Assignment.objects.filter(
        class_fk=student.class_fk,
        section=student.section
    ).order_by('due_date')

    submissions     = AssignmentSubmission.objects.filter(student=student)
    submission_dict = {s.assignment_id: s for s in submissions}

    return render(request, "student_profile/assignments.html", {
        "assignments":     assignments,
        "submission_dict": submission_dict,
        "today":           timezone.now().date(),
    })


# =============================================================
# SUBMIT ASSIGNMENT
# =============================================================
@login_required
def submit_assignment(request, assignment_id):
    student    = Student.objects.get(user=request.user)
    assignment = Assignment.objects.get(id=assignment_id)

    existing = AssignmentSubmission.objects.filter(
        assignment=assignment,
        student=student
    ).first()

    is_deadline_exceeded = assignment.due_date < timezone.now().date()

    if request.method == "POST" and not is_deadline_exceeded:
        file = request.FILES.get("file")
        AssignmentSubmission.objects.update_or_create(
            assignment=assignment,
            student=student,
            defaults={"file": file}
        )
        return redirect("student_assignments")

    return render(request, "student_profile/submit_assignment.html", {
        "assignment":           assignment,
        "existing":             existing,
        "is_deadline_exceeded": is_deadline_exceeded,
    })


# =============================================================
# STUDENT QUIZZES
# =============================================================
@login_required
def student_quizzes(request):
    student = Student.objects.get(user=request.user)
    quizzes = Quiz.objects.filter(
        class_fk=student.class_fk,
        section=student.section
    ).order_by('due_date')

    submissions     = QuizSubmission.objects.filter(student=student)
    submission_dict = {s.quiz_id: s for s in submissions}

    return render(request, "student_profile/quizzes.html", {
        "quizzes":         quizzes,
        "submission_dict": submission_dict,
        "today":           timezone.now().date(),
    })


# =============================================================
# SUBMIT QUIZ
# =============================================================
@login_required
def submit_quiz(request, quiz_id):
    student  = get_object_or_404(Student, user=request.user)
    quiz     = get_object_or_404(Quiz, id=quiz_id)
    existing = QuizSubmission.objects.filter(quiz=quiz, student=student).first()

    if request.method == 'POST':
        file = request.FILES.get('file')
        if not file:
            messages.error(request, "Please select a file to submit.")
            return redirect('submit_quiz', quiz_id=quiz_id)

        if existing:
            messages.warning(request, "You have already submitted this quiz.")
            return redirect('student_quizzes')

        QuizSubmission.objects.create(quiz=quiz, student=student, submitted_file=file)
        messages.success(request, f"✅ Quiz '{quiz.title}' submitted successfully.")
        return redirect('student_quizzes')

    return render(request, 'student_profile/submit_quiz.html', {
        'quiz':     quiz,
        'existing': existing,
    })


# =============================================================
# STUDENT DIARY
# =============================================================
@login_required
def student_diary(request):
    student = get_object_or_404(Student, user=request.user)
    diaries = Diary.objects.filter(
        class_fk=student.class_fk,
        section=student.section,
    ).select_related('teacher', 'subject').order_by('-date')

    return render(request, 'student_profile/diary.html', {'diaries': diaries})


# =============================================================
# STUDENT LECTURE NOTES
# =============================================================
@login_required
def student_lecture_notes(request):
    student      = get_object_or_404(Student, user=request.user)
    lecture_notes = LectureNote.objects.filter(
        class_fk=student.class_fk,
        section=student.section,
    ).select_related('teacher', 'subject').order_by('-id')

    return render(request, 'student_profile/lecture_notes.html', {
        'lecture_notes': lecture_notes,
    })


# =============================================================
# STUDENT TIMETABLE
# =============================================================
from admin_panel.models import AssignedPeriod, CreatePeriod

@login_required
def student_timetable(request):
    student     = Student.objects.get(user=request.user)
    class_obj   = student.class_fk
    section_obj = student.section

    all_periods  = CreatePeriod.objects.all().order_by('day', 'start_time')
    monday       = all_periods.filter(day='Monday')
    period_order = [p.period_name for p in monday]

    for p in all_periods:
        if p.period_name not in period_order:
            period_order.append(p.period_name)

    days  = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday']
    slots = {}

    for day in days:
        assigned_periods = AssignedPeriod.objects.filter(
            class_fk=class_obj,
            section=section_obj,
            day=day
        ).select_related('period', 'subject', 'teacher')

        assigned_map = {ap.period.period_name: ap for ap in assigned_periods}
        day_slots    = {}

        for pname in period_order:
            ap = assigned_map.get(pname)
            if ap:
                day_slots[pname] = (
                    f"{ap.subject.name}<br>"
                    f"<small>{ap.teacher.name}</small><br>"
                    f"<small>{ap.period.start_time.strftime('%I:%M %p')} - "
                    f"{ap.period.end_time.strftime('%I:%M %p')}</small>"
                )
            else:
                day_slots[pname] = "---"

        slots[day] = day_slots

    return render(request, "student_profile/student_timetable.html", {
        "period_order": period_order,
        "slots":        slots,
        "days":         days,
        "class_info":   class_obj,
        "section_info": section_obj,
    })

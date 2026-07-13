# from django.shortcuts import render
# from django.contrib.auth.decorators import login_required
# from parent_dashboard.models import Parent


# # ===================================================
# # 🔹 Parent Dashboard Home
# # ===================================================
# def parent_dashboard_home(request):
#     return render(request, 'parent_dashboard/dashboard.html')


# # ===================================================
# # 🔹 Parent Dashboard (logged-in parent ka view)
# # ===================================================
# @login_required
# def parent_dashboard(request):
#     try:
#         parent = Parent.objects.get(user=request.user)
#     except Parent.DoesNotExist:
#         parent = None

#     students = parent.students.all() if parent else []

#     return render(request, 'parent_dashboard/dashboard.html', {
#         'parent':   parent,
#         'students': students,
#     })


# # ===================================================
# # 🔹 Parent List (admin ke liye — sab parents)
# # ===================================================
# @login_required
# def parent_list(request):
#     parents = Parent.objects.prefetch_related('students').all()
#     return render(request, 'parent_dashboard/parent_list.html', {
#         'parents': parents,
#     })






from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required

from parent_dashboard.models import Parent

from admin_panel.models import (
    Subject,
    ExamResult,
    Diary,
    AssignedPeriod,
    CreatePeriod,
)

from teacher_dashboard.models import (
    Attendance,
    Assignment,
    Quiz,
    
)


@login_required
def parent_dashboard_home(request):
    return redirect("parent_dashboard")


@login_required
def parent_list(request):
    parents = Parent.objects.prefetch_related("students").all()

    return render(
        request,
        "parent_dashboard/parent_list.html",
        {
            "parents": parents,
        },
    )


@login_required
def parent_dashboard(request):

    parent = get_object_or_404(
        Parent,
        user=request.user,
    )

    students = parent.students.all()

    selected_student = None

    student_id = request.GET.get("student")

    if student_id:
        selected_student = students.filter(id=student_id).first()

    if selected_student is None:
        selected_student = students.first()

    if selected_student is None:
        return render(
            request,
            "parent_dashboard/dashboard.html",
            {
                "parent": parent,
                "students": [],
                "selected_student": None,
                "subjects": [],
            },
        )

    subjects = Subject.objects.filter(
        class_fk=selected_student.class_fk
    )

    return render(
        request,
        "parent_dashboard/dashboard.html",
        {
            "parent": parent,
            "students": students,
            "selected_student": selected_student,
            "subjects": subjects,
        },
    )
    
    
@login_required
def parent_attendance(request):

    parent = get_object_or_404(Parent, user=request.user)

    students = parent.students.all()

    student_id = request.GET.get("student")

    if student_id:
        selected_student = get_object_or_404(
            students,
            id=student_id
        )
    else:
        selected_student = students.first()

    if not selected_student:
        return render(request,
                      "parent_dashboard/attendance.html",
                      {
                          "students": students,
                          "selected_student": None,
                          "attendance": []
                      })

    attendance_records = Attendance.objects.filter(
        student=selected_student
    ).select_related(
        "marked_by",
        "period",
        "period__subject"
    )

    attendance = []

    subjects = Subject.objects.filter(
        class_fk=selected_student.class_fk
    )

    for subject in subjects:

        records = attendance_records.filter(
            period__subject=subject
        )

        present = records.filter(status="present").count()
        absent = records.filter(status="absent").count()
        leave = records.filter(status="leave").count()

        total = present + absent + leave

        percentage = 0

        if total:
            percentage = round((present / total) * 100, 2)

        teacher = "-"

        if records.exists() and records.first().marked_by:
            teacher = records.first().marked_by.name

        attendance.append({
            "title": subject.name,
            "class": selected_student.class_fk.class_name,
            "teacher": teacher,
            "present": present,
            "absent": absent,
            "total": total,
            "percentage": percentage,
        })

    return render(
        request,
        "parent_dashboard/attendance.html",
        {
            "students": students,
            "selected_student": selected_student,
            "attendance": attendance,
        },
    )
    
    
@login_required
def parent_result(request):

    parent = Parent.objects.get(user=request.user)

    students = parent.students.all()

    student_id = request.GET.get("student")

    student = students.filter(id=student_id).first()

    if not student:
        student = students.first()

    term = request.GET.get("term", "midterm")

    subjects = Subject.objects.filter(
        class_fk=student.class_fk
    )

    results = ExamResult.objects.filter(
        student=student,
        term=term
    )

    result_dict = {
        r.subject_id: r
        for r in results
    }

    comments_dict = {
        r.subject_id: r.teacher_remarks
        for r in results
    }

    return render(
        request,
        "parent_dashboard/result.html",
        {
            "student": student,
            "students": students,
            "subjects": subjects,
            "result_dict": result_dict,
            "comments_dict": comments_dict,
            "term": term,
        }
    )    
    
@login_required
def parent_assignment(request):

    parent = get_object_or_404(Parent, user=request.user)

    students = parent.students.all()

    student = students.filter(
        id=request.GET.get("student")
    ).first() or students.first()

    if student is None:
        return render(
            request,
            "parent_dashboard/assignments.html",
            {
                "students": students,
                "selected_student": None,
                "assignments": [],
            },
        )

    assignments = (
        Assignment.objects.filter(
            class_fk=student.class_fk,
            section=student.section,
        )
        .select_related("teacher", "subject")
        .order_by("due_date")
    )

    return render(
        request,
        "parent_dashboard/assignments.html",
        {
            "students": students,
            "selected_student": student,
            "assignments": assignments,
        },
    )
    
        
@login_required
def parent_quizzes(request):

    parent = get_object_or_404(Parent, user=request.user)

    students = parent.students.all()

    student = students.filter(
        id=request.GET.get("student")
    ).first() or students.first()

    if student is None:
        return render(
            request,
            "parent_dashboard/quizzes.html",
            {
                "students": students,
                "selected_student": None,
                "quizzes": [],
            },
        )

    quizzes = (
        Quiz.objects.filter(
            class_fk=student.class_fk,
            section=student.section,
        )
        .select_related("teacher", "subject")
        .order_by("due_date")
    )

    return render(
        request,
        "parent_dashboard/quizzes.html",
        {
            "students": students,
            "selected_student": student,
            "quizzes": quizzes,
        },
    )


    
@login_required
def parent_diary(request):

    parent = get_object_or_404(
        Parent,
        user=request.user
    )

    students = parent.students.all()

    student = students.filter(
        id=request.GET.get("student")
    ).first() or students.first()

    if student is None:
        return render(
            request,
            "parent_dashboard/diary.html",
            {
                "students": students,
                "selected_student": None,
                "diaries": [],
            },
        )

    diaries = Diary.objects.filter(
        class_fk=student.class_fk,
        section=student.section,
    ).select_related(
        "teacher",
        "subject",
    ).order_by("-date")

    return render(
        request,
        "parent_dashboard/diary.html",
        {
            "students": students,
            "selected_student": student,
            "diaries": diaries,
        },
    )    

@login_required
def parent_timetable(request):

    parent = get_object_or_404(Parent, user=request.user)

    students = parent.students.all()

    student = students.filter(
        id=request.GET.get("student")
    ).first() or students.first()

    if student is None:
        return render(
            request,
            "parent_dashboard/timetable.html",
            {
                "students": students,
                "selected_student": None,
                "period_order": [],
                "slots": {},
                "days": [],
            },
        )

    class_obj = student.class_fk
    section_obj = student.section

    all_periods = CreatePeriod.objects.all().order_by("day", "start_time")

    monday = all_periods.filter(day="Monday")

    period_order = [p.period_name for p in monday]

    for p in all_periods:
        if p.period_name not in period_order:
            period_order.append(p.period_name)

    days = [
        "Monday",
        "Tuesday",
        "Wednesday",
        "Thursday",
        "Friday",
        "Saturday",
    ]

    slots = {}

    for day in days:

        assigned_periods = AssignedPeriod.objects.filter(
            class_fk=class_obj,
            section=section_obj,
            day=day,
        ).select_related(
            "period",
            "subject",
            "teacher",
        )

        assigned_map = {
            ap.period.period_name: ap
            for ap in assigned_periods
        }

        day_slots = {}

        for pname in period_order:

            ap = assigned_map.get(pname)

            if ap:
                day_slots[pname] = {
                    "subject": ap.subject.name,
                    "teacher": ap.teacher.name,
                    "time": f"{ap.period.start_time.strftime('%I:%M %p')} - {ap.period.end_time.strftime('%I:%M %p')}",
                }
            else:
                day_slots[pname] = None

        slots[day] = day_slots

    return render(
        request,
        "parent_dashboard/timetable.html",
        {
            "students": students,
            "selected_student": student,
            "period_order": period_order,
            "slots": slots,
            "days": days,
            "class_info": class_obj,
            "section_info": section_obj,
        },
    )
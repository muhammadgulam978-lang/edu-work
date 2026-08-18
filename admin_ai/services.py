import re
from datetime import timedelta
from decimal import Decimal

from django.db.models import Avg, Count, Sum
from django.urls import reverse
from django.utils import timezone

from admin_panel.models import (
    Admission,
    AssignedPeriod,
    Class,
    ExamResult,
    FeeVoucher,
    Section,
    Subject,
    TeacherFixture,
)
from student_profile.models import AssignmentSubmission, QuizSubmission, Student
from teacher_dashboard.models import Attendance, Teacher

from .models import AdminAIToolAuditLog, AdminAIStudentProfileSnapshot


PERIOD_LABELS = {
    "today": "Today",
    "yesterday": "Yesterday",
    "week": "This Week",
    "this_month": "This Month",
    "last_month": "Last Month",
    "3_months": "Last 3 Months",
    "6_months": "Last 6 Months",
    "annual": "Annual",
    "custom": "Custom",
}


def _to_float(value):
    if isinstance(value, Decimal):
        return float(value)
    return value or 0


def _safe_count(queryset):
    try:
        return queryset.count()
    except Exception:
        return 0


def make_json_safe(value):
    if isinstance(value, Decimal):
        return float(value)
    if hasattr(value, "isoformat"):
        return value.isoformat()
    if isinstance(value, list):
        return [make_json_safe(item) for item in value]
    if isinstance(value, tuple):
        return [make_json_safe(item) for item in value]
    if isinstance(value, dict):
        return {str(key): make_json_safe(item) for key, item in value.items()}
    return value


def resolve_date_range(period="today", start_date=None, end_date=None):
    today = timezone.localdate()
    period = period or "today"

    if period == "yesterday":
        start = end = today - timedelta(days=1)
    elif period == "week":
        start = today - timedelta(days=today.weekday())
        end = today
    elif period == "this_month":
        start = today.replace(day=1)
        end = today
    elif period == "last_month":
        first_this_month = today.replace(day=1)
        end = first_this_month - timedelta(days=1)
        start = end.replace(day=1)
    elif period == "3_months":
        start = today - timedelta(days=90)
        end = today
    elif period == "6_months":
        start = today - timedelta(days=180)
        end = today
    elif period == "annual":
        start = today.replace(month=1, day=1)
        end = today
    elif period == "custom" and start_date and end_date:
        start = start_date
        end = end_date
    else:
        start = end = today

    return start, end, PERIOD_LABELS.get(period, "Today")


def _filter_class(queryset, class_id=None, section_id=None):
    if class_id:
        queryset = queryset.filter(class_fk_id=class_id)
    if section_id:
        queryset = queryset.filter(section_id=section_id)
    return queryset


def _class_name_for_id(class_id):
    if not class_id:
        return ""
    try:
        return Class.objects.only("class_name").get(id=class_id).class_name
    except Class.DoesNotExist:
        return ""


def _series_by_day(start, end, class_id=None, section_id=None):
    labels = []
    present = []
    absent = []
    leave = []
    day = start
    while day <= end:
        qs = _filter_class(Attendance.objects.filter(date=day), class_id, section_id)
        labels.append(day.strftime("%b %d"))
        present.append(_safe_count(qs.filter(status="present")))
        absent.append(_safe_count(qs.filter(status="absent")))
        leave.append(_safe_count(qs.filter(status="leave")))
        day += timedelta(days=1)
    return {"labels": labels, "present": present, "absent": absent, "leave": leave}


def _month_bounds(base_date, offset):
    month = base_date.month + offset
    year = base_date.year + ((month - 1) // 12)
    month = ((month - 1) % 12) + 1
    start = base_date.replace(year=year, month=month, day=1)
    if month == 12:
        end = start.replace(year=year + 1, month=1, day=1) - timedelta(days=1)
    else:
        end = start.replace(month=month + 1) - timedelta(days=1)
    return start, end


def _series_by_month(reference_date, class_id=None, section_id=None):
    labels = []
    fees_total = []
    fees_paid = []
    admissions = []
    fixtures_auto = []
    fixtures_manual = []
    class_name = _class_name_for_id(class_id)

    for offset in range(-5, 1):
        start, end = _month_bounds(reference_date, offset)
        labels.append(start.strftime("%b"))
        fee_qs = FeeVoucher.objects.filter(issue_date__gte=start, issue_date__lte=end)
        admission_qs = Admission.objects.filter(admission_date__gte=start, admission_date__lte=end)
        if class_id:
            if class_name:
                fee_qs = fee_qs.filter(student__current_class=class_name)
            admission_qs = admission_qs.filter(class_fk_id=class_id)
        if section_id:
            admission_qs = admission_qs.filter(section_id=section_id)

        fees_total.append(_to_float(fee_qs.aggregate(total=Sum("net_amount"))["total"]))
        fees_paid.append(_to_float(fee_qs.filter(status="PAID").aggregate(total=Sum("net_amount"))["total"]))
        admissions.append(_safe_count(admission_qs))
        fixtures_qs = TeacherFixture.objects.filter(fixture_date__gte=start, fixture_date__lte=end)
        fixtures_manual.append(_safe_count(fixtures_qs.filter(assignment_mode="manual")))
        fixtures_auto.append(_safe_count(fixtures_qs.exclude(assignment_mode="manual")))

    return {
        "labels": labels,
        "fees_total": fees_total,
        "fees_paid": fees_paid,
        "admissions": admissions,
        "fixtures_manual": fixtures_manual,
        "fixtures_auto": fixtures_auto,
    }


def build_advanced_analytics(filters=None):
    filters = filters or {}
    period = filters.get("period") or "today"
    start, end, label = resolve_date_range(period, filters.get("start_date"), filters.get("end_date"))
    class_id = filters.get("class_id")
    section_id = filters.get("section_id")

    students = Student.objects.all()
    admissions = Admission.objects.all()
    attendance = Attendance.objects.filter(date__gte=start, date__lte=end)
    fees = FeeVoucher.objects.filter(issue_date__gte=start, issue_date__lte=end)
    fixtures = TeacherFixture.objects.filter(fixture_date__gte=start, fixture_date__lte=end)
    exams = ExamResult.objects.filter(date_uploaded__date__gte=start, date_uploaded__date__lte=end)
    class_name = _class_name_for_id(class_id)

    if class_id:
        students = students.filter(class_fk_id=class_id)
        admissions = admissions.filter(class_fk_id=class_id)
        attendance = attendance.filter(class_fk_id=class_id)
        if class_name:
            fees = fees.filter(student__current_class=class_name)
        exams = exams.filter(class_fk_id=class_id)
    if section_id:
        students = students.filter(section_id=section_id)
        admissions = admissions.filter(section_id=section_id)
        attendance = attendance.filter(section_id=section_id)
        exams = exams.filter(section_id=section_id)

    attendance_total = _safe_count(attendance)
    present_count = _safe_count(attendance.filter(status="present"))
    absent_count = _safe_count(attendance.filter(status="absent"))
    leave_count = _safe_count(attendance.filter(status="leave"))
    attendance_rate = round((present_count / attendance_total) * 100, 1) if attendance_total else 0

    fee_total = _to_float(fees.aggregate(total=Sum("net_amount"))["total"])
    fee_paid = _to_float(fees.filter(status="PAID").aggregate(total=Sum("net_amount"))["total"])
    unpaid_vouchers = _safe_count(fees.exclude(status="PAID"))
    collection_rate = round((fee_paid / fee_total) * 100, 1) if fee_total else 0

    risk_score = min((absent_count * 6) + (unpaid_vouchers * 3) + (_safe_count(fixtures.filter(fixture_status="uncovered")) * 8), 100)
    day_series = _series_by_day(start, end, class_id, section_id)
    month_series = _series_by_month(end, class_id, section_id)

    workload_rows = list(
        AssignedPeriod.objects.values("teacher__name")
        .annotate(total=Count("id"))
        .order_by("-total")[:10]
    )

    return {
        "generated_at": timezone.now().strftime("%B %d, %Y, %I:%M %p"),
        "filters": {
            "period": period,
            "period_label": label,
            "start_date": start.isoformat(),
            "end_date": end.isoformat(),
            "class_id": class_id or "",
            "section_id": section_id or "",
        },
        "kpis": [
            {"key": "students", "title": "Students", "value": _safe_count(students), "label": "Active profiles", "tone": "teal", "icon": "fas fa-user-graduate"},
            {"key": "attendance", "title": "Attendance", "value": f"{attendance_rate}%", "label": f"{absent_count} absent records", "tone": "green" if absent_count == 0 else "warning", "icon": "fas fa-calendar-check"},
            {"key": "fees", "title": "Fee Collection", "value": f"{collection_rate}%", "label": f"{unpaid_vouchers} unpaid vouchers", "tone": "blue" if unpaid_vouchers == 0 else "warning", "icon": "fas fa-wallet"},
            {"key": "risk", "title": "AI Risk Index", "value": risk_score, "label": "Operational risk score", "tone": "green" if risk_score < 35 else "warning", "icon": "fas fa-brain"},
        ],
        "summary": {
            "students": _safe_count(students),
            "teachers": _safe_count(Teacher.objects.filter(status="active")),
            "classes": _safe_count(Class.objects.all()),
            "subjects": _safe_count(Subject.objects.all()),
            "attendance_total": attendance_total,
            "present": present_count,
            "absent": absent_count,
            "leave": leave_count,
            "fee_total": fee_total,
            "fee_paid": fee_paid,
            "unpaid_vouchers": unpaid_vouchers,
            "admissions": _safe_count(admissions.filter(admission_date__gte=start, admission_date__lte=end)),
            "fixtures": _safe_count(fixtures),
            "uncovered_fixtures": _safe_count(fixtures.filter(fixture_status="uncovered")),
            "average_exam_score": round(exams.aggregate(avg=Avg("marks_obtained"))["avg"] or 0, 1),
        },
        "charts": {
            "attendance": day_series,
            "fees": {"labels": month_series["labels"], "total": month_series["fees_total"], "paid": month_series["fees_paid"]},
            "admissions": {"labels": month_series["labels"], "values": month_series["admissions"]},
            "fixture_mix": {"labels": month_series["labels"], "manual": month_series["fixtures_manual"], "auto": month_series["fixtures_auto"]},
            "attendance_donut": {"labels": ["Present", "Absent", "Leave"], "values": [present_count, absent_count, leave_count]},
            "teacher_workload": {"labels": [row.get("teacher__name") or "Teacher" for row in workload_rows], "values": [row.get("total", 0) for row in workload_rows]},
        },
        "tables": {
            "teacher_workload": workload_rows,
            "absent_students": list(attendance.filter(status="absent").select_related("student", "class_fk", "section").values("student__student_id", "student__name", "class_fk__class_name", "section__section_name", "date")[:100]),
            "unpaid_vouchers": list(fees.exclude(status="PAID").select_related("student").values("voucher_no", "student__student_id", "student__full_name", "month", "year", "net_amount", "status")[:100]),
        },
    }


def parse_filter_request(request):
    period = request.GET.get("period") or request.POST.get("period") or "today"
    start = request.GET.get("start_date") or request.POST.get("start_date") or ""
    end = request.GET.get("end_date") or request.POST.get("end_date") or ""
    class_id = request.GET.get("class_id") or request.POST.get("class_id") or ""
    section_id = request.GET.get("section_id") or request.POST.get("section_id") or ""

    def parse_date(value):
        try:
            return timezone.datetime.fromisoformat(value).date() if value else None
        except ValueError:
            return None

    return {
        "period": period,
        "start_date": parse_date(start),
        "end_date": parse_date(end),
        "class_id": int(class_id) if str(class_id).isdigit() else None,
        "section_id": int(section_id) if str(section_id).isdigit() else None,
    }


def get_student_intelligence(student_id, user=None):
    student = (
        Student.objects.select_related("class_fk", "section", "user")
        .filter(student_id__iexact=student_id)
        .first()
    )
    if not student:
        student = Student.objects.select_related("class_fk", "section", "user").filter(id=student_id).first() if str(student_id).isdigit() else None
    if not student:
        return None

    photo_url = ""
    if getattr(student, "photo", None):
        try:
            photo_url = student.photo.url
        except ValueError:
            photo_url = ""

    attendance = Attendance.objects.filter(student=student)
    total_attendance = _safe_count(attendance)
    present = _safe_count(attendance.filter(status="present"))
    absent = _safe_count(attendance.filter(status="absent"))
    leave = _safe_count(attendance.filter(status="leave"))
    attendance_rate = round((present / total_attendance) * 100, 1) if total_attendance else 0

    vouchers = FeeVoucher.objects.filter(student__student_id=student.student_id).order_by("-issue_date")
    exams = ExamResult.objects.filter(student=student).select_related("subject").order_by("-date_uploaded")
    assignments = AssignmentSubmission.objects.filter(student=student).select_related("assignment").order_by("-submitted_at")
    quizzes = QuizSubmission.objects.filter(student=student).select_related("quiz").order_by("-submitted_at")

    ai_summary = {"sessions": 0, "practice_attempts": 0, "weak_topics": 0}
    try:
        from ai_tutor.models import AITutorSession, AIPracticeAttempt, StudentTopicMastery

        ai_summary = {
            "sessions": AITutorSession.objects.filter(student=student).count(),
            "practice_attempts": AIPracticeAttempt.objects.filter(student=student).count(),
            "weak_topics": StudentTopicMastery.objects.filter(student=student, mastery_level__lt=50).count(),
        }
    except Exception:
        pass

    snapshot = {
        "student": {
            "id": student.id,
            "student_id": student.student_id,
            "name": student.name,
            "father_name": student.father_name,
            "mother_name": student.mother_name,
            "email": student.email,
            "phone": str(student.phone or ""),
            "class": getattr(student.class_fk, "class_name", "No Class"),
            "section": getattr(student.section, "section_name", "No Section"),
            "roll_no": student.roll_no,
            "gender": student.gender,
            "date_of_birth": student.date_of_birth.isoformat() if student.date_of_birth else "",
            "photo_url": photo_url,
        },
        "attendance": {
            "total": total_attendance,
            "present": present,
            "absent": absent,
            "leave": leave,
            "rate": attendance_rate,
            "recent": list(attendance.order_by("-date").values("date", "status")[:20]),
        },
        "fees": {
            "total_vouchers": _safe_count(vouchers),
            "unpaid": _safe_count(vouchers.exclude(status="PAID")),
            "paid": _safe_count(vouchers.filter(status="PAID")),
            "recent": list(vouchers.values("voucher_no", "month", "year", "net_amount", "status")[:10]),
        },
        "marks": {
            "average": round(exams.aggregate(avg=Avg("marks_obtained"))["avg"] or 0, 1),
            "recent": list(exams.values("subject__name", "term", "marks_obtained", "total_marks", "teacher_remarks")[:20]),
        },
        "submissions": {
            "assignments": _safe_count(assignments),
            "quizzes": _safe_count(quizzes),
        },
        "ai_tutor": ai_summary,
    }
    AdminAIStudentProfileSnapshot.objects.create(student_id=student.student_id, viewed_by=user, snapshot_data=snapshot)
    return snapshot


def _extract_class_query(query):
    match = re.search(r"(?:class|grade)\s*([0-9]+|[a-zA-Z]+)", query.lower())
    if not match:
        return None
    return match.group(1)


def _extract_student_id(query):
    match = re.search(r"\b(?:student|id|profile)\s*[:#-]?\s*([A-Za-z]{1,4}[-]?\d{1,6}|\d{1,6})\b", query, re.IGNORECASE)
    if match:
        return match.group(1)
    match = re.search(r"\b(ST[-]?\d{1,6}|S\d{1,6})\b", query, re.IGNORECASE)
    return match.group(1) if match else None


def answer_admin_question(query, user=None, conversation=None):
    query = (query or "").strip()
    lower = query.lower()
    tool_name = "general_summary"
    filters = {}
    link = reverse("ai_analytics_advanced")

    if not query:
        answer = "Please ask a question about attendance, fees, students, reports, workload, or analytics."
        payload = {}
    elif "student" in lower and ("profile" in lower or "id" in lower or _extract_student_id(query)):
        student_id = _extract_student_id(query)
        tool_name = "get_student_profile"
        filters = {"student_id": student_id}
        if student_id:
            snapshot = get_student_intelligence(student_id, user=user)
            if snapshot:
                student = snapshot["student"]
                answer = (
                    f"{student['name']} ({student['student_id']}) is in {student['class']} - {student['section']}. "
                    f"Attendance rate is {snapshot['attendance']['rate']}%, with {snapshot['attendance']['absent']} absences. "
                    f"Fee status: {snapshot['fees']['unpaid']} unpaid voucher(s). Average marks: {snapshot['marks']['average']}."
                )
                link = reverse("admin_ai_student_intelligence_detail", kwargs={"student_id": student["student_id"]})
                payload = snapshot
            else:
                answer = "I could not find a student with that ID. Try the exact student ID from the student record."
                payload = {}
        else:
            answer = "Please include a student ID, for example: Show student ST001 profile."
            payload = {}
    elif "absent" in lower or "attendance" in lower or "present" in lower:
        class_query = _extract_class_query(query)
        class_obj = Class.objects.filter(class_name__icontains=class_query).first() if class_query else None
        filters = {"period": "today", "class_id": class_obj.id if class_obj else None}
        data = build_advanced_analytics(filters)
        tool_name = "get_class_attendance" if class_obj else "get_attendance_summary"
        class_text = f" for {class_obj.class_name}" if class_obj else ""
        answer = (
            f"Attendance today{class_text}: {data['summary']['present']} present, "
            f"{data['summary']['absent']} absent, {data['summary']['leave']} leave. "
            f"Attendance rate is {data['kpis'][1]['value']}."
        )
        payload = data
    elif "fee" in lower or "voucher" in lower or "collection" in lower or "compare" in lower:
        filters = {"period": "this_month"}
        data = build_advanced_analytics(filters)
        tool_name = "compare_fee_collection" if "compare" in lower else "get_fee_collection_summary"
        answer = (
            f"Fee collection for this month is {data['kpis'][2]['value']}. "
            f"Paid amount: {data['summary']['fee_paid']}; total billed: {data['summary']['fee_total']}; "
            f"unpaid vouchers: {data['summary']['unpaid_vouchers']}."
        )
        link = reverse("ai_analytics_reports")
        payload = data
    elif "workload" in lower or "teacher load" in lower or "period" in lower:
        data = build_advanced_analytics({"period": "this_month"})
        tool_name = "get_teacher_workload"
        rows = data["tables"]["teacher_workload"][:3]
        top = ", ".join([f"{row.get('teacher__name') or 'Teacher'}: {row.get('total', 0)}" for row in rows]) or "No assigned periods found"
        answer = f"Top teacher workload from assigned periods: {top}."
        payload = data
    elif "report" in lower or "pdf" in lower or "excel" in lower:
        tool_name = "generate_report_snapshot"
        answer = "Open the AI Analytics Report Center to generate PDF, Excel, and shareable reports."
        link = reverse("ai_analytics_reports")
        payload = {"report_center": link}
    else:
        data = build_advanced_analytics({"period": "today"})
        answer = (
            f"Today overview: {data['summary']['students']} students, "
            f"{data['summary']['absent']} absent records, {data['kpis'][2]['value']} fee collection, "
            f"and AI risk index {data['kpis'][3]['value']}."
        )
        payload = data

    AdminAIToolAuditLog.objects.create(
        user=user,
        conversation=conversation,
        tool_name=tool_name,
        query=query,
        filters=filters,
        result_summary=answer[:500],
        status="success",
    )
    return {
        "answer": answer,
        "tool_name": tool_name,
        "payload": payload,
        "link": link,
    }

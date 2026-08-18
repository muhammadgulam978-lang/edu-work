from collections import Counter

from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from .models import GradeRiskIntervention, StudentGradePrediction

# INTEGRATION NOTE: swap this for your project's real teacher-only decorator
# (you already use @login_required / @permission_required elsewhere in
# EduPilot per teacher_timetable_view) — e.g. @permission_required("teacher_dashboard.view_class")
TEACHER_ACCESS_DECORATOR = login_required


def _teacher_class_rooms(request):
    """
    Returns the Class queryset this logged-in teacher is assigned to,
    via teacher_dashboard.Teacher -> admin_panel.AssignedPeriod -> Class.

    NOTE: AssignedPeriod's exact field names (teacher / class_fk) are
    assumed from the naming convention used elsewhere in exam_system
    (e.g. QuestionBank.class_fk). If AssignedPeriod uses different field
    names in your admin_panel/models.py, adjust the filter() call below.
    """
    from admin_panel.models import AssignedPeriod, Class
    from teacher_dashboard.models import Teacher

    teacher = Teacher.objects.filter(user=request.user).first()
    if not teacher:
        return Class.objects.none()

    class_ids = (
        AssignedPeriod.objects.filter(teacher=teacher)
        .values_list("class_fk_id", flat=True)
        .distinct()
    )
    if class_ids:
        return Class.objects.filter(id__in=class_ids)

    # Fallback so the dashboard still renders if no periods are assigned yet
    return Class.objects.none()


@TEACHER_ACCESS_DECORATOR
def teacher_grade_predictor_dashboard(request):
    """
    Teacher Dashboard -> Analytics -> Grade Predictor  (spec section 13)
    Shows: expected pass rate, improving/stable/at-risk counts,
    predicted grade distribution, and the at-risk students table.
    """
    class_rooms = _teacher_class_rooms(request)
    subject_id = request.GET.get("subject")
    class_room_id = request.GET.get("class_room") or (
        class_rooms[0].id if class_rooms else None
    )

    predictions = StudentGradePrediction.objects.select_related(
        "student", "subject", "class_room"
    ).filter(class_room_id__in=[c.id for c in class_rooms]) if class_rooms else StudentGradePrediction.objects.none()

    if class_room_id:
        predictions = predictions.filter(class_room_id=class_room_id)
    if subject_id:
        predictions = predictions.filter(subject_id=subject_id)

    total = predictions.count()
    passing_grades = {"A+", "A", "B", "C", "D"}  # matches CentralizedResult.GRADE_CHOICES, F = fail
    passing = predictions.filter(predicted_grade__in=passing_grades).count()
    expected_pass_rate = round((passing / total) * 100) if total else 0

    improving = predictions.filter(trend__in=["improving", "rapidly_improving"]).count()
    stable = predictions.filter(trend="stable").count()
    at_risk = predictions.filter(risk_level__in=["high", "critical"]).count()

    grade_distribution = Counter(predictions.values_list("predicted_grade", flat=True))
    # keep a stable, spec-matching display order (matches CentralizedResult.GRADE_CHOICES)
    grade_order = ["A+", "A", "B", "C", "D", "F"]
    grade_distribution_ordered = [
        {"grade": g, "count": grade_distribution.get(g, 0)} for g in grade_order
    ]

    risk_students = predictions.filter(
        risk_level__in=["moderate", "high", "critical"]
    ).order_by("predicted_score")

    paginator = Paginator(risk_students, 15)
    page_obj = paginator.get_page(request.GET.get("page"))

    context = {
        "class_rooms": class_rooms,
        "selected_class_room_id": int(class_room_id) if class_room_id else None,
        "expected_pass_rate": expected_pass_rate,
        "improving_count": improving,
        "stable_count": stable,
        "at_risk_count": at_risk,
        "grade_distribution": grade_distribution_ordered,
        "risk_students": page_obj,
        "total_students": total,
    }
    return render(request, "grade_predictor/teacher_dashboard.html", context)


@TEACHER_ACCESS_DECORATOR
def student_prediction_detail(request, prediction_id):
    """Section 4 — Subject Prediction Detail, opened from the risk table row."""
    prediction = get_object_or_404(
        StudentGradePrediction.objects.select_related("student", "subject"),
        pk=prediction_id,
    )
    history = prediction.history.all()
    interventions = prediction.interventions.select_related("created_by")
    context = {
        "prediction": prediction,
        "history": history,
        "interventions": interventions,
    }
    return render(request, "grade_predictor/prediction_detail.html", context)


@TEACHER_ACCESS_DECORATOR
@require_POST
def create_intervention(request, prediction_id):
    """Section 14 — Teacher Intervention: Risk Detected -> Teacher Reviews
    Evidence -> Create Intervention -> Assign Practice / Remedial Class."""
    prediction = get_object_or_404(StudentGradePrediction, pk=prediction_id)
    action = request.POST.get("action", "").strip()
    note = request.POST.get("note", "").strip()

    if action:
        GradeRiskIntervention.objects.create(
            prediction=prediction,
            created_by=request.user,
            action=action,
            note=note,
        )

    if request.headers.get("x-requested-with") == "XMLHttpRequest":
        return JsonResponse({"status": "ok"})
    return redirect("grade_predictor:prediction_detail", prediction_id=prediction.id)

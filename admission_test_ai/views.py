from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render

from admin_panel.models import Admission, Class, Subject

from . import services
from .models import (
    AdmissionRecommendation,
    BlueprintSubject,
    GeneratedPaper,
    ReadinessReport,
    TestAttempt,
    TestBlueprint,
    TestSchedule,
)


@login_required
def dashboard(request):
    context = {
        "applications": Admission.objects.count(),
        "tests_scheduled": TestSchedule.objects.count(),
        "tests_completed": TestAttempt.objects.filter(status="evaluated").count(),
        "awaiting_evaluation": TestAttempt.objects.filter(status="awaiting_evaluation").count(),
        "recommended": AdmissionRecommendation.objects.filter(
            recommendation__in=["highly_recommended", "recommended"]
        ).count(),
        "borderline": ReadinessReport.objects.filter(is_borderline=True).count(),
        "reassessment": AdmissionRecommendation.objects.filter(
            recommendation="further_assessment"
        ).count(),
        "draft_papers": GeneratedPaper.objects.filter(status="ai_generated").count(),
        "pending_review": GeneratedPaper.objects.filter(
            status__in=["subject_teacher_review", "coordinator_review"]
        ).count(),
        "approved_papers": GeneratedPaper.objects.filter(status="approved").count(),
        "recent_blueprints": TestBlueprint.objects.select_related("applying_class")[:6],
        "recent_papers": GeneratedPaper.objects.select_related("blueprint")[:6],
    }
    return render(request, "admission_test_ai/dashboard.html", context)


@login_required
def blueprint_list(request):
    blueprints = TestBlueprint.objects.select_related("applying_class").prefetch_related("subjects__subject")
    return render(request, "admission_test_ai/blueprint_list.html", {"blueprints": blueprints})


@login_required
def blueprint_create(request):
    classes = Class.objects.all()
    subjects = Subject.objects.all()
    if request.method == "POST":
        bp = TestBlueprint.objects.create(
            name=request.POST.get("name"),
            applying_class_id=request.POST.get("applying_class"),
            curriculum=request.POST.get("curriculum") or "School Standard",
            passing_percentage=request.POST.get("passing_percentage") or 60,
            difficulty_easy_pct=request.POST.get("difficulty_easy_pct") or 30,
            difficulty_age_appropriate_pct=request.POST.get("difficulty_age_appropriate_pct") or 40,
            difficulty_moderate_pct=request.POST.get("difficulty_moderate_pct") or 20,
            difficulty_advanced_pct=request.POST.get("difficulty_advanced_pct") or 10,
            created_by=request.user,
        )
        subject_ids = request.POST.getlist("subject_id")
        for subject_id, num_q, marks, minutes, topics in zip(
            subject_ids,
            request.POST.getlist("num_questions"),
            request.POST.getlist("marks"),
            request.POST.getlist("time_minutes"),
            request.POST.getlist("topics"),
        ):
            if not subject_id:
                continue
            BlueprintSubject.objects.create(
                blueprint=bp,
                subject_id=subject_id,
                num_questions=num_q or 0,
                marks=marks or 0,
                time_minutes=minutes or 0,
                topics=topics or "",
            )
        bp.recompute_totals()
        messages.success(request, "Test blueprint saved.")
        return redirect("admission_blueprint_detail", pk=bp.pk)
    return render(
        request,
        "admission_test_ai/blueprint_form.html",
        {"classes": classes, "subjects": subjects},
    )


@login_required
def blueprint_detail(request, pk):
    bp = get_object_or_404(TestBlueprint.objects.prefetch_related("subjects__subject", "papers"), pk=pk)
    return render(request, "admission_test_ai/blueprint_detail.html", {"blueprint": bp})


@login_required
def generate_paper(request, pk):
    """Generates AI questions for every subject in the blueprint and creates
    a new draft GeneratedPaper version awaiting subject-teacher review."""
    bp = get_object_or_404(TestBlueprint, pk=pk)
    existing_versions = list(bp.papers.values_list("version_label", flat=True))
    next_label = next(v for v in "ABCDEFGH" if v not in existing_versions)

    all_questions = []
    try:
        for bp_subject in bp.subjects.all():
            questions = services.generate_questions_for_blueprint_subject(bp_subject)
            for q in questions:
                services.run_quality_check(q)
                services.find_duplicate_questions(q)
            all_questions.extend(questions)
    except Exception as exc:
        messages.error(request, f"AI paper generation failed: {exc}")
        return redirect("admission_blueprint_detail", pk=bp.pk)

    if not all_questions:
        messages.warning(
            request,
            "No questions were generated. Make sure the blueprint has at least one subject "
            "with a question count greater than 0.",
        )
        return redirect("admission_blueprint_detail", pk=bp.pk)


    paper = GeneratedPaper.objects.create(blueprint=bp, version_label=next_label, status="ai_generated")
    paper.questions.set(all_questions)
    messages.success(request, f"Paper {next_label} generated with {len(all_questions)} AI questions. Awaiting review.")
    return redirect("admission_paper_detail", pk=paper.pk)


@login_required
def paper_list(request):
    papers = GeneratedPaper.objects.select_related("blueprint").prefetch_related("questions")
    return render(request, "admission_test_ai/paper_list.html", {"papers": papers})


@login_required
def paper_detail(request, pk):
    paper = get_object_or_404(GeneratedPaper.objects.select_related("blueprint"), pk=pk)
    questions = paper.questions.select_related("blueprint_subject__subject").order_by(
        "blueprint_subject__subject__name", "id"
    )
    return render(request, "admission_test_ai/paper_detail.html", {"paper": paper, "questions": questions})


NEXT_STATUS = {
    "ai_generated": "subject_teacher_review",
    "subject_teacher_review": "coordinator_review",
    "coordinator_review": "approved",
}


@login_required
def paper_advance_status(request, pk):
    """Moves a paper through AI Generated -> Subject Teacher Review ->
    Academic Coordinator Review -> Approved. Approval is always a human
    action - the AI never auto-publishes a paper."""
    paper = get_object_or_404(GeneratedPaper, pk=pk)
    next_status = NEXT_STATUS.get(paper.status)
    if not next_status:
        messages.info(request, "This paper is already at its final status.")
        return redirect("admission_paper_detail", pk=paper.pk)
    paper.status = next_status
    paper.reviewed_by = request.user
    if request.method == "POST":
        paper.review_notes = request.POST.get("review_notes", paper.review_notes)
    if next_status == "approved":
        from django.utils import timezone

        paper.approved_at = timezone.now()
    paper.save()
    messages.success(request, f"Paper moved to: {paper.get_status_display()}")
    return redirect("admission_paper_detail", pk=paper.pk)


@login_required
def schedule_list(request):
    schedules = TestSchedule.objects.select_related("candidate", "paper__blueprint")
    return render(request, "admission_test_ai/schedule_list.html", {"schedules": schedules})


@login_required
def schedule_create(request):
    candidates = Admission.objects.all()
    approved_papers = GeneratedPaper.objects.filter(status="approved").select_related("blueprint")
    if request.method == "POST":
        schedule = TestSchedule.objects.create(
            candidate_id=request.POST.get("candidate"),
            paper_id=request.POST.get("paper"),
            test_date=request.POST.get("test_date"),
            test_time=request.POST.get("test_time"),
            campus=request.POST.get("campus", ""),
            room=request.POST.get("room", ""),
            mode=request.POST.get("mode", "online"),
        )
        TestAttempt.objects.get_or_create(schedule=schedule)
        messages.success(request, "Admission test scheduled and candidate notified.")
        return redirect("admission_schedule_list")
    return render(
        request,
        "admission_test_ai/schedule_form.html",
        {"candidates": candidates, "papers": approved_papers},
    )


@login_required
def readiness_report_view(request, attempt_id):
    attempt = get_object_or_404(TestAttempt.objects.select_related("schedule__candidate"), pk=attempt_id)
    report = getattr(attempt, "readiness_report", None)
    if report is None:
        report = services.build_readiness_report(attempt)
    return render(
        request,
        "admission_test_ai/readiness_report.html",
        {"attempt": attempt, "report": report},
    )

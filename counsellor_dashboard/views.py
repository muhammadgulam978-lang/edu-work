from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from .forms import (
    CaseClosureForm,
    CounsellingAppointmentForm,
    CounsellingCaseForm,
    CounsellingReferralForm,
    CounsellingSessionForm,
    SafeguardingConcernForm,
    StudentSupportPlanForm,
)
from .models import (
    CounsellingAppointment,
    CounsellingCase,
    CounsellingReferral,
    CounsellingSession,
    SafeguardingConcern,
    StudentSupportPlan,
)


# ---------------------------------------------------------------------------
# Dashboard
# ---------------------------------------------------------------------------

@login_required
def dashboard(request):
    today = timezone.localdate()

    todays_appointments = CounsellingAppointment.objects.filter(
        scheduled_datetime__date=today
    ).order_by("scheduled_datetime")
    new_referrals = CounsellingReferral.objects.filter(status="new").order_by("-created_at")
    follow_up_cases = CounsellingCase.objects.filter(
        status__in=["open", "in_progress", "monitoring"], follow_up_date__lte=today
    )
    high_priority_cases = CounsellingCase.objects.filter(
        priority__in=["high", "urgent"]
    ).exclude(status="closed")
    open_safeguarding = SafeguardingConcern.objects.exclude(status="closed").order_by("-reported_at")

    context = {
        "todays_appointments": todays_appointments,
        "new_referrals": new_referrals,
        "new_referrals_count": new_referrals.count(),
        "follow_up_count": follow_up_cases.count(),
        "high_priority_count": high_priority_cases.count(),
        "open_safeguarding": open_safeguarding[:6],
        "open_safeguarding_count": open_safeguarding.count(),
        "open_cases_count": CounsellingCase.objects.exclude(status="closed").count(),
    }
    return render(request, "counsellor_dashboard/dashboard.html", context)


# ---------------------------------------------------------------------------
# Referrals
# ---------------------------------------------------------------------------

@login_required
def referral_list(request):
    referrals = CounsellingReferral.objects.order_by("-created_at")
    return render(request, "counsellor_dashboard/referral_list.html", {"referrals": referrals})


@login_required
def referral_create(request):
    if request.method == "POST":
        form = CounsellingReferralForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(
                request,
                "Referral submitted. This is not an emergency service — for an immediate safety "
                "concern, use the Safeguarding workflow instead.",
            )
            return redirect("counsellor_dashboard:referral_list")
    else:
        form = CounsellingReferralForm()
    return render(request, "counsellor_dashboard/referral_form.html", {"form": form})


@login_required
def referral_accept(request, referral_id):
    referral = get_object_or_404(CounsellingReferral, pk=referral_id)
    referral.status = "accepted"
    referral.save()
    case = CounsellingCase.objects.create(
        student=referral.student,
        referral=referral,
        reason_for_referral=referral.description,
        priority=referral.priority,
    )
    messages.success(request, f"Case {case.case_number} opened from this referral.")
    return redirect("counsellor_dashboard:case_detail", case_id=case.id)


# ---------------------------------------------------------------------------
# Cases (confidential)
# ---------------------------------------------------------------------------

@login_required
@permission_required("counsellor_dashboard.view_confidential_case", raise_exception=True)
def case_list(request):
    cases = CounsellingCase.objects.select_related("student", "assigned_counsellor").order_by("-opened_at")
    return render(request, "counsellor_dashboard/case_list.html", {"cases": cases})


@login_required
@permission_required("counsellor_dashboard.view_confidential_case", raise_exception=True)
def case_create(request):
    if request.method == "POST":
        form = CounsellingCaseForm(request.POST)
        if form.is_valid():
            case = form.save()
            messages.success(request, f"Case {case.case_number} created.")
            return redirect("counsellor_dashboard:case_detail", case_id=case.id)
    else:
        form = CounsellingCaseForm()
    return render(request, "counsellor_dashboard/case_form.html", {"form": form})


@login_required
@permission_required("counsellor_dashboard.view_confidential_case", raise_exception=True)
def case_detail(request, case_id):
    case = get_object_or_404(CounsellingCase, pk=case_id)
    sessions = case.sessions.order_by("-session_datetime")
    support_plan = getattr(case, "support_plan", None)

    if request.method == "POST" and "close_case" in request.POST:
        closure_form = CaseClosureForm(request.POST, instance=case)
        if closure_form.is_valid():
            case = closure_form.save(commit=False)
            case.status = "closed"
            case.closed_at = timezone.now()
            case.save()
            messages.success(request, "Case closed.")
            return redirect("counsellor_dashboard:case_detail", case_id=case.id)
    else:
        closure_form = CaseClosureForm(instance=case)

    return render(
        request, "counsellor_dashboard/case_detail.html",
        {"case": case, "sessions": sessions, "support_plan": support_plan, "closure_form": closure_form},
    )


@login_required
@permission_required("counsellor_dashboard.view_confidential_session_note", raise_exception=True)
def session_create(request, case_id):
    case = get_object_or_404(CounsellingCase, pk=case_id)
    if request.method == "POST":
        form = CounsellingSessionForm(request.POST)
        if form.is_valid():
            session = form.save(commit=False)
            session.case = case
            session.save()
            messages.success(request, "Session note saved.")
            return redirect("counsellor_dashboard:case_detail", case_id=case.id)
    else:
        form = CounsellingSessionForm()
    return render(
        request, "counsellor_dashboard/session_form.html", {"form": form, "case": case}
    )


@login_required
@permission_required("counsellor_dashboard.view_confidential_case", raise_exception=True)
def support_plan_edit(request, case_id):
    case = get_object_or_404(CounsellingCase, pk=case_id)
    plan = getattr(case, "support_plan", None)
    if request.method == "POST":
        form = StudentSupportPlanForm(request.POST, instance=plan)
        if form.is_valid():
            plan = form.save(commit=False)
            plan.case = case
            plan.save()
            messages.success(request, "Support plan saved.")
            return redirect("counsellor_dashboard:case_detail", case_id=case.id)
    else:
        form = StudentSupportPlanForm(instance=plan)
    return render(
        request, "counsellor_dashboard/support_plan_form.html", {"form": form, "case": case}
    )


# ---------------------------------------------------------------------------
# Appointments
# ---------------------------------------------------------------------------

@login_required
def appointment_list(request):
    appointments = CounsellingAppointment.objects.select_related("student", "counsellor").order_by(
        "-scheduled_datetime"
    )
    return render(request, "counsellor_dashboard/appointment_list.html", {"appointments": appointments})


@login_required
def appointment_create(request):
    if request.method == "POST":
        form = CounsellingAppointmentForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Appointment scheduled.")
            return redirect("counsellor_dashboard:appointment_list")
    else:
        form = CounsellingAppointmentForm()
    return render(request, "counsellor_dashboard/appointment_form.html", {"form": form})


# ---------------------------------------------------------------------------
# Safeguarding (restricted)
# ---------------------------------------------------------------------------

@login_required
@permission_required("counsellor_dashboard.view_safeguarding_concern", raise_exception=True)
def safeguarding_list(request):
    concerns = SafeguardingConcern.objects.select_related("student").order_by("-reported_at")
    return render(request, "counsellor_dashboard/safeguarding_list.html", {"concerns": concerns})


@login_required
def safeguarding_create(request):
    # Intentionally reachable by any authenticated staff member (teacher, nurse, admin) —
    # anyone must be able to raise a safeguarding concern immediately.
    if request.method == "POST":
        form = SafeguardingConcernForm(request.POST)
        if form.is_valid():
            concern = form.save(commit=False)
            concern.status = "safeguarding_officer_notified"
            concern.save()
            messages.warning(
                request,
                "Safeguarding concern logged and the safeguarding officer has been notified. "
                "If this is an immediate danger, also contact emergency services directly.",
            )
            return redirect("counsellor_dashboard:dashboard")
    else:
        form = SafeguardingConcernForm()
    return render(request, "counsellor_dashboard/safeguarding_form.html", {"form": form})

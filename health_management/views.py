from datetime import timedelta

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from .forms import (
    EmergencyCaseForm,
    EmergencyClosureForm,
    HealthCheckupCycleForm,
    HealthCheckupRecordForm,
    MedicalVisitForm,
    MedicineBatchForm,
    MedicineForm,
    SickBayAdmissionForm,
)
from .models import (
    EmergencyCase,
    HealthCheckupCycle,
    HealthCheckupRecord,
    HealthProfile,
    MedicalVisit,
    Medicine,
    MedicineBatch,
    SickBayAdmission,
)


# ---------------------------------------------------------------------------
# Dashboard
# ---------------------------------------------------------------------------

@login_required
def dashboard(request):
    today = timezone.localdate()
    month_start = today.replace(day=1)

    checked_this_month = HealthCheckupRecord.objects.filter(
        checkup_date__gte=month_start, status__in=["completed", "completed_observation"]
    ).count()
    pending_checkups = HealthCheckupRecord.objects.filter(
        status__in=["not_scheduled", "scheduled", "consent_pending"]
    ).count()
    follow_up_required = HealthCheckupRecord.objects.filter(
        status="follow_up_required"
    ).count()

    visits_today = MedicalVisit.objects.filter(visit_datetime__date=today).count()
    in_sick_bay = SickBayAdmission.objects.filter(status__in=["resting", "awaiting_parent"]).count()
    emergencies_today = EmergencyCase.objects.filter(incident_datetime__date=today).count()
    open_emergencies = EmergencyCase.objects.exclude(status="closed").count()

    near_expiry_cutoff = today + timedelta(days=60)
    near_expiry_batches = MedicineBatch.objects.filter(
        expiry_date__lte=near_expiry_cutoff, expiry_date__gte=today
    ).count()
    low_stock_medicines = [m for m in Medicine.objects.all() if m.current_balance <= m.reorder_level]

    recent_emergencies = EmergencyCase.objects.order_by("-incident_datetime")[:6]
    recent_visits = MedicalVisit.objects.order_by("-visit_datetime")[:6]

    context = {
        "checked_this_month": checked_this_month,
        "pending_checkups": pending_checkups,
        "follow_up_required": follow_up_required,
        "visits_today": visits_today,
        "in_sick_bay": in_sick_bay,
        "emergencies_today": emergencies_today,
        "open_emergencies": open_emergencies,
        "near_expiry_batches": near_expiry_batches,
        "low_stock_count": len(low_stock_medicines),
        "recent_emergencies": recent_emergencies,
        "recent_visits": recent_visits,
    }
    return render(request, "health_management/dashboard.html", context)


# ---------------------------------------------------------------------------
# Checkup cycles + register
# ---------------------------------------------------------------------------

@login_required
def checkup_cycle_list(request):
    cycles = HealthCheckupCycle.objects.order_by("-start_date")
    return render(request, "health_management/checkup_cycle_list.html", {"cycles": cycles})


@login_required
def checkup_cycle_create(request):
    if request.method == "POST":
        form = HealthCheckupCycleForm(request.POST)
        if form.is_valid():
            cycle = form.save()
            messages.success(request, "Checkup cycle created.")
            return redirect("health_management:checkup_register", cycle_id=cycle.id)
    else:
        form = HealthCheckupCycleForm()
    return render(request, "health_management/checkup_cycle_form.html", {"form": form})


@login_required
def checkup_register(request, cycle_id):
    cycle = get_object_or_404(HealthCheckupCycle, pk=cycle_id)
    records = cycle.records.select_related("profile").order_by("profile__id")
    return render(
        request, "health_management/checkup_register.html",
        {"cycle": cycle, "records": records},
    )


@login_required
def checkup_record_edit(request, record_id):
    record = get_object_or_404(HealthCheckupRecord, pk=record_id)
    if request.method == "POST":
        form = HealthCheckupRecordForm(request.POST, instance=record)
        if form.is_valid():
            form.save()
            messages.success(request, "Checkup record updated.")
            return redirect("health_management:checkup_register", cycle_id=record.cycle_id)
    else:
        form = HealthCheckupRecordForm(instance=record)
    return render(
        request, "health_management/checkup_form.html",
        {"form": form, "record": record},
    )


# ---------------------------------------------------------------------------
# Health profile
# ---------------------------------------------------------------------------

@login_required
def health_profile_detail(request, profile_id):
    profile = get_object_or_404(HealthProfile, pk=profile_id)
    context = {
        "profile": profile,
        "checkups": profile.checkups.order_by("-checkup_date")[:10],
        "visits": profile.medical_visits.order_by("-visit_datetime")[:10],
        "emergencies": profile.emergency_cases.order_by("-incident_datetime")[:10],
        "allergies": profile.allergies.all(),
        "chronic_conditions": profile.chronic_conditions.all(),
    }
    return render(request, "health_management/health_profile_detail.html", context)


# ---------------------------------------------------------------------------
# Medical room visits
# ---------------------------------------------------------------------------

@login_required
def medical_visit_list(request):
    visits = MedicalVisit.objects.select_related("profile").order_by("-visit_datetime")[:200]
    return render(request, "health_management/medical_visit_list.html", {"visits": visits})


@login_required
def medical_visit_create(request):
    if request.method == "POST":
        form = MedicalVisitForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Medical visit recorded.")
            return redirect("health_management:medical_visit_list")
    else:
        form = MedicalVisitForm()
    return render(request, "health_management/medical_visit_form.html", {"form": form})


# ---------------------------------------------------------------------------
# Emergency treatment
# ---------------------------------------------------------------------------

@login_required
def emergency_case_list(request):
    cases = EmergencyCase.objects.select_related("profile").order_by("-incident_datetime")[:200]
    return render(request, "health_management/emergency_case_list.html", {"cases": cases})


@login_required
def emergency_case_create(request):
    if request.method == "POST":
        form = EmergencyCaseForm(request.POST)
        if form.is_valid():
            case = form.save()
            messages.success(request, f"Emergency case {case.case_number} created.")
            return redirect("health_management:emergency_case_detail", case_id=case.id)
    else:
        form = EmergencyCaseForm()
    return render(request, "health_management/emergency_case_form.html", {"form": form})


@login_required
def emergency_case_detail(request, case_id):
    case = get_object_or_404(EmergencyCase, pk=case_id)
    if request.method == "POST":
        closure_form = EmergencyClosureForm(request.POST, instance=case)
        if closure_form.is_valid():
            case = closure_form.save(commit=False)
            case.status = "closed"
            case.closed_at = timezone.now()
            case.save()
            messages.success(request, "Emergency case closed.")
            return redirect("health_management:emergency_case_detail", case_id=case.id)
    else:
        closure_form = EmergencyClosureForm(instance=case)
    return render(
        request, "health_management/emergency_case_detail.html",
        {"case": case, "closure_form": closure_form},
    )


# ---------------------------------------------------------------------------
# Sick bay
# ---------------------------------------------------------------------------

@login_required
def sick_bay_list(request):
    admissions = SickBayAdmission.objects.select_related("profile").order_by("-admission_time")
    return render(request, "health_management/sick_bay_list.html", {"admissions": admissions})


@login_required
def sick_bay_create(request):
    if request.method == "POST":
        form = SickBayAdmissionForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Sick bay admission recorded.")
            return redirect("health_management:sick_bay_list")
    else:
        form = SickBayAdmissionForm()
    return render(request, "health_management/sick_bay_form.html", {"form": form})


# ---------------------------------------------------------------------------
# Medicine inventory
# ---------------------------------------------------------------------------

@login_required
def medicine_inventory_list(request):
    medicines = Medicine.objects.prefetch_related("batches").order_by("name")
    return render(request, "health_management/medicine_inventory_list.html", {"medicines": medicines})


@login_required
def medicine_create(request):
    if request.method == "POST":
        form = MedicineForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Medicine added to inventory.")
            return redirect("health_management:medicine_inventory_list")
    else:
        form = MedicineForm()
    return render(request, "health_management/medicine_form.html", {"form": form})


@login_required
def medicine_batch_create(request):
    if request.method == "POST":
        form = MedicineBatchForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Stock batch added.")
            return redirect("health_management:medicine_inventory_list")
    else:
        form = MedicineBatchForm()
    return render(request, "health_management/medicine_batch_form.html", {"form": form})

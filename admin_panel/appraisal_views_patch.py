# ==================== APPRAISAL — FIXED SECTION ====================
# Sirf ye 3 functions apni views.py mein replace karo
# ====================================================================

from django.contrib.auth.decorators import user_passes_test, login_required
from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render
from admin_panel.models import AppraisalCycle, TeacherAppraisalSubmission, KpiTemplate, KpiRule
from .appraisal_services import generate_score, predict_band, train_random_forest


def is_admin(user):
    return user.is_superuser or user.is_staff or user.groups.filter(name__iexact="Admin").exists()


# ─────────────────────────────────────────────────────────
# 1. KPI BUILDER — koi change nahi, same rakho
# ─────────────────────────────────────────────────────────
@login_required
@user_passes_test(is_admin)
def admin_kpi_builder(request):
    cycle = AppraisalCycle.objects.filter(is_open=True).order_by("-start_date").first()
    if not cycle:
        messages.error(request, "No open appraisal cycle found.")
        return redirect("admin_dashboard")

    template = KpiTemplate.objects.filter(cycle=cycle).order_by("-id").first()
    if not template:
        template = KpiTemplate.objects.create(name=f"KPI Template - {cycle.name}", cycle=cycle)

    auto_keys = [k for k, _ in KpiRule.AUTO_KPI_KEYS]
    for k, label in KpiRule.AUTO_KPI_KEYS:
        KpiRule.objects.get_or_create(
            template=template,
            kpi_key=k,
            defaults={
                "title": label,
                "weight": 0,
                "target_value": 0,
                "scoring_method": "linear",
                "is_active": True,
                "is_manual": False,
            },
        )

    if request.method == "POST" and request.POST.get("save_kpis") == "1":
        for k in auto_keys:
            rule = template.rules.filter(kpi_key=k, is_manual=False).first()
            if not rule:
                continue
            active = request.POST.get(f"auto_active_{k}") == "on"
            w = request.POST.get(f"auto_weight_{k}") or "0"
            try:
                rule.weight = float(w)
            except Exception:
                rule.weight = 0.0
            rule.is_active = active
            rule.save(update_fields=["weight", "is_active"])

        manual_rules = list(template.rules.filter(is_manual=True).order_by("id"))
        for r in manual_rules:
            if request.POST.get(f"manual_delete_{r.id}") == "on":
                r.delete()
                continue
            r.is_active = request.POST.get(f"manual_active_{r.id}") == "on"
            r.title = (request.POST.get(f"manual_title_{r.id}") or r.title).strip()
            w = request.POST.get(f"manual_weight_{r.id}") or str(r.weight or 0)
            try:
                r.weight = float(w)
            except Exception:
                pass
            r.save()

        new_titles = request.POST.getlist("manual_title[]")
        new_weights = request.POST.getlist("manual_weight[]")
        for idx, t in enumerate(new_titles):
            t = (t or "").strip()
            if not t:
                continue
            w = 0.0
            if idx < len(new_weights):
                try:
                    w = float(new_weights[idx] or 0)
                except Exception:
                    w = 0.0
            KpiRule.objects.create(
                template=template,
                title=t,
                weight=w,
                is_active=True,
                is_manual=True,
                scoring_method="linear",
                target_value=10,
            )

        messages.success(request, "KPI rules saved successfully.")
        return redirect("admin_kpi_builder")

    auto_kpis = template.rules.filter(is_manual=False, kpi_key__in=auto_keys).order_by("id")
    manual_rules = template.rules.filter(is_manual=True).order_by("id")

    return render(request, "admin_panel/appraisal_admin_kpis.html", {
        "cycle": cycle,
        "template": template,
        "auto_kpis": auto_kpis,
        "manual_rules": manual_rules,
    })


# ─────────────────────────────────────────────────────────
# 2. APPRAISAL LIST — koi change nahi, same rakho
# ─────────────────────────────────────────────────────────
@login_required
@user_passes_test(is_admin)
def admin_appraisal_list(request):
    cycle = AppraisalCycle.objects.filter(is_open=True).order_by("-start_date").first()
    qs = TeacherAppraisalSubmission.objects.select_related("teacher", "cycle").order_by("-updated_at")
    if cycle:
        qs = qs.filter(cycle=cycle)
    return render(request, "admin_panel/appraisal_admin_list.html", {
        "cycle": cycle, "submissions": qs
    })


# ─────────────────────────────────────────────────────────
# 3. APPRAISAL DETAIL — ✅ FIX: train_random_forest ko
#    template argument diya gaya
# ─────────────────────────────────────────────────────────
@login_required
@user_passes_test(is_admin)
def admin_appraisal_detail(request, pk):
    submission = get_object_or_404(TeacherAppraisalSubmission, pk=pk)
    generate_score(submission)
    pred = predict_band(submission)

    if request.method == "POST":

        if request.POST.get("save_final_band"):
            submission.final_band = request.POST.get("final_band", "")
            submission.save(update_fields=["final_band"])
            messages.success(request, "Final band saved.")
            return redirect("admin_appraisal_detail", pk=pk)

        if request.POST.get("train_ml"):
            labeled = TeacherAppraisalSubmission.objects.exclude(
                final_band=""
            ).exclude(auto_metrics={})

            # ✅ FIX 1: submission ka kpi_template pass karo
            template = submission.kpi_template

            # ✅ FIX 2: agar template nahi mila to cycle se dhundo
            if not template and submission.cycle:
                template = KpiTemplate.objects.filter(
                    cycle=submission.cycle
                ).order_by("-id").first()

            if not template:
                messages.error(
                    request,
                    "❌ KPI Template nahi mila. Pehle KPI Builder mein template banao."
                )
                return redirect("admin_appraisal_detail", pk=pk)

            try:
                # ✅ FIX 3: dono arguments diye — submissions aur template
                train_random_forest(labeled, template)
                messages.success(request, "✅ RandomForest trained successfully.")
            except RuntimeError as e:
                messages.error(request, f"❌ Training failed: {str(e)}")
            except Exception as e:
                messages.error(request, f"❌ Unexpected error: {str(e)}")

            return redirect("admin_appraisal_detail", pk=pk)

        if request.POST.get("regenerate"):
            generate_score(submission)
            messages.success(request, "Score regenerated.")
            return redirect("admin_appraisal_detail", pk=pk)

    return render(request, "admin_panel/appraisal_admin_detail.html", {
        "submission": submission,
        "pred": pred,
    })

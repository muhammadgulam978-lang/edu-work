import os
from collections import defaultdict
from django.conf import settings
from admin_panel.models import (
    AssignedPeriod, TeacherFixture,
    AppraisalScore, GradePolicy, MLModelArtifact, KpiRule,
    AppraisalSection,  # ✅ NEW
)

# ExamResult import safely — agar model nahi hai to gracefully handle karo
try:
    from admin_panel.models import ExamResult
    EXAM_RESULT_OK = True
except ImportError:
    EXAM_RESULT_OK = False

try:
    from sklearn.ensemble import RandomForestClassifier
    import joblib
    SKLEARN_OK = True
except Exception:
    SKLEARN_OK = False


# ✅ NEW (Phase 1) — default sections auto-create karne wala helper
DEFAULT_SECTIONS = [
    ("Teaching & Learning", 1),
    ("Student Performance", 2),
    ("Professional Behaviour", 3),
    ("Leadership", 4),
    ("Professional Development", 5),
]


def ensure_default_sections(template):
    """Template ke liye default sections banata hai agar already na hoon."""
    if template.sections.exists():
        return
    for name, order in DEFAULT_SECTIONS:
        AppraisalSection.objects.create(template=template, name=name, order=order)


def band_from_score(total):
    if total >= 90:
        return "Outstanding"
    if total >= 80:
        return "Excellent"
    if total >= 70:
        return "Good"
    if total >= 60:
        return "Fair"
    if total >= 50:
        return "Average"
    return "Below Average"


def score_rule(actual, rule):
    if rule.target_value <= 0:
        return 0.0
    raw = (float(actual) / float(rule.target_value)) * 100.0
    return max(0.0, min(100.0, raw))


# ✅ NEW — ExamResult % ko GradePolicy thresholds se A/B/C/D/E/F mein convert karta hai
def _grade_for_percentage(percentage, policy):
    if not policy:
        # policy na ho to default standard thresholds use karo
        a_min, b_min, c_min, d_min, e_min = 80, 70, 60, 50, 40
    else:
        a_min, b_min, c_min, d_min, e_min = (
            policy.a_min, policy.b_min, policy.c_min, policy.d_min, policy.e_min
        )

    if percentage >= a_min:
        return "A"
    if percentage >= b_min:
        return "B"
    if percentage >= c_min:
        return "C"
    if percentage >= d_min:
        return "D"
    if percentage >= e_min:
        return "E"
    return "F"


# ✅ NEW — teacher ke saare ExamResult se pass_rate / ab_rate / a_rate nikalta hai
def _compute_exam_rates(teacher, grade_policy):
    """
    Returns: (total_results, pass_rate, ab_rate, a_rate, grade_counts_dict)
    """
    if not EXAM_RESULT_OK:
        return 0, 0.0, 0.0, 0.0, {}

    try:
        exam_qs = ExamResult.objects.filter(teacher=teacher)
        total_results = exam_qs.count()
    except Exception:
        return 0, 0.0, 0.0, 0.0, {}

    if total_results == 0:
        return 0, 0.0, 0.0, 0.0, {}

    grade_counts = {"A": 0, "B": 0, "C": 0, "D": 0, "E": 0, "F": 0}

    for result in exam_qs:
        try:
            if not result.total_marks or float(result.total_marks) <= 0:
                continue
            percentage = (float(result.marks_obtained) / float(result.total_marks)) * 100.0
        except Exception:
            continue

        grade = _grade_for_percentage(percentage, grade_policy)
        grade_counts[grade] = grade_counts.get(grade, 0) + 1

    graded_total = sum(grade_counts.values())
    if graded_total == 0:
        return total_results, 0.0, 0.0, 0.0, grade_counts

    pass_count = graded_total - grade_counts.get("F", 0)
    ab_count = grade_counts.get("A", 0) + grade_counts.get("B", 0)
    a_count = grade_counts.get("A", 0)

    pass_rate = round((pass_count / graded_total) * 100.0, 2)
    ab_rate = round((ab_count / graded_total) * 100.0, 2)
    a_rate = round((a_count / graded_total) * 100.0, 2)

    return total_results, pass_rate, ab_rate, a_rate, grade_counts


BASE_FEATURE_KEYS = [
    "pass_rate",
    "ab_rate",
    "a_rate",
    "results_count",
    "classes_taught",
    "fixtures_substitute",
    "fixtures_absent",
    "workshops_attended",
    "trainings_given",
    "extra_curricular",
    "diary_submissions",
    "lesson_plans_created",
    "lesson_days_created",
    "lecture_notes_uploaded",
    "assignments_uploaded",
    "quizzes_created",
]


def _feature_keys_for_template(template):
    manual_keys = list(
        template.rules.filter(is_active=True, is_manual=True).values_list("kpi_key", flat=True)
    )
    manual_keys = [k for k in manual_keys if k]
    return BASE_FEATURE_KEYS + sorted(set(manual_keys))


def _vector_from_submission(submission, feature_keys):
    m = submission.auto_metrics or {}
    manual = submission.manual_ratings or {}

    vec = []
    for k in feature_keys:
        if k in manual:
            vec.append(float(manual.get(k, 0) or 0))
        else:
            vec.append(float(m.get(k, manual.get(k, 0)) or 0))
    return vec


def generate_score(submission):
    template = submission.kpi_template
    if not template:
        return None

    # ✅ NEW — ensure sections exist (safe no-op if already there)
    ensure_default_sections(template)

    # grade_policy attribute safely access karo
    grade_policy = getattr(template, 'grade_policy', None) or GradePolicy.objects.first()

    # ── Auto Metrics Collect ──
    assignments = AssignedPeriod.objects.filter(teacher=submission.teacher).distinct()
    classes_taught = assignments.count()

    # TeacherFixture mein 'date' field nahi — 'day' field hai (string)
    # Isliye date filter hata diya; sirf teacher filter se count karo
    fixtures_absent = TeacherFixture.objects.filter(
        absent_teacher=submission.teacher
    ).count()

    fixtures_substitute = TeacherFixture.objects.filter(
        substitute_teacher=submission.teacher
    ).count()

    # ✅ FIXED — ExamResult se actual grade-based rates calculate karo
    total_results, pass_rate, ab_rate, a_rate, grade_counts = _compute_exam_rates(
        submission.teacher, grade_policy
    )

    # Pehle se saved manual metrics preserve karo, naye auto metrics upar se set karo
    metrics = dict(submission.auto_metrics or {})
    metrics.update({
        "classes_taught": classes_taught,
        "fixtures_absent": fixtures_absent,
        "fixtures_substitute": fixtures_substitute,
        "results_count": total_results,
        "pass_rate": pass_rate,
        "ab_rate": ab_rate,
        "a_rate": a_rate,
    })

    # ✅ NEW — results_summary field ko bhi A/B/C/D/E/F breakdown se update karo
    if grade_counts:
        submission.results_summary = grade_counts

    breakdown = {}
    total = 0.0

    rules = template.rules.filter(is_active=True).select_related("section")

    for rule in rules:
        if rule.is_manual:
            key = (rule.kpi_key or "").strip()
            actual = float((submission.manual_ratings or {}).get(key, 0) or 0)
            target = float(rule.target_value or 10)
        else:
            actual = float(metrics.get(rule.kpi_key, 0))
            target = float(rule.target_value or 0)

        kpi_score = score_rule(actual, rule)
        weighted = kpi_score * (float(rule.weight) / 100.0)

        breakdown_key = rule.kpi_key or rule.title
        breakdown[breakdown_key] = {
            "title": rule.title,
            "section": rule.section.name if rule.section_id else None,  # ✅ NEW
            "actual": actual,
            "target": target,
            "method": "linear",
            "kpi_score": round(kpi_score, 2),
            "weight": float(rule.weight),
            "weighted": round(weighted, 2),
        }

        total += weighted

    total_score = round(total, 2)
    band = band_from_score(total_score)

    submission.auto_metrics = metrics
    submission.save(update_fields=["auto_metrics", "results_summary", "updated_at"])

    obj, _ = AppraisalScore.objects.get_or_create(submission=submission)
    obj.total_score = total_score
    obj.band = band
    obj.breakdown = breakdown
    obj.save()

    return obj


# template parameter add kiya — views.py se match karne ke liye
def train_random_forest(submissions_qs, template=None):
    if not SKLEARN_OK:
        raise RuntimeError(
            "scikit-learn/joblib not installed. "
            "Run: pip install scikit-learn joblib"
        )

    # template None ho to auto detect karo
    if template is None:
        first = submissions_qs.first()
        if first and first.kpi_template:
            template = first.kpi_template
        else:
            raise RuntimeError("No KpiTemplate found — please pass template argument.")

    feature_keys = _feature_keys_for_template(template)

    X, y = [], []
    for s in submissions_qs:
        if not s.final_band:
            continue
        X.append(_vector_from_submission(s, feature_keys))
        y.append(s.final_band)

    if len(X) < 10:
        raise RuntimeError(
            f"At least 10 labeled submissions required to train ML model. "
            f"Currently only {len(X)} available."
        )

    clf = RandomForestClassifier(
        n_estimators=300,
        random_state=42,
        n_jobs=-1
    )
    clf.fit(X, y)

    folder = os.path.join(settings.MEDIA_ROOT, "appraisal_models")
    os.makedirs(folder, exist_ok=True)
    path = os.path.join(folder, "rf_appraisal.joblib")
    joblib.dump(clf, path)

    MLModelArtifact.objects.update(is_active=False)
    MLModelArtifact.objects.create(
        model_path=path,
        algorithm="RandomForest",
        is_active=True,
        feature_keys=feature_keys,
    )

    return path


def predict_band(submission):
    if not SKLEARN_OK:
        return ""

    art = MLModelArtifact.objects.filter(is_active=True).order_by("-trained_at").first()
    if not art or not os.path.exists(art.model_path):
        return ""

    import joblib
    clf = joblib.load(art.model_path)

    feature_keys = art.feature_keys or BASE_FEATURE_KEYS
    X = [_vector_from_submission(submission, feature_keys)]
    pred = clf.predict(X)[0]
    return str(pred)
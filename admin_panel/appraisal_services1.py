import os
from collections import defaultdict
from django.conf import settings
from admin_panel.models import (
    AssignedPeriod, ExamResult, TeacherFixture,
    AppraisalScore, GradePolicy, MLModelArtifact, KpiRule
)

try:
    from sklearn.ensemble import RandomForestClassifier
    import joblib
    SKLEARN_OK = True
except Exception:
    SKLEARN_OK = False


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
    # Manual + Auto dono ke liye linear allow
    if rule.target_value <= 0:
        return 0.0
    raw = (float(actual) / float(rule.target_value)) * 100.0
    return max(0.0, min(100.0, raw))


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
        if k in (manual.keys()):
            vec.append(float(manual.get(k, 0) or 0))
        else:
            # if manual key not directly present, still try
            if k not in m and k in manual:
                vec.append(float(manual.get(k, 0) or 0))
            else:
                vec.append(float(m.get(k, manual.get(k, 0)) or 0))
    return vec


def generate_score(submission):
    template = submission.kpi_template
    if not template:
        return None

    grade_policy = template.grade_policy or GradePolicy.objects.first()

    # build metrics (auto)
    assignments = AssignedPeriod.objects.filter(teacher=submission.teacher).distinct()
    classes_taught = assignments.count()

    fixtures_absent = TeacherFixture.objects.filter(
        absent_teacher=submission.teacher,
        date__gte=submission.cycle.start_date,
        date__lte=submission.cycle.end_date
    ).count()

    fixtures_substitute = TeacherFixture.objects.filter(
        substitute_teacher=submission.teacher,
        date__gte=submission.cycle.start_date,
        date__lte=submission.cycle.end_date
    ).count()

    # NOTE: tumhara existing compute_exam_summary etc. agar already hai to usko use kar lo
    # yahan short version assume:
    exam_qs = ExamResult.objects.filter(
        teacher=submission.teacher,
        date_uploaded__date__gte=submission.cycle.start_date,
        date_uploaded__date__lte=submission.cycle.end_date
    )
    total_results = exam_qs.count()
    pass_rate = 0.0
    ab_rate = 0.0
    a_rate = 0.0

    metrics = submission.auto_metrics or {}
    metrics.update({
        "classes_taught": classes_taught,
        "fixtures_absent": fixtures_absent,
        "fixtures_substitute": fixtures_substitute,
        "results_count": total_results,
        "pass_rate": pass_rate,
        "ab_rate": ab_rate,
        "a_rate": a_rate,
    })

    breakdown = {}
    total = 0.0

    rules = template.rules.filter(is_active=True)

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

        breakdown_key = rule.kpi_key
        breakdown[breakdown_key] = {
            "title": rule.title,
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
    submission.save(update_fields=["auto_metrics", "updated_at"])

    obj, _ = AppraisalScore.objects.get_or_create(submission=submission)
    obj.total_score = total_score
    obj.band = band
    obj.breakdown = breakdown
    obj.save()

    return obj


def train_random_forest(submissions_qs, template):
    if not SKLEARN_OK:
        raise RuntimeError("scikit-learn/joblib not installed. Install: pip install scikit-learn joblib")

    feature_keys = _feature_keys_for_template(template)

    X, y = [], []
    for s in submissions_qs:
        if not s.final_band:
            continue
        X.append(_vector_from_submission(s, feature_keys))
        y.append(s.final_band)

    if len(X) < 10:
        raise RuntimeError("At least 10 labeled submissions required to train ML model.")

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

"""
Grade Predictor — prediction engine.

Per spec section 19, v1 deliberately avoids deep learning:
    school grading formula + statistical forecasting + explainable rules.
Swap `_trend_projection` / `_grade_probability` for a gradient-boosting
model later once enough historical data exists — the rest of the pipeline
(weighted score -> confidence -> risk -> explanation) stays the same.

INTEGRATION NOTE: `get_assessment_records(student, subject)` is the one
function you MUST adapt to your real exam_system models. It should return
a list of dicts: {"category": "quiz", "score_pct": 82.0, "label": "Quiz 3",
"date": <datetime>}. Everything else in this file is generic.
"""

from __future__ import annotations

import statistics
from dataclasses import dataclass, field
from typing import Optional

from django.utils import timezone

from .models import GradePredictorConfig, StudentGradePrediction, PredictionHistory


DEFAULT_GRADING_SCALE = {
    # Kept in sync with exam_system.CentralizedResult.GRADE_CHOICES
    "A+": (90, 100), "A": (80, 89), "B": (70, 79),
    "C": (60, 69), "D": (50, 59), "F": (0, 49),
}
DEFAULT_WEIGHTAGES = {
    # Maps to ExamPlan.EXAM_TYPES: WEEKLY, MONTHLY, MIDTERM, FINAL
    "quiz": 15,        # WEEKLY
    "class_test": 20,  # MONTHLY
    "midterm": 25,     # MIDTERM
    "final_exam": 40,  # FINAL
}
DEFAULT_RISK_THRESHOLDS = {"low": 70, "moderate": 60, "high": 50, "critical": 0}
DEFAULT_CONFIDENCE_THRESHOLDS = {"high": 5, "medium": 3, "low": 0}


@dataclass
class PredictionResult:
    current_score: float
    predicted_score: float
    predicted_range: tuple
    predicted_grade: str
    grade_probability: dict
    confidence_level: str
    confidence_pct: float
    trend: str
    risk_level: str
    assessments_used: int
    explanation: dict = field(default_factory=dict)
    weak_topics: list = field(default_factory=list)
    strong_topics: list = field(default_factory=list)
    history_points: list = field(default_factory=list)


def get_config() -> GradePredictorConfig:
    config = GradePredictorConfig.objects.first()
    if config:
        return config
    # Sensible fallback so the dashboard never crashes before an admin configures it
    return GradePredictorConfig(
        grading_scale=DEFAULT_GRADING_SCALE,
        assessment_weightages=DEFAULT_WEIGHTAGES,
        risk_thresholds=DEFAULT_RISK_THRESHOLDS,
        confidence_thresholds=DEFAULT_CONFIDENCE_THRESHOLDS,
        minimum_data_requirement=2,
    )


def score_to_grade(score: float, grading_scale: dict) -> str:
    for grade, bounds in grading_scale.items():
        low, high = bounds
        if low <= score <= high:
            return grade
    return "N/A"


def _weighted_current_score(records: list[dict], weightages: dict) -> tuple[float, int]:
    """Weighted average across recorded categories, re-normalized to only the
    categories that actually have data (so a missing final exam doesn't drag
    the score down before it happens)."""
    by_category: dict[str, list[float]] = {}
    for r in records:
        by_category.setdefault(r["category"], []).append(r["score_pct"])

    if not by_category:
        return 0.0, 0

    used_weight_total = sum(weightages.get(cat, 0) for cat in by_category) or 1
    weighted_sum = 0.0
    for cat, scores in by_category.items():
        avg = statistics.mean(scores)
        weighted_sum += avg * (weightages.get(cat, 0) / used_weight_total)

    return round(weighted_sum, 1), len(records)


def _trend_projection(records: list[dict]) -> tuple[float, str, list[dict]]:
    """Simple linear trend over the chronological score sequence to project
    a final score, plus a qualitative trend label."""
    ordered = sorted(records, key=lambda r: r["date"])
    scores = [r["score_pct"] for r in ordered]
    history_points = [{"label": r["label"], "score": r["score_pct"]} for r in ordered]

    if len(scores) < 2:
        projected = scores[0] if scores else 0.0
        return projected, "stable", history_points

    # Simple linear regression, x = index
    n = len(scores)
    xs = list(range(n))
    x_mean = statistics.mean(xs)
    y_mean = statistics.mean(scores)
    numerator = sum((x - x_mean) * (y - y_mean) for x, y in zip(xs, scores))
    denominator = sum((x - x_mean) ** 2 for x in xs) or 1
    slope = numerator / denominator
    intercept = y_mean - slope * x_mean

    projected = intercept + slope * n  # project one step past the last data point
    projected = max(0.0, min(100.0, round(projected, 1)))

    if slope > 2:
        trend = "rapidly_improving"
    elif slope > 0.3:
        trend = "improving"
    elif slope > -0.3:
        trend = "stable"
    elif slope > -2:
        trend = "declining"
    else:
        trend = "high_risk"

    return projected, trend, history_points


def _confidence(assessment_count: int, thresholds: dict) -> tuple[str, float]:
    high_min = thresholds.get("high", 5)
    med_min = thresholds.get("medium", 3)
    if assessment_count >= high_min:
        pct = min(97, 70 + (assessment_count - high_min) * 3)
        return "high", float(pct)
    if assessment_count >= med_min:
        pct = 50 + (assessment_count - med_min) * 8
        return "medium", float(pct)
    pct = 20 + assessment_count * 10
    return "low", float(pct)


def _risk_level(predicted_score: float, thresholds: dict) -> str:
    if predicted_score >= thresholds.get("low", 70):
        return "low"
    if predicted_score >= thresholds.get("moderate", 60):
        return "moderate"
    if predicted_score >= thresholds.get("high", 50):
        return "high"
    return "critical"


def _grade_probability(predicted_score: float, grading_scale: dict, confidence_pct: float) -> dict:
    """Spread probability mass around the predicted score using a normal-ish
    distribution narrowed by confidence — narrow spread when confidence is
    high, wide spread when it's low."""
    spread = max(2.0, 12.0 - (confidence_pct / 10))  # std-dev proxy in points
    probs = {}
    total = 0.0
    for grade, (low, high) in grading_scale.items():
        mid = (low + high) / 2
        # crude gaussian-like weight based on distance from predicted score
        distance = abs(mid - predicted_score)
        weight = max(0.0, 1 - (distance / (spread * 2.5)))
        probs[grade] = weight
        total += weight
    if total == 0:
        return {score_to_grade(predicted_score, grading_scale): 100}
    return {g: round((w / total) * 100) for g, w in probs.items() if w > 0}


def _explain(records: list[dict], trend: str) -> dict:
    by_category: dict[str, list[float]] = {}
    for r in records:
        by_category.setdefault(r["category"], []).append(r["score_pct"])

    explanation = {}
    for cat, scores in by_category.items():
        avg = statistics.mean(scores)
        label = cat.replace("_", " ").title()
        if avg >= 85:
            explanation[label] = "Strong"
        elif avg >= 70:
            explanation[label] = "Improving" if trend in ("improving", "rapidly_improving") else "Average"
        else:
            explanation[label] = "Needs improvement"
    return explanation


# ExamPlan.exam_type -> weightage category used above
EXAM_TYPE_TO_CATEGORY = {
    "WEEKLY": "quiz",
    "MONTHLY": "class_test",
    "MIDTERM": "midterm",
    "FINAL": "final_exam",
}


def get_assessment_records(student, subject) -> list[dict]:
    """
    Pulls every compiled result this student has for this subject, across
    all exam plans (weekly/monthly/midterm/final), from your real
    exam_system chain:

        CentralizedResult -> AnswerSheet -> ExamSchedule -> (subject, ExamPlan.exam_type)
    """
    from exam_system.models import CentralizedResult

    qs = (
        CentralizedResult.objects.filter(
            answer_sheet__student=student,
            answer_sheet__schedule__subject=subject,
        )
        .select_related(
            "answer_sheet__schedule__exam_plan",
            "answer_sheet__schedule__subject",
        )
        .order_by("compiled_at")
    )

    records = []
    for result in qs:
        schedule = result.answer_sheet.schedule
        exam_plan = schedule.exam_plan
        category = EXAM_TYPE_TO_CATEGORY.get(exam_plan.exam_type, "class_test")
        records.append(
            {
                "category": category,
                "score_pct": float(result.percentage),
                "label": f"{exam_plan.title} ({exam_plan.get_exam_type_display()})",
                "date": schedule.exam_date or result.compiled_at.date(),
            }
        )
    return records


def predict_for_student_subject(student, subject, class_room=None) -> PredictionResult:
    config = get_config()
    grading_scale = config.grading_scale or DEFAULT_GRADING_SCALE
    weightages = config.assessment_weightages or DEFAULT_WEIGHTAGES
    risk_thresholds = config.risk_thresholds or DEFAULT_RISK_THRESHOLDS
    confidence_thresholds = config.confidence_thresholds or DEFAULT_CONFIDENCE_THRESHOLDS

    records = get_assessment_records(student, subject)

    current_score, count = _weighted_current_score(records, weightages)
    projected, trend, history_points = _trend_projection(records)

    # Blend weighted-current and trend-projection so one bad/good outlier
    # assessment doesn't swing the prediction too hard.
    predicted_score = round((current_score * 0.6) + (projected * 0.4), 1)

    confidence_level, confidence_pct = _confidence(count, confidence_thresholds)

    margin = max(2.0, 12 - (confidence_pct / 10))
    predicted_range = (
        max(0.0, round(predicted_score - margin, 1)),
        min(100.0, round(predicted_score + margin, 1)),
    )

    predicted_grade = score_to_grade(predicted_score, grading_scale)
    grade_probability = _grade_probability(predicted_score, grading_scale, confidence_pct)
    risk_level = _risk_level(predicted_score, risk_thresholds)
    explanation = _explain(records, trend)

    if count < config.minimum_data_requirement:
        confidence_level = "low"

    return PredictionResult(
        current_score=current_score,
        predicted_score=predicted_score,
        predicted_range=predicted_range,
        predicted_grade=predicted_grade,
        grade_probability=grade_probability,
        confidence_level=confidence_level,
        confidence_pct=confidence_pct,
        trend=trend,
        risk_level=risk_level,
        assessments_used=count,
        explanation=explanation,
        history_points=history_points,
    )


def save_prediction(student, subject, class_room=None) -> StudentGradePrediction:
    """Runs the engine and upserts the cached StudentGradePrediction row,
    logging a history point. Call this from a signal / management command
    whenever new assessment data lands (see section 11's 'Continuous
    Recalculation' requirement)."""
    result = predict_for_student_subject(student, subject, class_room)

    obj, _ = StudentGradePrediction.objects.update_or_create(
        student=student, subject=subject,
        defaults={
            "class_room": class_room,
            "current_score": result.current_score,
            "predicted_score": result.predicted_score,
            "predicted_score_low": result.predicted_range[0],
            "predicted_score_high": result.predicted_range[1],
            "predicted_grade": result.predicted_grade,
            "grade_probability": result.grade_probability,
            "confidence_level": result.confidence_level,
            "confidence_pct": result.confidence_pct,
            "trend": result.trend,
            "risk_level": result.risk_level,
            "assessments_used": result.assessments_used,
            "explanation": result.explanation,
            "last_calculated": timezone.now(),
        },
    )

    if result.history_points:
        last_point = result.history_points[-1]
        PredictionHistory.objects.create(
            prediction=obj, label=last_point["label"], score=last_point["score"]
        )

    return obj


def required_score_for_target(current_weighted_score: float, remaining_weight_pct: float,
                               target_grade: str, grading_scale: dict) -> Optional[float]:
    """Section 7 — 'What Do I Need?' calculator.
    current_weighted_score is on a 0-100 scale already earned (weighted).
    remaining_weight_pct is how much weight is still un-assessed (e.g. 20 for
    a final exam worth 20%). Returns the % needed on the remaining portion,
    or None if the target isn't mathematically reachable."""
    if target_grade not in grading_scale:
        return None
    target_low, _ = grading_scale[target_grade]
    if remaining_weight_pct <= 0:
        return None if current_weighted_score < target_low else 0.0

    needed = (target_low - current_weighted_score) / (remaining_weight_pct / 100)
    if needed > 100:
        return None  # not achievable
    return round(max(0.0, needed), 1)

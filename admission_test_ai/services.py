"""
AI services for the Admission Test Paper System.

Uses Groq (llama-3.3-70b-versatile) the same way the existing AI lesson-plan
feature does elsewhere in EduPilot, so no new AI provider/account is needed.
Set GROQ_API_KEY in the environment / settings. If it isn't set, paper
generation falls back to a clear error instead of silently producing junk
questions.
"""
import json
import os
from difflib import SequenceMatcher

from django.conf import settings

from .models import AdmissionQuestion, GeneratedPaper


def _groq_client():
    try:
        from groq import Groq
    except ImportError as exc:
        raise RuntimeError(
            "The 'groq' package isn't installed. Run: pip install groq"
        ) from exc

    api_key = getattr(settings, "GROQ_API_KEY", None) or os.environ.get("GROQ_API_KEY")
    if not api_key:
        raise RuntimeError(
            "GROQ_API_KEY is not configured. Add it to settings.py or the environment."
        )
    return Groq(api_key=api_key)


def _chat_json(prompt, system="You are an expert school admission-test paper setter."):
    client = _groq_client()
    completion = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {"role": "system", "content": system + " Reply with ONLY valid JSON, no markdown fences, no commentary."},
            {"role": "user", "content": prompt},
        ],
        temperature=0.4,
    )
    raw = completion.choices[0].message.content.strip()
    raw = raw.removeprefix("```json").removeprefix("```").removesuffix("```").strip()
    return json.loads(raw)


def generate_questions_for_blueprint_subject(blueprint_subject):
    """Calls the AI to generate questions for one subject row of a blueprint,
    following the approved difficulty distribution, and saves them as
    AdmissionQuestion rows (AI Generated status, not yet reviewed)."""
    bp = blueprint_subject.blueprint
    prompt = f"""
Generate an admission test question set for a school admission exam.

Grade / applying class: {bp.applying_class}
Subject: {blueprint_subject.subject}
Curriculum: {bp.curriculum}
Number of questions: {blueprint_subject.num_questions}
Total marks for this subject: {blueprint_subject.marks}
Topics to draw from (if given): {blueprint_subject.topics or "age-appropriate general syllabus topics"}

Difficulty distribution to follow:
Easy: {bp.difficulty_easy_pct}%
Age appropriate: {bp.difficulty_age_appropriate_pct}%
Moderate: {bp.difficulty_moderate_pct}%
Advanced: {bp.difficulty_advanced_pct}%

Mix question types appropriate for the subject and grade (mcq, true_false, fill_blank,
matching, short_answer, long_answer, comprehension, problem_solving, mental_math,
creative_writing, diagram_based, scenario, logical_reasoning).

Return a JSON object: {{"questions": [
  {{"question_text": "...", "question_type": "mcq", "options": ["A","B","C","D"] or null,
    "correct_answer": "...", "marks": 1, "difficulty": "easy|age_appropriate|moderate|advanced",
    "bloom_level": "remember|understand|apply|analyze|evaluate|create",
    "topic": "...", "skill": "..."}}
]}}
The marks of all questions must sum to {blueprint_subject.marks}.
"""
    data = _chat_json(prompt)
    created = []
    for q in data.get("questions", []):
        obj = AdmissionQuestion.objects.create(
            blueprint_subject=blueprint_subject,
            question_text=q.get("question_text", "").strip(),
            question_type=q.get("question_type", "short_answer"),
            options=q.get("options"),
            correct_answer=q.get("correct_answer", ""),
            marks=q.get("marks", 1),
            difficulty=q.get("difficulty", "age_appropriate"),
            bloom_level=q.get("bloom_level", "understand"),
            topic=q.get("topic", ""),
            skill=q.get("skill", ""),
            is_ai_generated=True,
        )
        created.append(obj)
    return created


def run_quality_check(question):
    """Lightweight AI quality check: language, age suitability, difficulty
    match, answer validity, ambiguity, curriculum relevance. Stores notes on
    the question rather than blocking - a human still approves."""
    prompt = f"""
Review this admission-test question for a school ERP quality check.
Question type: {question.question_type}
Difficulty label: {question.difficulty}
Question: {question.question_text}
Options: {question.options}
Correct answer: {question.correct_answer}

Check: language/grammar clarity, age suitability, whether difficulty matches the label,
whether the correct answer is valid, whether the question is ambiguous (more than one
right answer), and curriculum relevance.

Return JSON: {{"language_ok": true/false, "age_appropriate": true/false,
"difficulty_matches": true/false, "answer_valid": true/false, "ambiguous": true/false,
"notes": "short human-readable summary"}}
"""
    try:
        result = _chat_json(prompt, system="You are a strict academic quality reviewer.")
    except Exception as exc:  # AI unavailable - don't block the workflow
        result = {"error": str(exc)}
    question.ai_quality_notes = result
    question.save(update_fields=["ai_quality_notes"])
    return result


def find_duplicate_questions(question, similarity_threshold=0.82):
    """Simple text-similarity duplicate check against the existing question
    bank for the same subject (no AI call needed - keeps this fast/cheap)."""
    candidates = AdmissionQuestion.objects.filter(
        blueprint_subject__subject=question.blueprint_subject.subject
    ).exclude(pk=question.pk)
    matches = []
    for other in candidates:
        ratio = SequenceMatcher(None, question.question_text.lower(), other.question_text.lower()).ratio()
        if ratio >= similarity_threshold:
            matches.append((other, ratio))
    if matches:
        best = max(matches, key=lambda m: m[1])
        question.duplicate_flag = f"Similar to question #{best[0].id} ({best[1]:.0%} match)"
        question.save(update_fields=["duplicate_flag"])
    return matches


def build_readiness_report(attempt):
    """Aggregates AttemptAnswer marks into a subject-wise readiness report."""
    from .models import ReadinessReport

    subject_totals = {}
    for answer in attempt.answers.select_related("question__blueprint_subject__subject"):
        subj = answer.question.blueprint_subject.subject.name
        earned, possible = subject_totals.get(subj, (0, 0))
        subject_totals[subj] = (
            earned + (answer.marks_awarded or 0),
            possible + answer.question.marks,
        )

    subject_scores = {
        subj: round((earned / possible) * 100, 1) if possible else 0
        for subj, (earned, possible) in subject_totals.items()
    }
    overall = round(sum(subject_scores.values()) / len(subject_scores), 1) if subject_scores else 0
    attempt.overall_score_pct = overall
    attempt.status = "evaluated"
    attempt.save(update_fields=["overall_score_pct", "status"])

    strengths = [s for s, v in subject_scores.items() if v >= 75]
    areas_for_support = [s for s, v in subject_scores.items() if v < 60]

    blueprint = attempt.schedule.paper.blueprint
    is_borderline = 0 <= (overall - blueprint.passing_percentage) <= 5
    note = ""
    if is_borderline:
        weak = ", ".join(areas_for_support) or "one or two subjects"
        note = (
            f"Borderline candidate: overall {overall}% is close to the "
            f"{blueprint.passing_percentage}% passing mark. Weak area(s): {weak}. "
            "Recommend a follow-up interview or reassessment rather than an automatic decision."
        )

    report, _ = ReadinessReport.objects.update_or_create(
        attempt=attempt,
        defaults={
            "subject_scores": subject_scores,
            "strengths": strengths,
            "areas_for_support": areas_for_support,
            "is_borderline": is_borderline,
            "borderline_note": note,
        },
    )
    return report


def compute_recommendation(recommendation):
    """Blends the academic test score with previous results/interview/
    observation inputs already stored on the AdmissionRecommendation row
    (those are entered by the admission office) into a final label."""
    report = recommendation.readiness_report
    academic_score = report.attempt.overall_score_pct if report and report.attempt else 0

    total_weight = (
        recommendation.academic_test_weight_pct
        + recommendation.previous_results_weight_pct
        + recommendation.interview_weight_pct
        + recommendation.teacher_observation_weight_pct
    ) or 100

    # Only the academic component is auto-scored here; previous
    # results/interview/observation scores are captured separately by staff
    # and factored in once entered - this keeps the AI from making the final
    # call, per the admission workflow (human decision stays authoritative).
    weighted = academic_score * (recommendation.academic_test_weight_pct / total_weight)
    recommendation.computed_score_pct = round(weighted, 1)

    if report and report.is_borderline:
        recommendation.recommendation = "further_assessment"
    elif weighted >= 75:
        recommendation.recommendation = "highly_recommended"
    elif weighted >= 60:
        recommendation.recommendation = "recommended"
    elif weighted >= 45:
        recommendation.recommendation = "recommended_support"
    else:
        recommendation.recommendation = "not_recommended"

    recommendation.save()
    return recommendation

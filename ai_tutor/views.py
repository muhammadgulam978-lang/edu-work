import json

from django.contrib.auth.decorators import login_required
from django.db.models import Avg
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from admin_panel.models import Subject
from student_profile.models import Student
from teacher_dashboard.models import Assignment, Quiz

from .models import AITutorSession, AIPracticeAttempt, StudentTopicMastery
from .services import (
    create_sample_practice_attempt,
    evaluate_practice_answer,
    get_or_create_preferences,
    handle_student_message,
)


def _student_from_request(request):
    return get_object_or_404(Student, user=request.user)


def _student_subjects(student):
    queryset = Subject.objects.none()
    if student.class_fk_id:
        queryset = Subject.objects.filter(class_fk=student.class_fk).order_by("sort_order", "name")
    return queryset


def _student_scope_filter(student):
    filters = {}
    if student.class_fk_id:
        filters["class_fk"] = student.class_fk
    if student.section_id:
        filters["section"] = student.section
    return filters


def _latest_topic(latest_session):
    if latest_session and latest_session.topic:
        return latest_session.topic
    return "today's lesson"


@login_required
def dashboard(request):
    student = _student_from_request(request)
    subjects = _student_subjects(student)
    sessions = AITutorSession.objects.filter(student=student).select_related("subject")[:6]
    latest_session = sessions[0] if sessions else None
    mastery = StudentTopicMastery.objects.filter(student=student).select_related("subject")
    weak_topics = mastery.filter(mastery_level__in=["needs_revision", "developing"]).order_by("accuracy_percentage", "-last_practiced_at")[:5]
    preference = get_or_create_preferences(student)
    scope = _student_scope_filter(student)
    assignments = Assignment.objects.filter(**scope).select_related("subject").order_by("due_date")[:4] if scope else Assignment.objects.none()
    quizzes = Quiz.objects.filter(**scope).select_related("subject").order_by("due_date")[:4] if scope else Quiz.objects.none()
    first_subject = subjects.first()

    recommendation_cards = []
    for item in weak_topics[:2]:
        recommendation_cards.append(
            {
                "label": "Revise" if item.mastery_level == "needs_revision" else "Practice",
                "title": item.topic,
                "meta": "20 min" if item.mastery_level == "needs_revision" else "15 min",
                "session_type": "revise" if item.mastery_level == "needs_revision" else "practice",
                "subject_id": item.subject_id,
                "tone": "teal",
            }
        )
    for assignment in assignments[:1]:
        recommendation_cards.append(
            {
                "label": "Complete",
                "title": assignment.title,
                "meta": f"Due {assignment.due_date:%d %b}",
                "session_type": "homework_help",
                "subject_id": assignment.subject_id,
                "tone": "green",
            }
        )
    if latest_session:
        recommendation_cards.append(
            {
                "label": "Read",
                "title": _latest_topic(latest_session),
                "meta": "15 min",
                "session_type": "learn",
                "subject_id": latest_session.subject_id or (first_subject.id if first_subject else ""),
                "tone": "navy",
            }
        )
    fallback_cards = [
        {"label": "Revise", "title": "Linear Equations", "meta": "20 min", "session_type": "revise", "tone": "teal"},
        {"label": "Practice", "title": "Fractions", "meta": "15 min", "session_type": "practice", "tone": "green"},
        {"label": "Vocabulary", "title": "10 New Words", "meta": "10 min", "session_type": "learn", "tone": "navy"},
        {"label": "Read", "title": "Photosynthesis", "meta": "15 min", "session_type": "learn", "tone": "teal"},
    ]
    for card in fallback_cards:
        if len(recommendation_cards) >= 5:
            break
        card = card.copy()
        card["subject_id"] = card.get("subject_id") or (first_subject.id if first_subject else "")
        recommendation_cards.append(card)

    return render(
        request,
        "ai_tutor/dashboard.html",
        {
            "student": student,
            "subjects": subjects,
            "sessions": sessions,
            "latest_session": latest_session,
            "weak_topics": weak_topics,
            "preference": preference,
            "assignments": assignments,
            "quizzes": quizzes,
            "recommendation_cards": recommendation_cards,
            "current_hour": timezone.localtime().hour,
        },
    )


@login_required
@require_POST
def start_session(request):
    student = _student_from_request(request)
    payload = _payload(request)
    subject_id = payload.get("subject_id") or request.POST.get("subject_id")
    topic = (payload.get("topic") or request.POST.get("topic", "")).strip()
    session_type = payload.get("session_type") or request.POST.get("session_type", "learn")
    language = payload.get("language") or request.POST.get("language", "English")

    subject = None
    if subject_id:
        subject = get_object_or_404(_student_subjects(student), id=subject_id)

    session = AITutorSession.objects.create(
        student=student,
        subject=subject,
        topic=topic,
        session_type=session_type,
        language=language,
    )

    if request.headers.get("x-requested-with") == "XMLHttpRequest":
        return JsonResponse({"session_id": session.id, "redirect": session.get_absolute_url() if hasattr(session, "get_absolute_url") else ""})

    return redirect("ai_tutor_chat", session_id=session.id)


@login_required
def chat(request, session_id):
    student = _student_from_request(request)
    session = get_object_or_404(
        AITutorSession.objects.select_related("subject"),
        id=session_id,
        student=student,
    )
    messages = session.messages.all()
    practice_attempts = session.practice_attempts.all()[:5]

    return render(
        request,
        "ai_tutor/chat.html",
        {
            "student": student,
            "session": session,
            "messages": messages,
            "practice_attempts": practice_attempts,
        },
    )


@login_required
@require_POST
def send_message(request, session_id):
    student = _student_from_request(request)
    session = get_object_or_404(AITutorSession, id=session_id, student=student)
    payload = _payload(request)
    message = (payload.get("message") or request.POST.get("message") or "").strip()

    if not message:
        return JsonResponse({"error": "Message is required."}, status=400)

    result = handle_student_message(session=session, student=student, message=message)
    result["session_id"] = session.id
    return JsonResponse(result)


@login_required
@require_POST
def create_practice(request, session_id):
    student = _student_from_request(request)
    session = get_object_or_404(AITutorSession, id=session_id, student=student)
    attempt = create_sample_practice_attempt(session=session, student=student)
    return JsonResponse(
        {
            "attempt_id": attempt.id,
            "question": attempt.question_text,
            "topic": attempt.topic,
        }
    )


@login_required
@require_POST
def answer_practice(request, attempt_id):
    student = _student_from_request(request)
    attempt = get_object_or_404(AIPracticeAttempt, id=attempt_id, student=student)
    payload = _payload(request)
    answer = (payload.get("answer") or request.POST.get("answer") or "").strip()

    if not answer:
        return JsonResponse({"error": "Answer is required."}, status=400)

    return JsonResponse(evaluate_practice_answer(attempt=attempt, student=student, answer=answer))


@login_required
def progress(request):
    student = _student_from_request(request)
    mastery = StudentTopicMastery.objects.filter(student=student).select_related("subject")
    weak_topics = mastery.filter(mastery_level__in=["needs_revision", "developing"]).order_by("accuracy_percentage", "-last_practiced_at")
    mastered_topics = mastery.filter(mastery_level="mastered")
    attempts = AIPracticeAttempt.objects.filter(student=student).select_related("subject", "session")
    answered_attempts = attempts.exclude(score__isnull=True)
    average_score = answered_attempts.aggregate(value=Avg("score"))["value"] or 0
    recommended_actions = mastery.exclude(recommended_action="")[:8]

    if request.headers.get("accept") == "application/json":
        return JsonResponse(
            {
                "summary": {
                    "tracked_topics": mastery.count(),
                    "weak_topics": weak_topics.count(),
                    "mastered_topics": mastered_topics.count(),
                    "questions_solved": answered_attempts.count(),
                    "average_accuracy": round(average_score),
                },
                "mastery": [
                    {
                        "subject": item.subject.name,
                        "topic": item.topic,
                        "mastery_level": item.mastery_level,
                        "accuracy_percentage": item.accuracy_percentage,
                        "attempts": item.attempts,
                        "recommended_action": item.recommended_action,
                    }
                    for item in mastery
                ]
            }
        )

    return render(
        request,
        "ai_tutor/progress.html",
        {
            "student": student,
            "mastery": mastery,
            "weak_topics": weak_topics,
            "mastered_topics": mastered_topics,
            "attempts": attempts[:20],
            "questions_solved": answered_attempts.count(),
            "average_accuracy": round(average_score),
            "recommended_actions": recommended_actions,
        },
    )


@login_required
@require_POST
def study_plan(request):
    student = _student_from_request(request)
    minutes = int(request.POST.get("available_minutes_per_day", 60) or 60)
    days = int(request.POST.get("plan_duration_days", 7) or 7)
    weak_topics = StudentTopicMastery.objects.filter(
        student=student,
        mastery_level__in=["needs_revision", "developing", "introduced"],
    ).select_related("subject")[:days]
    plan = []
    for index in range(days):
        topic = weak_topics[index] if index < len(weak_topics) else None
        plan.append(
            {
                "day": index + 1,
                "minutes": minutes,
                "task": (
                    f"{topic.subject.name}: revise {topic.topic} and answer 3 practice questions"
                    if topic
                    else "Review today's class notes and save one question for AI Tutor"
                ),
            }
        )
    return JsonResponse({"plan": plan})


@login_required
def sessions(request):
    student = _student_from_request(request)
    subjects = _student_subjects(student)
    session_list = AITutorSession.objects.filter(student=student).select_related("subject")

    subject_id = request.GET.get("subject_id")
    session_type = request.GET.get("session_type")
    language = request.GET.get("language")
    status = request.GET.get("status")

    if subject_id:
        session_list = session_list.filter(subject_id=subject_id)
    if session_type:
        session_list = session_list.filter(session_type=session_type)
    if language:
        session_list = session_list.filter(language=language)
    if status:
        session_list = session_list.filter(status=status)

    all_sessions = AITutorSession.objects.filter(student=student)
    latest_session = all_sessions.select_related("subject").first()
    total_messages = sum(all_sessions.values_list("total_messages", flat=True))

    return render(
        request,
        "ai_tutor/sessions.html",
        {
            "student": student,
            "sessions": session_list,
            "subjects": subjects,
            "session_types": AITutorSession.SESSION_TYPES,
            "statuses": AITutorSession.STATUS_CHOICES,
            "selected_subject_id": subject_id or "",
            "selected_session_type": session_type or "",
            "selected_language": language or "",
            "selected_status": status or "",
            "total_sessions": all_sessions.count(),
            "active_sessions": all_sessions.filter(status="active").count(),
            "closed_sessions": all_sessions.filter(status="closed").count(),
            "total_messages": total_messages,
            "latest_session": latest_session,
        },
    )


def _payload(request):
    if request.content_type and "application/json" in request.content_type:
        try:
            return json.loads(request.body.decode("utf-8"))
        except json.JSONDecodeError:
            return {}
    return {}

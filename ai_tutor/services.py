from django.conf import settings
from django.db import transaction
from django.utils import timezone

from .llm import generate_ai_tutor_response
from .models import (
    AIAuditLog,
    AIPracticeAttempt,
    AITutorMessage,
    StudentAIPreference,
    StudentTopicMastery,
)
from .prompts import build_system_prompt, build_user_prompt, classify_intent
from .rag import retrieve_documents
from .safety import classify_query_safety, validate_response_safety


def get_or_create_preferences(student):
    preference, _ = StudentAIPreference.objects.get_or_create(student=student)
    return preference


def get_progress_summary(student, subject=None):
    queryset = StudentTopicMastery.objects.filter(student=student)
    if subject:
        queryset = queryset.filter(subject=subject)
    weak = queryset.filter(mastery_level__in=["needs_revision", "developing"])[:5]
    mastered = queryset.filter(mastery_level="mastered")[:5]
    weak_text = ", ".join(item.topic for item in weak) or "None recorded"
    mastered_text = ", ".join(item.topic for item in mastered) or "None recorded"
    return f"Weak/developing topics: {weak_text}. Mastered topics: {mastered_text}."


def handle_student_message(*, session, student, message):
    subject = session.subject
    safety = classify_query_safety(message, session.session_type)
    intent = "restricted_request" if safety["status"] == "blocked" else classify_intent(message, session.session_type)

    if safety["status"] == "blocked":
        with transaction.atomic():
            AITutorMessage.objects.create(
                session=session,
                student=student,
                sender_type="student",
                message_text=message,
                intent=intent,
                safety_status="blocked",
            )
            assistant_message = AITutorMessage.objects.create(
                session=session,
                student=student,
                sender_type="assistant",
                response_text=safety["message"],
                intent=intent,
                model_name=getattr(settings, "AI_TUTOR_MODEL", "gpt-5.6-terra"),
                safety_status="blocked",
            )
            _increment_session(session, 2, 0)
            AIAuditLog.objects.create(
                student=student,
                session=session,
                action_type="message_blocked",
                model_used=getattr(settings, "AI_TUTOR_MODEL", "gpt-5.6-terra"),
                safety_flags=safety["flags"],
                access_result="blocked",
            )
        return {
            "reply": assistant_message.response_text,
            "intent": intent,
            "safety_status": "blocked",
            "sources": [],
            "model": assistant_message.model_name,
        }

    documents = retrieve_documents(student=student, subject=subject, query=f"{session.topic} {message}")
    preference = get_or_create_preferences(student)
    progress_summary = get_progress_summary(student, subject)
    system_prompt = build_system_prompt(student=student, subject=subject, session=session, preference=preference)
    user_prompt = build_user_prompt(
        message=message,
        intent=intent,
        context_documents=documents,
        progress_summary=progress_summary,
    )
    model_name = getattr(settings, "AI_TUTOR_MODEL", "gpt-5.6-terra")
    result = generate_ai_tutor_response(
        model=model_name,
        system_prompt=system_prompt,
        user_prompt=user_prompt,
        context_documents=documents,
        response_format="text",
    )
    response_safety = validate_response_safety(result.text)
    safety_status = "error" if result.error else response_safety["status"]

    with transaction.atomic():
        AITutorMessage.objects.create(
            session=session,
            student=student,
            sender_type="student",
            message_text=message,
            intent=intent,
            safety_status="allowed",
        )
        AITutorMessage.objects.create(
            session=session,
            student=student,
            sender_type="assistant",
            response_text=result.text,
            intent=intent,
            model_name=result.model,
            safety_status=safety_status,
        )
        _increment_session(session, 2, result.token_count)
        _update_mastery_from_intent(student, subject, session.topic, intent)
        AIAuditLog.objects.create(
            student=student,
            session=session,
            action_type="message_response",
            model_used=result.model,
            retrieved_document_ids=[doc.id for doc in documents],
            safety_flags=response_safety["flags"] + ([result.error] if result.error else []),
            access_result=safety_status,
            metadata={"intent": intent},
        )

    return {
        "reply": result.text,
        "intent": intent,
        "safety_status": safety_status,
        "sources": [{"id": doc.id, "title": doc.title, "source": doc.source_reference} for doc in documents],
        "model": result.model,
    }


def evaluate_practice_answer(*, attempt, student, answer):
    expected = (attempt.expected_answer or "").lower()
    submitted = (answer or "").lower()
    expected_terms = [term for term in expected.replace(".", " ").replace(",", " ").split() if len(term) > 3]
    matched = sum(1 for term in expected_terms if term in submitted)
    score = round((matched / max(len(expected_terms), 1)) * 100, 2)
    is_correct = score >= 60
    feedback = (
        "Good work. Your answer includes the key idea. Try adding one supporting detail."
        if is_correct
        else "You are close. Review the key concept and try again with the main terms from the lesson."
    )

    attempt.student_answer = answer
    attempt.score = score
    attempt.is_correct = is_correct
    attempt.feedback = feedback
    attempt.answered_at = timezone.now()
    attempt.save(update_fields=["student_answer", "score", "is_correct", "feedback", "answered_at"])

    if attempt.subject and attempt.topic:
        mastery, _ = StudentTopicMastery.objects.get_or_create(
            student=student,
            subject=attempt.subject,
            topic=attempt.topic,
        )
        previous_total = mastery.accuracy_percentage * mastery.attempts
        mastery.attempts += 1
        mastery.accuracy_percentage = round((previous_total + score) / mastery.attempts, 2)
        mastery.last_practiced_at = timezone.now()
        mastery.mastery_level = "mastered" if mastery.accuracy_percentage >= 80 else "practicing" if mastery.accuracy_percentage >= 50 else "needs_revision"
        mastery.recommended_action = "Continue with harder practice." if is_correct else "Revise the topic and try foundation questions."
        mastery.save()

    AIAuditLog.objects.create(
        student=student,
        session=attempt.session,
        action_type="practice_answer",
        access_result="allowed",
        metadata={"attempt_id": attempt.id, "score": score},
    )

    return {"is_correct": is_correct, "score": score, "feedback": feedback}


def create_sample_practice_attempt(*, session, student):
    question = f"Write one key point about {session.topic or session.subject or 'this topic'}."
    expected = f"A correct answer should explain the main idea of {session.topic or 'the selected topic'} using subject vocabulary."
    return AIPracticeAttempt.objects.create(
        student=student,
        session=session,
        subject=session.subject,
        topic=session.topic,
        question_text=question,
        expected_answer=expected,
        expected_concepts=[session.topic] if session.topic else [],
    )


def _increment_session(session, messages, tokens):
    session.total_messages += messages
    session.total_tokens += tokens or 0
    session.save(update_fields=["total_messages", "total_tokens"])


def _update_mastery_from_intent(student, subject, topic, intent):
    if not subject or not topic or intent not in {"explain_concept", "summarize_lesson", "translate_explanation"}:
        return
    mastery, created = StudentTopicMastery.objects.get_or_create(
        student=student,
        subject=subject,
        topic=topic,
        defaults={"mastery_level": "introduced", "recommended_action": "Answer the checking question to continue."},
    )
    if not created and mastery.mastery_level == "not_started":
        mastery.mastery_level = "introduced"
        mastery.recommended_action = "Practice this topic next."
        mastery.save(update_fields=["mastery_level", "recommended_action"])

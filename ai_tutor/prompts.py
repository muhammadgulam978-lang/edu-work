def classify_intent(message, session_type="learn"):
    text = (message or "").lower()

    if session_type == "homework_help" or "homework" in text or "assignment" in text:
        return "homework_guidance"
    if session_type == "exam_prep" or "exam" in text or "test" in text:
        return "exam_preparation"
    if "practice" in text or "questions" in text or "quiz me" in text or "test me" in text:
        return "generate_practice"
    if "check" in text or "my answer" in text or "is this correct" in text:
        return "check_answer"
    if "plan" in text or "schedule" in text:
        return "study_planning"
    if "urdu" in text or "translate" in text:
        return "translate_explanation"
    if "progress" in text or "weak" in text or "mastered" in text:
        return "progress_inquiry"
    if "summarize" in text or "summary" in text:
        return "summarize_lesson"
    return "explain_concept"


def build_system_prompt(*, student, subject, session, preference):
    class_name = student.class_fk.class_name if student.class_fk else "Unknown class"
    section_name = student.section.section_name if student.section else "Unknown section"
    subject_name = subject.name if subject else "General"
    style = preference.explanation_style if preference else "simple"

    return f"""You are EduPilot AI Tutor for the authenticated student.
Use only approved school curriculum context when available.
Do not reveal information about any other student.
Do not complete prohibited graded work.
Explain at the student's class level.
Ask one checking question after explanations.

Student academic context:
Class: {class_name}
Section: {section_name}
Subject: {subject_name}
Topic: {session.topic or "General"}
Preferred language: {session.language}
Explanation style: {style}
Learning mode: {session.session_type}
"""


def build_user_prompt(*, message, intent, context_documents, progress_summary):
    context = "\n\n".join(
        f"Source: {doc.title}\n{doc.content[:1800]}" for doc in context_documents
    )
    if not context:
        context = "No approved curriculum context was found for this exact query. Stay general, age-appropriate, and avoid inventing school-specific curriculum requirements."

    return f"""Student intent: {intent}

Approved context:
{context}

Student progress summary:
{progress_summary or "No prior AI Tutor progress recorded."}

Student message:
{message}

Respond with:
1. A helpful answer
2. A simple example when useful
3. Key points
4. One checking question or next action
"""


def build_feedback_prompt(*, question, student_answer, expected_answer, expected_concepts):
    return f"""Evaluate the student's answer.

Question:
{question}

Student answer:
{student_answer}

Expected answer:
{expected_answer}

Expected concepts:
{", ".join(expected_concepts or [])}

Provide:
1. What is correct
2. What needs improvement
3. One hint
4. Whether another attempt is recommended

Do not reveal the complete answer on the first attempt unless it is necessary for learning."""

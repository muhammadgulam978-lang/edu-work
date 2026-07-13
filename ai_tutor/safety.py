import re


OTHER_STUDENT_PATTERNS = [
    r"\b(other|another)\s+student\b",
    r"\b(classmate|friend)\b.*\b(mark|grade|attendance|result|record)\b",
    r"\bshow\s+me\b.*\b(mark|grade|attendance|result|record)\b",
    r"\b[a-zA-Z]+\s+(marks|grades|attendance|result)\b",
]

EXAM_RESTRICTED_PATTERNS = [
    r"\b(live|active|current)\s+(exam|quiz|test)\b",
    r"\banswer(s)?\s+for\s+(the\s+)?(exam|quiz|test)\b",
    r"\bsolve\s+(my|the)\s+(exam|quiz|test)\b",
]

HOMEWORK_COMPLETION_PATTERNS = [
    r"\bwrite\s+(my|the)\s+(essay|assignment|homework)\b",
    r"\bcomplete\s+(my|the)\s+(assignment|homework|project)\b",
    r"\bdo\s+(my|the)\s+(assignment|homework)\b",
]


def _matches_any(text, patterns):
    return any(re.search(pattern, text, flags=re.IGNORECASE) for pattern in patterns)


def detect_other_student_data_request(message):
    return _matches_any(message or "", OTHER_STUDENT_PATTERNS)


def is_exam_restricted(message):
    return _matches_any(message or "", EXAM_RESTRICTED_PATTERNS)


def is_homework_allowed(message, session_type="learn"):
    if session_type != "homework_help":
        return True
    return not _matches_any(message or "", HOMEWORK_COMPLETION_PATTERNS)


def classify_query_safety(message, session_type="learn"):
    flags = []

    if detect_other_student_data_request(message):
        flags.append("other_student_data")
    if is_exam_restricted(message):
        flags.append("active_exam_or_quiz")
    if not is_homework_allowed(message, session_type):
        flags.append("homework_completion")

    if flags:
        return {
            "status": "blocked",
            "flags": flags,
            "message": _blocked_message(flags),
        }

    return {"status": "allowed", "flags": [], "message": ""}


def validate_response_safety(response_text):
    flags = []
    text = response_text or ""

    if re.search(r"\b(student_id|password|cnic|phone number)\b", text, flags=re.IGNORECASE):
        flags.append("possible_private_data")

    if flags:
        return {"status": "needs_review", "flags": flags}

    return {"status": "allowed", "flags": []}


def _blocked_message(flags):
    if "other_student_data" in flags:
        return "I cannot access or share another student's information. I can help you review your own progress."
    if "active_exam_or_quiz" in flags:
        return "I cannot provide answers for an active exam or quiz. I can help you revise the topic or practice similar questions."
    if "homework_completion" in flags:
        return "I cannot complete graded homework for direct submission. I can explain the question, give hints, or check your draft."
    return "I cannot help with that request, but I can support your learning safely."

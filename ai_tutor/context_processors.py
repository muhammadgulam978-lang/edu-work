from django.urls import reverse

from student_profile.models import Student

from .models import AITutorSession


def ai_tutor_fab(request):
    user = getattr(request, "user", None)
    if not user or not user.is_authenticated:
        return {"show_ai_tutor_fab": False}

    try:
        student = Student.objects.get(user=user)
    except Student.DoesNotExist:
        return {"show_ai_tutor_fab": False}

    latest_session = (
        AITutorSession.objects.filter(student=student)
        .only("id", "student_id", "started_at")
        .first()
    )
    if latest_session:
        fab_url = reverse("ai_tutor_chat", kwargs={"session_id": latest_session.id})
    else:
        fab_url = f"{reverse('ai_tutor_dashboard')}#start-session-panel"

    return {
        "show_ai_tutor_fab": True,
        "ai_tutor_fab_latest_session": latest_session,
        "ai_tutor_fab_url": fab_url,
    }

from parent_dashboard.access import accessible_students
from django.contrib.auth import get_user_model
from django.db.models import Q


User = get_user_model()


def user_role(user):
    if user.is_staff or user.is_superuser:
        return "admin"
    if hasattr(user, "teacher"):
        return "teacher"
    if hasattr(user, "student"):
        return "student"
    if hasattr(user, "parent"):
        return "parent"
    return "unknown"


def _teacher_sections(user):
    from admin_panel.models import ClassTeacher

    teacher = getattr(user, "teacher", None)
    if not teacher:
        return set()
    return set(
        ClassTeacher.objects.filter(teacher=teacher).values_list("section_id", flat=True)
    )


def _parent_student_ids(user):
    parent = getattr(user, "parent", None)
    if not parent:
        return set()
    return set(accessible_students(parent).values_list("id", flat=True))


def can_contact(sender, recipient):
    if not sender.is_authenticated or not sender.is_active or not recipient.is_active or sender.pk == recipient.pk:
        return False
    if sender.is_staff or sender.is_superuser:
        return True
    if recipient.is_staff or recipient.is_superuser:
        return True

    sender_role = user_role(sender)
    recipient_role = user_role(recipient)
    if sender_role == "teacher":
        if recipient_role == "teacher":
            return True
        section_ids = _teacher_sections(sender)
        student = getattr(recipient, "student", None)
        if student and student.section_id in section_ids:
            return True
        parent = getattr(recipient, "parent", None)
        return bool(
            parent
            and accessible_students(parent).filter(section_id__in=section_ids).exists()
        )
    if sender_role == "student":
        student = sender.student
        other_student = getattr(recipient, "student", None)
        if other_student:
            return bool(
                student.section_id
                and other_student.section_id == student.section_id
            )
        teacher = getattr(recipient, "teacher", None)
        if teacher:
            from admin_panel.models import ClassTeacher

            return ClassTeacher.objects.filter(
                teacher=teacher, section_id=student.section_id
            ).exists()
        parent = getattr(recipient, "parent", None)
        return bool(parent and accessible_students(parent).filter(pk=student.pk).exists())
    if sender_role == "parent":
        child_ids = _parent_student_ids(sender)
        student = getattr(recipient, "student", None)
        if student:
            return student.pk in child_ids
        teacher = getattr(recipient, "teacher", None)
        if teacher:
            from admin_panel.models import ClassTeacher
            from student_profile.models import Student

            section_ids = Student.objects.filter(pk__in=child_ids).values_list(
                "section_id", flat=True
            )
            return ClassTeacher.objects.filter(
                teacher=teacher, section_id__in=section_ids
            ).exists()
    return False


def contactable_users(user):
    from communication.models import UserBlock

    blocked_ids = UserBlock.objects.filter(
        Q(blocker=user) | Q(blocked=user)
    ).values_list("blocker_id", "blocked_id")
    excluded = {user.pk}
    for blocker_id, blocked_id in blocked_ids:
        excluded.add(blocked_id if blocker_id == user.pk else blocker_id)
    candidates = User.objects.filter(is_active=True).exclude(pk__in=excluded)
    if user.is_staff or user.is_superuser:
        return candidates
    return [candidate for candidate in candidates if can_contact(user, candidate)]


def can_access_conversation(user, conversation):
    if not user.is_authenticated or not user.is_active or conversation.is_archived:
        return False
    if not conversation.memberships.filter(user=user, is_archived=False).exists():
        return False
    if not conversation.is_group:
        others = list(conversation.memberships.exclude(user=user).select_related('user'))
        return bool(others) and all(can_contact(user, member.user) for member in others)
    if conversation.class_fk_id and user_role(user) == 'parent':
        return accessible_students(getattr(user, 'parent', None)).filter(class_fk_id=conversation.class_fk_id).exists()
    if conversation.class_fk_id and user_role(user) == 'student':
        return user.student.class_fk_id == conversation.class_fk_id
    if conversation.class_fk_id and user_role(user) == 'teacher':
        from admin_panel.models import ClassTeacher, AssignedPeriod
        return (ClassTeacher.objects.filter(teacher__user=user, class_fk_id=conversation.class_fk_id).exists()
                or AssignedPeriod.objects.filter(teacher__user=user, class_fk_id=conversation.class_fk_id).exists())
    return True

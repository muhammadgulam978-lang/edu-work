from django.core.exceptions import PermissionDenied


READ_ONLY_TOOL_NAMES = {
    "small_talk",
    "attendance_summary",
    "student_profile",
    "fee_collection",
    "teacher_workload",
    "advanced_analytics",
    "report_snapshot",
    "general_overview",
}


def can_use_admin_agent(user):
    return bool(
        user
        and user.is_authenticated
        and (user.is_staff or user.is_superuser or user.has_perm("auth.view_group"))
    )


def assert_can_use_admin_agent(user):
    if not can_use_admin_agent(user):
        raise PermissionDenied("You do not have permission to use the Admin AI Agent.")


def assert_tool_allowed(user, tool_name):
    assert_can_use_admin_agent(user)
    if tool_name not in READ_ONLY_TOOL_NAMES:
        raise PermissionDenied("This Admin AI action needs explicit confirmation and is not enabled yet.")
    return True


def sanitize_query(query):
    value = (query or "").strip()
    if len(value) > 2000:
        value = value[:2000]
    return value

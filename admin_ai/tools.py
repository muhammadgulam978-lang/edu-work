import re
from dataclasses import dataclass, field
from datetime import timedelta

from django.urls import reverse
from django.utils import timezone

from admin_panel.models import Class

from .models import AdminAIReport
from .security import assert_tool_allowed
from .services import (
    build_advanced_analytics,
    get_student_intelligence,
    make_json_safe,
)


@dataclass
class ToolResult:
    name: str
    summary: str
    data: dict = field(default_factory=dict)
    evidence: list = field(default_factory=list)
    actions: list = field(default_factory=list)
    status: str = "success"


def _extract_class_query(text):
    match = re.search(r"(?:class|grade)\s*([0-9]+|[a-zA-Z]+)", text.lower())
    return match.group(1) if match else None


def _extract_student_id(text):
    match = re.search(r"\b(?:student|id|profile)\s*[:#-]?\s*([A-Za-z]{1,5}[-\s]?\d{1,8}|\d{1,8})\b", text, re.IGNORECASE)
    if match:
        return match.group(1).replace(" ", "")
    match = re.search(r"\b(ST[-\s]?\d{1,8}|STD[-\s]?\d{1,8}|S\d{1,8})\b", text, re.IGNORECASE)
    return match.group(1).replace(" ", "") if match else None


def _class_from_query(text):
    value = _extract_class_query(text)
    if not value:
        return None
    return Class.objects.filter(class_name__icontains=value).first()


def _action(label, url, kind="open", meta=None):
    action = {"label": label, "url": url, "kind": kind}
    if meta:
        action["meta"] = meta
    return action


def _auto_report_action(label, report_type="full", period="today", title=None):
    meta = {
        "report_type": report_type,
        "period": period,
        "title": title or f"{label} - {timezone.localdate()}",
        "source": "admin_ai_copilot",
    }
    return _action(label, reverse("ai_analytics_report_auto_generate"), "auto_report", meta)


def small_talk_tool(*, user, query="", arguments=None):
    assert_tool_allowed(user, "small_talk")
    return ToolResult(
        name="small_talk",
        summary=(
            "Hello Admin. I can answer ERP questions using live data, open Student Insight Profiles, "
            "compare fees, analyze attendance, show teacher workload, and generate PDF/Excel reports. "
            "Try: How many students are absent today?"
        ),
        evidence=["No ERP data was queried because this was not a data request."],
        actions=[
            _action("Open Advanced Analytics", reverse("ai_analytics_advanced")),
            _auto_report_action("Generate Executive Report", "full", "today", f"Executive AI Report - {timezone.localdate()}"),
        ],
    )


def attendance_summary_tool(*, user, query="", arguments=None):
    assert_tool_allowed(user, "attendance_summary")
    class_query = _extract_class_query(query)
    class_obj = _class_from_query(query)
    if class_query and not class_obj:
        return ToolResult(
            name="attendance_summary",
            status="not_found",
            summary=f"I could not find a class or grade matching '{class_query}'. Please use the exact class name from Academics.",
            evidence=[f"Class lookup attempted for: {class_query}"],
            actions=[
                _action("Open Advanced Analytics", reverse("ai_analytics_advanced")),
            ],
        )
    filters = {"period": "today", "class_id": class_obj.id if class_obj else None}
    data = build_advanced_analytics(filters)
    class_text = f" for {class_obj.class_name}" if class_obj else ""
    summary = (
        f"Attendance today{class_text}: {data['summary']['present']} present, "
        f"{data['summary']['absent']} absent, {data['summary']['leave']} leave. "
        f"Attendance rate is {data['kpis'][1]['value']}."
    )
    return ToolResult(
        name="attendance_summary",
        summary=summary,
        data=data,
        evidence=[
            f"Attendance records from {data['filters']['start_date']} to {data['filters']['end_date']}",
            f"Class filter: {class_obj.class_name if class_obj else 'All classes'}",
        ],
        actions=[
            _action("Open Advanced Analytics", reverse("ai_analytics_advanced")),
            _auto_report_action("Generate Attendance Report", "attendance", "today", f"Attendance Report - {timezone.localdate()}"),
        ],
    )


def student_profile_tool(*, user, query="", arguments=None):
    assert_tool_allowed(user, "student_profile")
    student_id = (arguments or {}).get("student_id") or _extract_student_id(query)
    if not student_id:
        return ToolResult(
            name="student_profile",
            status="needs_input",
            summary="Please include a student ID, for example: Show student ST001 profile.",
            evidence=["No student identifier was found in the request."],
            actions=[_action("Open Student Insight Search", reverse("admin_ai_student_intelligence"))],
        )
    snapshot = get_student_intelligence(student_id, user=user)
    if not snapshot:
        return ToolResult(
            name="student_profile",
            status="not_found",
            summary="I could not find a student with that ID.",
            evidence=[f"Student lookup attempted for: {student_id}"],
            actions=[_action("Open Student Insight Search", reverse("admin_ai_student_intelligence"))],
        )
    student = snapshot["student"]
    url = reverse("admin_ai_student_intelligence_detail", kwargs={"student_id": student["student_id"]})
    return ToolResult(
        name="student_profile",
        summary=(
            f"Found {student['name']} ({student['student_id']}). "
            f"Class: {student['class']} - {student['section']}. "
            f"Attendance rate: {snapshot['attendance']['rate']}%. "
            f"Unpaid vouchers: {snapshot['fees']['unpaid']}."
        ),
        data=snapshot,
        evidence=[
            "Student Insight Profile snapshot generated from live student, attendance, fee, marks, and AI Tutor records.",
        ],
        actions=[
            _action("Open Student Insight Profile", url),
            _action("Download Student Profile PDF", reverse("admin_ai_student_intelligence_pdf", kwargs={"student_id": student["student_id"]}), "download"),
        ],
    )


def fee_collection_tool(*, user, query="", arguments=None):
    assert_tool_allowed(user, "fee_collection")
    period = "this_month"
    if "last month" in query.lower():
        period = "last_month"
    data = build_advanced_analytics({"period": period})
    summary = (
        f"Fee collection for {data['filters']['period_label']} is {data['kpis'][2]['value']}. "
        f"Paid amount: {data['summary']['fee_paid']}; total billed: {data['summary']['fee_total']}; "
        f"unpaid vouchers: {data['summary']['unpaid_vouchers']}."
    )
    return ToolResult(
        name="fee_collection",
        summary=summary,
        data=data,
        evidence=[f"Fee vouchers issued from {data['filters']['start_date']} to {data['filters']['end_date']}"],
        actions=[
            _auto_report_action("Generate Fee Report", "fees", period, f"Fee Collection Report - {timezone.localdate()}"),
            _action("Open Advanced Analytics", reverse("ai_analytics_advanced")),
        ],
    )


def teacher_workload_tool(*, user, query="", arguments=None):
    assert_tool_allowed(user, "teacher_workload")
    data = build_advanced_analytics({"period": "this_month"})
    rows = data["tables"]["teacher_workload"][:5]
    top = ", ".join([f"{row.get('teacher__name') or 'Teacher'}: {row.get('total', 0)} period(s)" for row in rows])
    summary = f"Top teacher workload from assigned periods: {top or 'No assigned periods found'}."
    return ToolResult(
        name="teacher_workload",
        summary=summary,
        data=data,
        evidence=["AssignedPeriod records grouped by teacher."],
        actions=[_action("Open Advanced Analytics", reverse("ai_analytics_advanced"))],
    )


def advanced_analytics_tool(*, user, query="", arguments=None):
    assert_tool_allowed(user, "advanced_analytics")
    data = build_advanced_analytics({"period": (arguments or {}).get("period") or "today"})
    summary = (
        f"Analytics snapshot: {data['summary']['students']} students, "
        f"{data['summary']['absent']} absent records, "
        f"{data['kpis'][2]['value']} fee collection, risk index {data['kpis'][3]['value']}."
    )
    return ToolResult(
        name="advanced_analytics",
        summary=summary,
        data=data,
        evidence=["Advanced analytics built from live ERP modules."],
        actions=[_action("Open Advanced Analytics", reverse("ai_analytics_advanced"))],
    )


def report_snapshot_tool(*, user, query="", arguments=None):
    assert_tool_allowed(user, "report_snapshot")
    period = (arguments or {}).get("period") or "today"
    data = build_advanced_analytics({"period": period})
    report = AdminAIReport.objects.create(
        title=f"AI Copilot Report - {timezone.localdate()}",
        report_type="full",
        generated_by=user,
        snapshot_data=make_json_safe(data),
        expires_at=timezone.now() + timedelta(days=30),
    )
    url = reverse("ai_analytics_report_detail", kwargs={"report_uuid": report.uuid})
    return ToolResult(
        name="report_snapshot",
        summary="I generated a saved AI Analytics report snapshot with PDF, Excel, email, and share options.",
        data={"report_uuid": str(report.uuid), "snapshot": data},
        evidence=["Report snapshot saved from live AI Analytics data."],
        actions=[
            _action("Open Generated Report", url),
            _action("Download PDF", reverse("ai_analytics_report_pdf", kwargs={"report_uuid": report.uuid}), "download"),
            _action("Download Excel", reverse("ai_analytics_report_excel", kwargs={"report_uuid": report.uuid}), "download"),
        ],
    )


def general_overview_tool(*, user, query="", arguments=None):
    assert_tool_allowed(user, "general_overview")
    data = build_advanced_analytics({"period": "today"})
    summary = (
        f"Today overview: {data['summary']['students']} students, "
        f"{data['summary']['absent']} absent records, {data['kpis'][2]['value']} fee collection, "
        f"and AI risk index {data['kpis'][3]['value']}."
    )
    return ToolResult(
        name="general_overview",
        summary=summary,
        data=data,
        evidence=["Live ERP summary for today's date."],
        actions=[_action("Open Advanced Analytics", reverse("ai_analytics_advanced"))],
    )


TOOL_REGISTRY = {
    "small_talk": small_talk_tool,
    "attendance_summary": attendance_summary_tool,
    "student_profile": student_profile_tool,
    "fee_collection": fee_collection_tool,
    "teacher_workload": teacher_workload_tool,
    "advanced_analytics": advanced_analytics_tool,
    "report_snapshot": report_snapshot_tool,
    "general_overview": general_overview_tool,
}


def execute_tool(name, *, user, query="", arguments=None):
    tool = TOOL_REGISTRY.get(name) or general_overview_tool
    return tool(user=user, query=query, arguments=arguments or {})


def serialize_tool_result(result):
    return {
        "name": result.name,
        "summary": result.summary,
        "data": make_json_safe(result.data),
        "evidence": result.evidence,
        "actions": result.actions,
        "status": result.status,
    }

import json

from .llm import generate_admin_ai_response
from .prompts import PLANNER_PROMPT


VALID_TOOLS = {
    "small_talk",
    "attendance_summary",
    "student_profile",
    "fee_collection",
    "teacher_workload",
    "advanced_analytics",
    "report_snapshot",
    "general_overview",
}


def _looks_like_student_identifier(query):
    value = (query or "").strip().lower().replace(" ", "")
    return value.startswith(("st", "std", "s")) and any(char.isdigit() for char in value)


def _is_greeting_or_help(query):
    lower = (query or "").strip().lower()
    greetings = {"hi", "hello", "hey", "salam", "assalamualaikum", "assalamu alaikum", "help", "what can you do"}
    return lower in greetings


def _fallback_plan(query):
    lower = (query or "").lower()
    if _is_greeting_or_help(query):
        return {
            "intent": "admin_agent_help",
            "tools": [{"name": "small_talk", "arguments": {}}],
            "reason": "The request is a greeting or help prompt, not an ERP data query.",
            "planner_source": "fallback",
        }
    if "absent" in lower or "attendance" in lower or "present" in lower:
        return {
            "intent": "attendance_analysis",
            "tools": [{"name": "attendance_summary", "arguments": {}}],
            "reason": "The request asks for attendance or absence data.",
            "planner_source": "fallback",
        }
    if "profile" in lower or _looks_like_student_identifier(query) or "student id" in lower:
        return {
            "intent": "student_profile_lookup",
            "tools": [{"name": "student_profile", "arguments": {}}],
            "reason": "The request looks like a student profile or student identifier lookup.",
            "planner_source": "fallback",
        }
    if "fee" in lower or "voucher" in lower or "collection" in lower:
        return {
            "intent": "fee_collection_analysis",
            "tools": [{"name": "fee_collection", "arguments": {}}],
            "reason": "The request asks for fee or voucher data.",
            "planner_source": "fallback",
        }
    if "workload" in lower or "teacher load" in lower or "period" in lower:
        return {
            "intent": "teacher_workload_analysis",
            "tools": [{"name": "teacher_workload", "arguments": {}}],
            "reason": "The request asks for teacher workload or periods.",
            "planner_source": "fallback",
        }
    if "report" in lower or "pdf" in lower or "excel" in lower:
        return {
            "intent": "report_generation",
            "tools": [{"name": "report_snapshot", "arguments": {}}],
            "reason": "The request asks to generate or export a report.",
            "planner_source": "fallback",
        }
    if "analytics" in lower or "dashboard" in lower or "risk" in lower or "overview" in lower or "summary" in lower:
        return {
            "intent": "analytics_snapshot",
            "tools": [{"name": "advanced_analytics", "arguments": {}}],
            "reason": "The request asks for analytics or risk insight.",
            "planner_source": "fallback",
        }
    return {
        "intent": "admin_agent_help",
        "tools": [{"name": "small_talk", "arguments": {}}],
        "reason": "No specific ERP module was detected, so the agent asks for a clearer command.",
        "planner_source": "fallback",
    }


def _clean_plan(plan):
    tools = []
    for item in plan.get("tools", []):
        name = item.get("name")
        if name in VALID_TOOLS:
            tools.append({"name": name, "arguments": item.get("arguments") or {}})
    if not tools:
        tools = [{"name": "general_overview", "arguments": {}}]
    return {
        "intent": plan.get("intent") or tools[0]["name"],
        "tools": tools[:3],
        "reason": plan.get("reason") or "Tool plan selected for the administrator request.",
        "planner_source": plan.get("planner_source") or "llm",
    }


def _guard_plan(query, plan):
    lower = (query or "").lower()
    asks_attendance = "absent" in lower or "attendance" in lower or "present" in lower
    asks_profile = "profile" in lower or "student id" in lower or _looks_like_student_identifier(query)
    if _is_greeting_or_help(query):
        return {
            "intent": "admin_agent_help",
            "tools": [{"name": "small_talk", "arguments": {}}],
            "reason": "Greeting/help prompts should not query ERP data.",
            "planner_source": plan.get("planner_source", "guarded"),
        }
    if asks_profile:
        return {
            "intent": "student_profile_lookup",
            "tools": [{"name": "student_profile", "arguments": {}}],
            "reason": "Student identifiers/profile requests should open Student Insight Profile evidence.",
            "planner_source": plan.get("planner_source", "guarded"),
        }
    if asks_attendance and not asks_profile:
        return {
            "intent": "attendance_analysis",
            "tools": [{"name": "attendance_summary", "arguments": {}}],
            "reason": "Attendance keywords require live attendance data.",
            "planner_source": plan.get("planner_source", "guarded"),
        }
    return plan


def plan_admin_request(query, memory=None):
    llm_result = generate_admin_ai_response(
        system_prompt=PLANNER_PROMPT,
        user_prompt=f"Request: {query}\nMemory: {memory or {}}",
        response_format="json",
    )
    if llm_result.text and not llm_result.error:
        try:
            plan = json.loads(llm_result.text)
            return _guard_plan(query, _clean_plan(plan))
        except (TypeError, ValueError, json.JSONDecodeError):
            pass
    plan = _fallback_plan(query)
    if llm_result.error:
        plan["planner_error"] = llm_result.error
    return _guard_plan(query, _clean_plan(plan))

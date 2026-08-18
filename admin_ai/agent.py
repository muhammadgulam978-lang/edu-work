from .llm import generate_admin_ai_response
from .memory import build_session_memory
from .models import AdminAIToolAuditLog
from .planner import plan_admin_request
from .prompts import ADMIN_AGENT_SYSTEM_PROMPT, build_answer_prompt
from .security import assert_can_use_admin_agent, sanitize_query
from .tools import execute_tool, serialize_tool_result


def _fallback_answer(tool_results):
    if not tool_results:
        return "I could not retrieve ERP evidence for this request."
    return tool_results[0]["summary"]


def run_admin_agent(*, query, user, conversation=None):
    assert_can_use_admin_agent(user)
    query = sanitize_query(query)
    memory = build_session_memory(conversation)
    plan = plan_admin_request(query, memory=memory)

    tool_results = []
    for tool_call in plan["tools"]:
        result = execute_tool(
            tool_call["name"],
            user=user,
            query=query,
            arguments=tool_call.get("arguments") or {},
        )
        serialized = serialize_tool_result(result)
        tool_results.append(serialized)
        AdminAIToolAuditLog.objects.create(
            user=user,
            conversation=conversation,
            tool_name=serialized["name"],
            query=query,
            filters=tool_call.get("arguments") or {},
            result_summary=serialized["summary"][:500],
            status=serialized["status"],
        )

    answer_prompt = build_answer_prompt(
        query=query,
        plan=plan,
        tool_results=tool_results,
        memory=memory,
    )
    llm_result = generate_admin_ai_response(
        system_prompt=ADMIN_AGENT_SYSTEM_PROMPT,
        user_prompt=answer_prompt,
    )

    used_llm = bool(llm_result.text and not llm_result.error)
    answer = llm_result.text if used_llm else _fallback_answer(tool_results)
    actions = []
    evidence = []
    for result in tool_results:
        actions.extend(result.get("actions") or [])
        evidence.extend(result.get("evidence") or [])

    return {
        "answer": answer,
        "intent": plan["intent"],
        "plan": {
            "intent": plan["intent"],
            "reason": plan["reason"],
            "planner_source": plan.get("planner_source", "llm"),
            "steps": [
                f"Understand administrator request: {query}",
                f"Select ERP tool(s): {', '.join([item['name'] for item in plan['tools']])}",
                "Retrieve live ERP data through approved tools",
                "Generate an evidence-based response",
            ],
        },
        "tools": tool_results,
        "evidence": evidence,
        "actions": actions,
        "model": llm_result.model,
        "mode": "llm_agent" if used_llm else "tool_agent_fallback",
        "llm_error": llm_result.error,
        "token_count": llm_result.token_count,
    }

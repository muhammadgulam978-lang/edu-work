def build_session_memory(conversation, limit=6):
    if not conversation:
        return {"recent_messages": []}
    messages = conversation.messages.order_by("-created_at")[:limit]
    recent = [
        {
            "sender": message.sender,
            "intent": message.intent,
            "tool_name": message.tool_name,
            "content": message.content[:500],
        }
        for message in reversed(list(messages))
    ]
    return {"recent_messages": recent}

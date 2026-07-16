from dataclasses import dataclass

from django.conf import settings


@dataclass
class AdminLLMResult:
    text: str
    model: str
    token_count: int = 0
    error: str = ""


def generate_admin_ai_response(*, system_prompt, user_prompt, response_format="text"):
    model = getattr(settings, "AI_TUTOR_MODEL", "gpt-5.6-terra")
    api_key = getattr(settings, "AI_TUTOR_API_KEY", "")
    provider = getattr(settings, "AI_TUTOR_PROVIDER", "openai")

    if not api_key:
        return AdminLLMResult(
            text="",
            model=model,
            error="missing_api_key",
        )

    if provider != "openai":
        return AdminLLMResult(
            text="",
            model=model,
            error=f"unsupported_provider:{provider}",
        )

    try:
        from openai import OpenAI

        client = OpenAI(api_key=api_key, timeout=20)
        kwargs = {
            "model": model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": 0.2,
        }
        if response_format == "json":
            kwargs["response_format"] = {"type": "json_object"}
        response = client.chat.completions.create(**kwargs)
        text = response.choices[0].message.content or ""
        usage = getattr(response, "usage", None)
        token_count = getattr(usage, "total_tokens", 0) if usage else 0
        return AdminLLMResult(text=text.strip(), model=model, token_count=token_count)
    except Exception as exc:
        return AdminLLMResult(
            text="",
            model=model,
            error=str(exc),
        )

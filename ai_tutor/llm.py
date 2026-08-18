from dataclasses import dataclass

from django.conf import settings


@dataclass
class LLMResult:
    text: str
    model: str
    token_count: int = 0
    error: str = ""


def generate_ai_tutor_response(*, model, system_prompt, user_prompt, context_documents=None, response_format="text"):
    configured_model = model or getattr(settings, "AI_TUTOR_MODEL", "gpt-5.6-terra")
    api_key = getattr(settings, "AI_TUTOR_API_KEY", "")
    provider = getattr(settings, "AI_TUTOR_PROVIDER", "openai")

    if not api_key:
        groq_key = getattr(settings, "GROQ_API_KEY", "")
        if groq_key:
            return _generate_with_groq(
                api_key=groq_key,
                model=getattr(settings, "AI_TUTOR_FALLBACK_MODEL", "llama-3.3-70b-versatile"),
                system_prompt=system_prompt,
                user_prompt=user_prompt,
            )
        return LLMResult(
            text=(
                "AI Tutor needs an AI API key before it can answer. "
                "Please configure AI_TUTOR_API_KEY or GROQ_API_KEY."
            ),
            model=configured_model,
            error="missing_api_key",
        )

    if provider != "openai":
        return LLMResult(
            text=f"AI Tutor provider '{provider}' is not supported yet.",
            model=configured_model,
            error="unsupported_provider",
        )

    try:
        from openai import OpenAI

        client = OpenAI(api_key=api_key)
        response = client.chat.completions.create(
            model=configured_model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.3,
        )
        text = response.choices[0].message.content or ""
        usage = getattr(response, "usage", None)
        tokens = getattr(usage, "total_tokens", 0) if usage else 0
        return LLMResult(text=text.strip(), model=configured_model, token_count=tokens)
    except Exception as exc:
        fallback = getattr(settings, "AI_TUTOR_FALLBACK_MODEL", "")
        groq_key = getattr(settings, "GROQ_API_KEY", "")
        if fallback and groq_key:
            return _generate_with_groq(
                api_key=groq_key,
                model=fallback,
                system_prompt=system_prompt,
                user_prompt=user_prompt,
            )
        return LLMResult(
            text=(
                "AI Tutor could not reach GPT-5.6 Terra right now. "
                "The request was logged, and the configuration should be checked by an administrator."
            ),
            model=configured_model,
            error=str(exc),
        )


def _generate_with_groq(*, api_key, model, system_prompt, user_prompt):
    try:
        from groq import Groq

        client = Groq(api_key=api_key)
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.3,
        )
        text = response.choices[0].message.content or ""
        usage = getattr(response, "usage", None)
        tokens = getattr(usage, "total_tokens", 0) if usage else 0
        return LLMResult(text=text.strip(), model=model, token_count=tokens)
    except Exception as exc:
        return LLMResult(
            text=(
                "AI Tutor could not reach the fallback AI model right now. "
                "Please check the AI API configuration."
            ),
            model=model,
            error=str(exc),
        )

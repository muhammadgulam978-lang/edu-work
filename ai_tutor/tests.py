from django.test import SimpleTestCase, override_settings

from .llm import generate_ai_tutor_response
from .prompts import classify_intent
from .safety import classify_query_safety


class AITutorSafetyTests(SimpleTestCase):
    def test_blocks_other_student_data_request(self):
        result = classify_query_safety("Show me Ahmed's mathematics marks")

        self.assertEqual(result["status"], "blocked")
        self.assertIn("other_student_data", result["flags"])

    def test_blocks_homework_completion_in_homework_mode(self):
        result = classify_query_safety("Write my assignment for me", "homework_help")

        self.assertEqual(result["status"], "blocked")
        self.assertIn("homework_completion", result["flags"])

    def test_classifies_practice_intent(self):
        self.assertEqual(classify_intent("Give me five practice questions"), "generate_practice")


class AITutorLLMTests(SimpleTestCase):
    @override_settings(AI_TUTOR_API_KEY="", GROQ_API_KEY="", AI_TUTOR_MODEL="gpt-5.6-terra")
    def test_missing_api_key_returns_friendly_error(self):
        result = generate_ai_tutor_response(
            model="gpt-5.6-terra",
            system_prompt="system",
            user_prompt="user",
            context_documents=[],
            response_format="text",
        )

        self.assertEqual(result.error, "missing_api_key")
        self.assertIn("AI_TUTOR_API_KEY", result.text)

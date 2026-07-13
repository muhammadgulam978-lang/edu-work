import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'sms.settings')
django.setup()

from django.conf import settings
from groq import Groq
import json

client = Groq(api_key=settings.GROQ_API_KEY)

prompt = """Generate exactly 2 MCQ questions about Physics.
Return ONLY a valid JSON array. No explanation, no markdown.
Format: [{"type":"MCQ","question":"...?","option_a":"...","option_b":"...","option_c":"...","option_d":"...","correct_answer":"option_a","marks":1}]
Generate now:"""

try:
    chat = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.4,
        max_tokens=1000,
    )
    raw = chat.choices[0].message.content.strip()
    print("RAW RESPONSE:")
    print(raw)
    parsed = json.loads(raw)
    print("PARSED OK:", len(parsed), "questions")
except Exception as e:
    import traceback
    traceback.print_exc()
    print("ERROR:", e)
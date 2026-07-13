"""
exam_system/services.py
=======================
Groq API se questions generate karo + paper blueprint se select karo.
"""

import json
import random
from django.conf import settings

from io import BytesIO
from django.core.files.base import ContentFile
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.lib.utils import simpleSplit



# =============================================================
# GROQ API CALL — helper
# =============================================================

def _call_groq(prompt: str, max_tokens: int = 2000) -> str:
    try:
        from groq import Groq
    except ImportError:
        raise ImportError("Groq library install nahi hai. Run: pip install groq")

    api_key = getattr(settings, 'GROQ_API_KEY', None)
    if not api_key:
        raise ValueError("GROQ_API_KEY settings.py mein set nahi hai.")

    client = Groq(api_key=api_key)
    chat_completion = client.chat.completions.create(
        messages=[
            {
                "role": "system",
                "content": (
                    "You are an expert educational question generator for Pakistani school system. "
                    "Always respond ONLY with valid JSON. No extra text, no markdown, no backticks."
                ),
            },
            {"role": "user", "content": prompt},
        ],
        model="llama3-8b-8192",
        max_tokens=max_tokens,
        temperature=0.7,
    )
    return chat_completion.choices[0].message.content.strip()


# =============================================================
# SECTION 1: AI QUESTION GENERATION (Topic se)
# =============================================================

def generate_questions_ai(
    topic, difficulty, question_type, count, subject_name, class_name
) -> list:
    if question_type == 'MCQ':
        format_instruction = "Each question must have exactly 4 options (option_a-d) and answer field (A/B/C/D)."
        example = '{"questions":[{"question":"...?","marks":1,"option_a":"...","option_b":"...","option_c":"...","option_d":"...","answer":"A"}]}'
    elif question_type == 'SHORT':
        format_instruction = "Each question should require a 2-4 sentence answer."
        example = '{"questions":[{"question":"...?","marks":3,"answer":"..."}]}'
    else:
        format_instruction = "Each question should require a detailed paragraph answer."
        example = '{"questions":[{"question":"...?","marks":8,"answer":"..."}]}'

    prompt = f"""Generate exactly {count} {question_type} questions for:
- Subject: {subject_name}
- Class: {class_name}
- Topic: {topic}
- Difficulty: {difficulty}

{format_instruction}
Return ONLY this JSON (no extra text): {example}
Generate {count} questions now."""

    raw_response = _call_groq(prompt, max_tokens=2000)

    try:
        cleaned = raw_response.replace("```json", "").replace("```", "").strip()
        data = json.loads(cleaned)
        questions = data.get("questions", [])
        for q in questions:
            if question_type == 'MCQ':
                q.setdefault('option_a', '')
                q.setdefault('option_b', '')
                q.setdefault('option_c', '')
                q.setdefault('option_d', '')
            else:
                q['option_a'] = q['option_b'] = q['option_c'] = q['option_d'] = None
        return questions
    except json.JSONDecodeError as e:
        raise ValueError(f"AI response parse nahi hua: {str(e)}\nRaw: {raw_response[:300]}")


# =============================================================
# SECTION 2: PDF TEXT SE QUESTIONS GENERATE KARO
# =============================================================

def generate_questions_from_pdf_text(
    pdf_text, question_type, difficulty, count, subject_name, class_name, marks_each=1
) -> list:
    if len(pdf_text) > 3000:
        pdf_text = pdf_text[:3000] + "\n...[text truncated]"

    if question_type == 'MCQ':
        fmt = '{"questions":[{"question":"...?","marks":1,"option_a":"...","option_b":"...","option_c":"...","option_d":"...","answer":"A"}]}'
    else:
        fmt = '{"questions":[{"question":"...?","marks":3,"answer":"..."}]}'

    prompt = f"""You are an exam paper setter for {subject_name} (Class {class_name}).
Based on this content, generate exactly {count} {question_type} questions.
Difficulty: {difficulty}, Marks each: {marks_each}

CONTENT:
{pdf_text}

Return ONLY this JSON: {fmt}"""

    raw_response = _call_groq(prompt, max_tokens=2500)
    try:
        cleaned = raw_response.replace("```json", "").replace("```", "").strip()
        data = json.loads(cleaned)
        questions = data.get("questions", [])
        for q in questions:
            q['marks'] = marks_each
            if question_type != 'MCQ':
                q['option_a'] = q['option_b'] = q['option_c'] = q['option_d'] = None
        return questions
    except json.JSONDecodeError as e:
        raise ValueError(f"AI response parse nahi hua: {str(e)}\nRaw: {raw_response[:300]}")


# =============================================================
# SECTION 3: BLUEPRINT SE PAPER GENERATE KARO — FIXED ✅
# =============================================================

def generate_paper_from_blueprint(blueprint) -> list:
    """
    Blueprint ke rules ke mutabiq Question Bank se APPROVED questions select karo.

    FIX:
    1. Bank dhundne ke liye academic_year filter optional rakha (fallback without year)
    2. Agar approved kam hain to unapproved bhi include karo (warning ke saath)
    3. Agar kisi type mein questions nahi to ValueError raise karo with clear message
    """
    from exam_system.models import Question, QuestionBank

    selected_questions = []
    selected_ids = []

    # ── Step 1: Question Bank dhundo ─────────────────────────
    # Pehle exact match try karo (subject + class + academic_year)
    bank = QuestionBank.objects.filter(
        subject=blueprint.subject,
        class_fk=blueprint.exam_plan.class_fk,
        academic_year=blueprint.exam_plan.academic_year,
    ).first()

    # Agar academic_year se nahi mila to sirf subject+class se dhundo
    if not bank:
        bank = QuestionBank.objects.filter(
            subject=blueprint.subject,
            class_fk=blueprint.exam_plan.class_fk,
        ).first()

    if not bank:
        raise ValueError(
            f"❌ '{blueprint.subject.name}' ka Question Bank nahi mila. "
            f"Pehle Question Bank mein questions add karo aur approve karo."
        )

    # ── Step 2: Check karo kuch approved questions hain? ─────
    total_approved = bank.questions.filter(human_approved=True).count()
    total_all      = bank.questions.count()

    if total_all == 0:
        raise ValueError(
            f"❌ '{blueprint.subject.name}' ke Question Bank mein koi questions nahi hain. "
            f"Pehle PDF upload karo ya manually questions add karo."
        )

    # ── Step 3: Har rule ke liye questions select karo ───────
    warnings = []

    for rule in blueprint.rules.all():
        q_type     = rule.question_type
        total_need = rule.count

        # Difficulty split
        easy_need   = round(total_need * rule.easy_percent   / 100)
        medium_need = round(total_need * rule.medium_percent / 100)
        hard_need   = total_need - easy_need - medium_need

        for difficulty, need_count in [
            ('EASY',   easy_need),
            ('MEDIUM', medium_need),
            ('HARD',   hard_need),
        ]:
            if need_count <= 0:
                continue

            # Pehle: approved + sahi difficulty
            available = list(
                bank.questions.filter(
                    question_type=q_type,
                    difficulty=difficulty,
                    human_approved=True,
                ).exclude(id__in=selected_ids)
            )

            # Kam hain to: approved + koi bhi difficulty (same type)
            if len(available) < need_count:
                extra = list(
                    bank.questions.filter(
                        question_type=q_type,
                        human_approved=True,
                    ).exclude(
                        id__in=selected_ids + [q.id for q in available]
                    )
                )
                available += extra

            # Abhi bhi kam hain to: unapproved bhi lo (last resort)
            if len(available) < need_count:
                extra = list(
                    bank.questions.filter(
                        question_type=q_type,
                    ).exclude(
                        id__in=selected_ids + [q.id for q in available]
                    )
                )
                available += extra
                if extra:
                    warnings.append(
                        f"⚠️ {q_type} ({difficulty}): approved questions kam the, "
                        f"kuch unapproved bhi include kiye."
                    )

            if not available:
                warnings.append(
                    f"⚠️ {q_type} ke liye koi questions nahi mile — skip kiya."
                )
                continue

            random.shuffle(available)
            picked = available[:need_count]
            selected_questions.extend(picked)
            selected_ids.extend([q.id for q in picked])

    if not selected_questions:
        raise ValueError(
            f"❌ Question Bank mein blueprint ke mutabiq koi questions nahi mile. "
            f"Bank mein {total_all} questions hain (approved: {total_approved}). "
            f"Questions approve karo ya blueprint ke rules check karo."
        )

    # Warnings store karo (views.py mein messages se dikhao chahein to)
    blueprint._generation_warnings = warnings

    return selected_questions


# =============================================================
# SECTION 4: RESULTS COMPILE KARO
# =============================================================

def compile_results(schedule) -> int:
    from exam_system.models import AnswerSheet, QuestionScore, CentralizedResult, PaperBlueprint

    sheets = AnswerSheet.objects.filter(
        schedule=schedule,
        is_submitted=True,
    ).select_related('student', 'paper__blueprint')

    try:
        blueprint = PaperBlueprint.objects.get(
            exam_plan=schedule.exam_plan,
            subject=schedule.subject,
        )
        total_marks   = blueprint.total_marks
        passing_marks = blueprint.passing_marks
    except PaperBlueprint.DoesNotExist:
        total_marks   = 100
        passing_marks = 40

    compiled_count = 0

    for sheet in sheets:
        scores  = QuestionScore.objects.filter(answer_sheet=sheet)
        obtained = 0
        for score in scores:
            if score.teacher_score is not None:
                obtained += float(score.teacher_score)
            elif score.ai_score is not None:
                obtained += float(score.ai_score)

        percentage = round((obtained / total_marks) * 100, 2) if total_marks else 0
        is_pass    = obtained >= passing_marks

        if   percentage >= 90: grade = 'A+'
        elif percentage >= 80: grade = 'A'
        elif percentage >= 70: grade = 'B'
        elif percentage >= 60: grade = 'C'
        elif percentage >= 50: grade = 'D'
        else:                  grade = 'F'

        CentralizedResult.objects.update_or_create(
            answer_sheet=sheet,
            defaults={
                'total_marks':    total_marks,
                'obtained_marks': obtained,
                'percentage':     percentage,
                'grade':          grade,
                'is_pass':        is_pass,
                'remarks':        'Pass' if is_pass else 'Fail',
            }
        )
        compiled_count += 1

    results = list(
        CentralizedResult.objects.filter(
            answer_sheet__schedule=schedule
        ).order_by('-obtained_marks')
    )
    for pos, result in enumerate(results, start=1):
        result.class_position = pos
        result.save(update_fields=['class_position'])

    return compiled_count




def generate_final_pdf(paper):

    buffer = BytesIO()

    p = canvas.Canvas(buffer)

    y = 800

    p.setFont(
        "Helvetica-Bold",
        16
    )

    p.drawString(
        50,
        y,
        paper.blueprint.subject.name
    )

    y -= 40

    for idx,q in enumerate(
        paper.questions.all(),
        start=1
    ):

        p.drawString(
            50,
            y,
            f"{idx}. {q.text}"
        )

        y -= 25

        if y < 80:
            p.showPage()
            y = 800

    p.save()

    pdf = buffer.getvalue()

    paper.pdf_file.save(
        f"paper_{paper.id}.pdf",
        ContentFile(pdf),
        save=True
    )
    
    
# exam_system/services.py — is function ko file ke end mein add karein

def generate_paper_pdf(paper):
    """
    GeneratedPaper ke questions se ek PDF banata hai aur
    paper.pdf_file field mein save kar deta hai.
    """
    buffer = BytesIO() 
    c = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4
    margin = 2 * cm
    y = height - margin

    blueprint = paper.blueprint

    # ── Header ──
    c.setFont("Helvetica-Bold", 16)
    c.drawCentredString(width / 2, y, f"{blueprint.subject.name} — Class {blueprint.exam_plan.class_fk.class_name}")
    y -= 22
    c.setFont("Helvetica", 11)
    c.drawCentredString(width / 2, y, f"{blueprint.exam_plan.title}  |  Paper Set: {paper.paper_set}")
    y -= 16
    c.drawCentredString(width / 2, y, f"Total Marks: {blueprint.total_marks}   Passing Marks: {blueprint.passing_marks}")
    y -= 26
    c.line(margin, y, width - margin, y)
    y -= 24

    c.setFont("Helvetica", 11)
    questions = paper.questions.all().order_by('question_type')

    for i, q in enumerate(questions, start=1):
        text = f"Q{i}. {q.text}  [{q.marks} marks]"
        lines = simpleSplit(text, "Helvetica", 11, width - 2 * margin)
        for line in lines:
            if y < margin + 40:
                c.showPage()
                c.setFont("Helvetica", 11)
                y = height - margin
            c.drawString(margin, y, line)
            y -= 16

        if q.option_a:
            for label, opt in [('A', q.option_a), ('B', q.option_b), ('C', q.option_c), ('D', q.option_d)]:
                if not opt:
                    continue
                opt_text = f"   {label}. {opt}"
                if y < margin + 40:
                    c.showPage()
                    c.setFont("Helvetica", 11)
                    y = height - margin
                c.drawString(margin, y, opt_text)
                y -= 15

        y -= 10  # question ke darmiyan gap

    c.save()
    buffer.seek(0)

    filename = f"paper_{paper.id}_{paper.paper_set}.pdf"
    # save=True is liye taake DB record apne aap update ho jaye
    paper.pdf_file.save(filename, ContentFile(buffer.read()), save=True)    

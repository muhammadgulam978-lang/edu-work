# =============================================================
# exam_system/views.py
# =============================================================

import json
import fitz                          # pip install pymupdf
from groq import Groq

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from django.http import HttpResponse, JsonResponse
from django.db import transaction
from django.conf import settings

from exam_system.services import generate_paper_pdf 

from teacher_dashboard.models import Teacher
from student_profile.models import Student
from admin_panel.models import (
    Class, Section, Subject, AcademicYear, AssignedPeriod
)
from exam_system.models import (
    QuestionBank, Question,
    ExamPlan, ExamSchedule, PaperBlueprint, BlueprintRule,
    GeneratedPaper, PaperApproval, PaperAccessLog,
    ExamSeatingPlan, InvigilatorDuty,
    ExamAttendance, AnswerSheet, QuestionScore,
    CentralizedResult,
)
from exam_system.services import (
    generate_questions_ai,
    generate_questions_from_pdf_text,
    generate_paper_from_blueprint,
    compile_results,
)


# =============================================================
# HELPERS
# =============================================================

def get_active_year():
    return AcademicYear.objects.filter(is_active=True).first()


def _extract_pdf_text(pdf_file) -> str:
    """
    InMemoryUploadedFile → plain text via PyMuPDF (fitz).
    """
    pdf_bytes = pdf_file.read()
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    text = "".join(page.get_text() for page in doc)
    doc.close()
    return text.strip()


def _groq_generate(groq_client, prompt: str) -> list:
    """
    Groq API call → JSON list parse karke return karo.
    """
    chat = groq_client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.4,
        max_tokens=4096,
    )
    raw = chat.choices[0].message.content.strip()
    # markdown fences hata do
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
    return json.loads(raw.strip())


# =============================================================
# SECTION 1: QUESTION BANK — LIST + CREATE
# =============================================================

@login_required
def question_bank_list(request):
    """
    Sab question banks dikhao.
    Yahan se naya bank (subject) create bhi ho sakta hai.
    """
    academic_year = get_active_year()
    banks = QuestionBank.objects.filter(
        academic_year=academic_year
    ).select_related('subject', 'class_fk', 'created_by')

    classes  = Class.objects.all()
    subjects = Subject.objects.all()

    # ── Naya Question Bank / Subject create ──────────────────
    if request.method == 'POST':
        subject_id = request.POST.get('subject_id')
        class_id   = request.POST.get('class_id')

        if not subject_id or not class_id:
            messages.error(request, "Please select both Subject and Class.")
            return redirect('question_bank_list')

        bank, created = QuestionBank.objects.get_or_create(
            subject_id=subject_id,
            class_fk_id=class_id,
            academic_year=academic_year,
            defaults={'created_by': request.user},
        )

        if created:
            messages.success(request, "New Question Bank created! You can now upload a book.")
        else:
            messages.info(request, "ℹ️ Ye Question Bank pehle se exist karta hai.")

        return redirect('upload_book_for_bank', bank_id=bank.id)

    return render(request, 'exam_system/question_bank_list.html', {
        'banks':         banks,
        'academic_year': academic_year,
        'classes':       classes,
        'subjects':      subjects,
    })

@login_required
def delete_question_bank(request, bank_id):
    """Question bank delete karo (uske sab questions bhi CASCADE se delete ho jayenge)."""
    bank = get_object_or_404(QuestionBank, id=bank_id)

    if request.method == 'POST':
        bank_name = f"{bank.subject.name} - Class {bank.class_fk.class_name}"
        bank.delete()
        messages.success(request, f"Question bank '{bank_name}' deleted successfully.")
    else:
        messages.error(request, "Invalid request method.")

    return redirect('question_bank_list')


# =============================================================
# SECTION 2: QUESTION BANK DETAIL — Questions + Filter
# =============================================================

@login_required
def question_bank_detail(request, bank_id):
    """Ek bank ke sab questions — filter by type/difficulty."""
    bank = get_object_or_404(QuestionBank, id=bank_id)

    q_type        = request.GET.get('type', '')
    diff          = request.GET.get('difficulty', '')
    approved_only = request.GET.get('approved', '')

    questions = bank.questions.all().order_by('-created_at')

    if q_type:
        questions = questions.filter(question_type=q_type)
    if diff:
        questions = questions.filter(difficulty=diff)
    if approved_only == '1':
        questions = questions.filter(human_approved=True)

    return render(request, 'exam_system/question_bank_detail.html', {
        'bank':           bank,
        'questions':      questions,
        'q_types':        Question.QUESTION_TYPES,
        'difficulties':   Question.DIFFICULTY_LEVELS,
        'total_count':    bank.questions.count(),
        'approved_count': bank.questions.filter(human_approved=True).count(),
    })


# =============================================================
# SECTION 3: BOOK UPLOAD → AI QUESTIONS GENERATE
# =============================================================

@login_required
def upload_book_for_bank(request, bank_id):
    """
    Step 1 → PDF Book upload karo
    Step 2 → Groq AI se MCQ + SHORT + LONG questions generate karo
    Step 3 → Question Bank mein unapproved save karo
    Step 4 → Teacher review/edit/approve kare
    """
    bank = get_object_or_404(QuestionBank, id=bank_id)

    if request.method == 'POST':
        pdf_file = request.FILES.get('pdf_file')

        # ── Validations ──────────────────────────────────────
        if not pdf_file:
            messages.error(request, "Please upload a PDF file.")
            return redirect('upload_book_for_bank', bank_id=bank.id)

        if not pdf_file.name.lower().endswith('.pdf'):
            messages.error(request, "Only PDF files are allowed.")
            return redirect('upload_book_for_bank', bank_id=bank.id)

        if pdf_file.size > 15 * 1024 * 1024:
            messages.error(request, "File must not be larger than 15MB.")
            return redirect('upload_book_for_bank', bank_id=bank.id)

        try:
            # ── Step 1: PDF se text extract ──────────────────
            text = _extract_pdf_text(pdf_file)

            if not text or len(text) < 50:
                messages.error(
                    request,
                    "Could not extract text from this PDF. "
                    "Please use a text-based PDF instead of a scanned one."
                )
                return redirect('upload_book_for_bank', bank_id=bank.id)

            # ── Step 2: Form values ───────────────────────────
            difficulty  = request.POST.get('difficulty', 'MEDIUM')
            mcq_count   = int(request.POST.get('mcq_count',   10))
            short_count = int(request.POST.get('short_count',  7))
            long_count  = int(request.POST.get('long_count',   5))

            groq_client = Groq(api_key=settings.GROQ_API_KEY)
            total_saved = 0

            question_configs = [
                ('MCQ',   mcq_count,   1,
                 '{"type":"MCQ","question":"...?","option_a":"...","option_b":"...","option_c":"...","option_d":"...","correct_answer":"option_a","marks":1}'),
                ('SHORT', short_count, 3,
                 '{"type":"SHORT","question":"...?","option_a":null,"option_b":null,"option_c":null,"option_d":null,"correct_answer":"model answer","marks":3}'),
                ('LONG',  long_count,  5,
                 '{"type":"LONG","question":"...?","option_a":null,"option_b":null,"option_c":null,"option_d":null,"correct_answer":"model answer","marks":5}'),
            ]

            # ── Step 3: Har type ke liye Groq call ───────────
            for q_type, count, marks, fmt in question_configs:
                if count == 0:
                    continue

                prompt = f"""You are an expert exam question generator for {bank.subject.name} — Class {bank.class_fk.class_name}.

Based on this content, generate exactly {count} {q_type} questions.
Difficulty: {difficulty}.

Content:
\"\"\"
{text[:5000]}
\"\"\"

Return ONLY a valid JSON array. No explanation, no markdown, no extra text.
Use this exact format for each question:
{fmt}

Generate exactly {count} questions now:"""

                try:
                    generated = _groq_generate(groq_client, prompt)
                except json.JSONDecodeError:
                    messages.warning(
                        request,
                        f"AI returned an unexpected response for {q_type} questions. Skipping."
                    )
                    continue

                # ── Step 4: DB mein save ──────────────────────
                for q_data in generated:
                    q_text = q_data.get('question', '').strip()
                    if not q_text:
                        continue

                    Question.objects.create(
                        bank=bank,
                        question_type=q_type,
                        text=q_text,
                        marks=q_data.get('marks', marks),
                        difficulty=difficulty,
                        option_a=q_data.get('option_a'),
                        option_b=q_data.get('option_b'),
                        option_c=q_data.get('option_c'),
                        option_d=q_data.get('option_d'),
                        correct_answer=q_data.get('correct_answer', ''),
                        topic_tag=f"PDF: {pdf_file.name}",
                        ai_generated=True,
                        human_approved=False,   # Teacher approve karega
                    )
                    total_saved += 1

            messages.success(
                request,
                f"{total_saved} questions generated! "
                f"Review them below, edit if needed, then approve."
            )
            return redirect('question_bank_detail', bank_id=bank.id)

        except Exception as e:
            messages.error(request, f"Error: {str(e)}")
            return redirect('upload_book_for_bank', bank_id=bank.id)

    return render(request, 'exam_system/upload_book_for_bank.html', {
        'bank': bank,
    })


# =============================================================
# SECTION 4: QUESTION CRUD — Add / Edit / Approve
# =============================================================

@login_required
def add_question_to_bank(request, bank_id):
    """Teacher manually question add kare."""
    bank = get_object_or_404(QuestionBank, id=bank_id)

    if request.method == 'POST':
        try:
            Question.objects.create(
                bank=bank,
                question_type=request.POST.get('question_type'),
                text=request.POST.get('text', '').strip(),
                marks=int(request.POST.get('marks', 1)),
                difficulty=request.POST.get('difficulty', 'MEDIUM'),
                bloom_level=request.POST.get('bloom_level', 'UNDERSTAND'),
                topic_tag=request.POST.get('topic_tag', ''),
                option_a=request.POST.get('option_a') or None,
                option_b=request.POST.get('option_b') or None,
                option_c=request.POST.get('option_c') or None,
                option_d=request.POST.get('option_d') or None,
                correct_answer=request.POST.get('correct_answer', ''),
                ai_generated=False,
                human_approved=False,
            )
            messages.success(request, "Question added successfully!")
        except Exception as e:
            messages.error(request, f"Could not add question: {str(e)}")

        return redirect('question_bank_detail', bank_id=bank.id)

    return render(request, 'exam_system/add_question.html', {
        'bank':        bank,
        'q_types':     Question.QUESTION_TYPES,
        'difficulties': Question.DIFFICULTY_LEVELS,
        'bloom_levels': Question.BLOOM_LEVELS,
    })


@login_required
def edit_question(request, question_id):
    """Teacher question edit kare — inline form ya standalone page."""
    question = get_object_or_404(Question, id=question_id)

    if request.method == 'POST':
        question.text           = request.POST.get('text', '').strip()
        question.marks          = int(request.POST.get('marks', question.marks))
        question.difficulty     = request.POST.get('difficulty', question.difficulty)
        question.option_a       = request.POST.get('option_a', '') or None
        question.option_b       = request.POST.get('option_b', '') or None
        question.option_c       = request.POST.get('option_c', '') or None
        question.option_d       = request.POST.get('option_d', '') or None
        question.correct_answer = request.POST.get('correct_answer', '')
        question.save()

        messages.success(request, "Question updated successfully!")

        # Inline edit ke baad filters ke saath wapas bhejo
        next_url = request.POST.get('next', '').strip()
        if next_url:
            return redirect(next_url)
        return redirect('question_bank_detail', bank_id=question.bank.id)

    return render(request, 'exam_system/edit_question.html', {
        'question':    question,
        'difficulties': Question.DIFFICULTY_LEVELS,
    })


@login_required
def approve_question(request, question_id):
    """Coordinator ya Academic Head question approve kare."""
    question = get_object_or_404(Question, id=question_id)

    if request.method == 'POST':
        question.human_approved = True
        question.approved_by    = request.user
        question.save()
        messages.success(request, "Question approved.")
        return redirect('question_bank_detail', bank_id=question.bank.id)

    return render(request, 'exam_system/approve_question.html', {
        'question': question,
    })


@login_required
def bulk_approve_questions(request, bank_id):
    """Ek saath multiple questions approve karo."""
    bank = get_object_or_404(QuestionBank, id=bank_id)

    if request.method == 'POST':
        question_ids = request.POST.getlist('question_ids')
        if question_ids:
            updated = Question.objects.filter(
                id__in=question_ids, bank=bank
            ).update(human_approved=True, approved_by=request.user)
            messages.success(request, f"{updated} questions approved.")
        else:
            messages.warning(request, "No question was selected.")

    return redirect('question_bank_detail', bank_id=bank.id)


@login_required
def toggle_approve_question(request, question_id):
    """AJAX: Question approve/unapprove toggle."""
    question = get_object_or_404(Question, id=question_id)

    if request.method == 'POST':
        question.human_approved = not question.human_approved
        if question.human_approved:
            question.approved_by = request.user
        else:
            question.approved_by = None
        question.save()

        return JsonResponse({
            'approved': question.human_approved,
            'message':  'Approved' if question.human_approved else 'Unapproved',
        })

    return JsonResponse({'error': 'Invalid request'}, status=400)


# =============================================================
# SECTION 5: AI QUESTION GENERATION — Topic se
# =============================================================

@login_required
def ai_generate_questions(request, bank_id):
    """Topic enter karo → Groq AI se questions generate karo."""
    bank = get_object_or_404(QuestionBank, id=bank_id)

    if request.method == 'POST':
        topic      = request.POST.get('topic', '').strip()
        difficulty = request.POST.get('difficulty', 'MEDIUM')
        q_type     = request.POST.get('question_type', 'MCQ')
        count      = int(request.POST.get('count', 5))

        if not topic:
            messages.error(request, "Please enter a topic.")
            return redirect('ai_generate_questions', bank_id=bank.id)

        try:
            generated = generate_questions_ai(
                topic=topic,
                difficulty=difficulty,
                question_type=q_type,
                count=count,
                subject_name=bank.subject.name,
                class_name=bank.class_fk.class_name,
            )

            saved_count = 0
            for q_data in generated:
                q_text = q_data.get('question', '').strip()
                if not q_text:
                    continue
                Question.objects.create(
                    bank=bank,
                    question_type=q_type,
                    text=q_text,
                    marks=q_data.get('marks', 1),
                    difficulty=difficulty,
                    correct_answer=q_data.get('answer', ''),
                    option_a=q_data.get('option_a'),
                    option_b=q_data.get('option_b'),
                    option_c=q_data.get('option_c'),
                    option_d=q_data.get('option_d'),
                    topic_tag=topic,
                    ai_generated=True,
                    human_approved=False,
                )
                saved_count += 1

            messages.success(
                request,
                f"{saved_count} questions generated by AI! Review them to approve."
            )

        except Exception as e:
            messages.error(request, f"AI generation failed: {str(e)}")

        return redirect('question_bank_detail', bank_id=bank.id)

    return render(request, 'exam_system/ai_generate_questions.html', {
        'bank':        bank,
        'difficulties': Question.DIFFICULTY_LEVELS,
        'q_types':     Question.QUESTION_TYPES,
    })


# =============================================================
# SECTION 6: EXAM PLAN VIEWS
# =============================================================

@login_required
def exam_plan_list(request):
    """Sab exam plans."""
    academic_year = get_active_year()
    plans = ExamPlan.objects.filter(
        academic_year=academic_year
    ).prefetch_related('schedules').order_by('-created_at')

    return render(request, 'exam_system/exam_plan_list.html', {
        'plans':      plans,
        'exam_types': ExamPlan.EXAM_TYPES,
    })


@login_required
def create_exam_plan(request):
    """Naya exam plan banao."""
    academic_year = get_active_year()

    if request.method == 'POST':
        start_date = request.POST.get('start_date')
        end_date = request.POST.get('end_date')

        # Guard against malformed dates (e.g. a 2-digit year typed as 0026)
        from datetime import datetime
        for label, value in [('Start date', start_date), ('End date', end_date)]:
            try:
                parsed = datetime.strptime(value, '%Y-%m-%d')
                if parsed.year < 2000 or parsed.year > 2100:
                    raise ValueError
            except (ValueError, TypeError):
                messages.error(request, f"{label} is invalid. Please pick a valid date.")
                classes = Class.objects.all()
                return render(request, 'exam_system/create_exam_plan.html', {
                    'classes':       classes,
                    'exam_types':    ExamPlan.EXAM_TYPES,
                    'academic_year': academic_year,
                })

        plan = ExamPlan.objects.create(
            title=request.POST.get('title'),
            academic_year=academic_year,
            exam_type=request.POST.get('exam_type'),
            class_fk_id=request.POST.get('class_id'),
            start_date=start_date,
            end_date=end_date,
            created_by=request.user,
        )
        messages.success(request, f"Exam plan '{plan.title}' was created successfully.")
        return redirect('exam_plan_detail', plan_id=plan.id)

    classes = Class.objects.all()
    return render(request, 'exam_system/create_exam_plan.html', {
        'classes':       classes,
        'exam_types':    ExamPlan.EXAM_TYPES,
        'academic_year': academic_year,
    })


@login_required
def exam_plan_detail(request, plan_id):
    plan       = get_object_or_404(ExamPlan, id=plan_id)
    schedules  = ExamSchedule.objects.filter(exam_plan=plan).select_related('subject')
    blueprints = PaperBlueprint.objects.filter(exam_plan=plan).select_related('subject')
    papers     = GeneratedPaper.objects.filter(
                     blueprint__exam_plan=plan
                 ).select_related('blueprint__subject')

    return render(request, 'exam_system/exam_plan_detail.html', {
        'plan':       plan,
        'schedules':  schedules,
        'blueprints': blueprints,
        'papers':     papers,
    })


@login_required
def add_exam_schedule(request, plan_id):
    plan               = get_object_or_404(ExamPlan, id=plan_id)
    subjects           = Subject.objects.filter(class_fk=plan.class_fk)
    existing_schedules = ExamSchedule.objects.filter(exam_plan=plan)

    if request.method == 'POST':
        ExamSchedule.objects.create(
            exam_plan=plan,
            subject_id=request.POST.get('subject'),
            exam_date=request.POST.get('exam_date'),
            start_time=request.POST.get('start_time'),
            end_time=request.POST.get('end_time'),
            room=request.POST.get('room', ''),
        )
        messages.success(request, "Schedule added!")
        return redirect('exam_plan_detail', plan_id=plan.id)

    return render(request, 'exam_system/add_schedule.html', {
        'plan':               plan,
        'subjects':           subjects,
        'existing_schedules': existing_schedules,
    })


@login_required
def create_blueprint(request, plan_id, subject_id):
    """Blueprint banao — marks distribution define karo."""
    plan    = get_object_or_404(ExamPlan, id=plan_id)
    subject = get_object_or_404(Subject, id=subject_id)

    blueprint, _ = PaperBlueprint.objects.get_or_create(
        exam_plan=plan,
        subject=subject,
        defaults={'created_by': request.user},
    )

    if request.method == 'POST':
        blueprint.total_marks   = request.POST.get('total_marks', 100)
        blueprint.passing_marks = request.POST.get('passing_marks', 40)
        blueprint.save()

        blueprint.rules.all().delete()
        q_types = request.POST.getlist('question_type')
        counts  = request.POST.getlist('count')
        marks   = request.POST.getlist('marks_each')
        easy    = request.POST.getlist('easy_percent')
        medium  = request.POST.getlist('medium_percent')
        hard    = request.POST.getlist('hard_percent')

        for i in range(len(q_types)):
            BlueprintRule.objects.create(
                blueprint=blueprint,
                question_type=q_types[i],
                count=int(counts[i]),
                marks_each=int(marks[i]),
                easy_percent=int(easy[i]),
                medium_percent=int(medium[i]),
                hard_percent=int(hard[i]),
            )

        messages.success(request, "Blueprint saved successfully.")
        return redirect('exam_plan_detail', plan_id=plan.id)

    return render(request, 'exam_system/create_blueprint.html', {
        'plan':      plan,
        'subject':   subject,
        'blueprint': blueprint,
        'q_types':   Question.QUESTION_TYPES,
    })


# =============================================================
# SECTION 7: PAPER GENERATION + APPROVAL
# =============================================================

@login_required
def generate_paper_view(request, blueprint_id):
    """Blueprint se paper generate karo."""
    blueprint = get_object_or_404(PaperBlueprint, id=blueprint_id)

    # ── Question Bank stats nikaalo (yehi missing tha) ────────
    bank = QuestionBank.objects.filter(
        subject=blueprint.subject,
        class_fk=blueprint.exam_plan.class_fk,
        academic_year=blueprint.exam_plan.academic_year,
    ).first()

    bank_stats = None
    if bank:
        bank_stats = {
            'total':    bank.questions.count(),
            'approved': bank.questions.filter(human_approved=True).count(),
        }

    if request.method == 'POST':
        paper_set  = request.POST.get('paper_set', 'SINGLE')
        section_id = request.POST.get('section_id')

        try:
            with transaction.atomic():
                paper = GeneratedPaper.objects.create(
                    blueprint=blueprint,
                    section_id=section_id if section_id else None,
                    paper_set=paper_set,
                    generated_by=request.user,
                    status='DRAFT',
                )

                selected_questions = generate_paper_from_blueprint(blueprint)
                paper.questions.set(selected_questions)

                for stage in ['TEACHER', 'COORDINATOR', 'ACADEMIC_HEAD', 'CONTROLLER']:
                    PaperApproval.objects.create(
                        paper=paper, stage=stage, status='PENDING'
                    )

                messages.success(
                    request,
                    f"Paper Set {paper_set} generated successfully "
                    f"({len(selected_questions)} questions). Sent for review."
                )
                return redirect('paper_approval_detail', paper_id=paper.id)

        except ValueError as e:
            messages.error(request, f"{str(e)}")
        except Exception as e:
            messages.error(request, f"Paper generation failed: {str(e)}")

        return redirect('exam_plan_detail', plan_id=blueprint.exam_plan.id)

    sections = Section.objects.filter(class_fk=blueprint.exam_plan.class_fk)
    return render(request, 'exam_system/generate_paper.html', {
        'blueprint':   blueprint,
        'sections':    sections,
        'set_choices': GeneratedPaper.SET_CHOICES,
        'bank_stats':  bank_stats,   # ← ye line add hui
    })


@login_required
def admin_paper_queue(request):
    """Central Controller/Admin dashboard — shows every generated paper and where it
    currently sits in the approval workflow. This is the missing link that made
    generated papers invisible on the admin side."""
    status_filter = request.GET.get('status', '')

    papers = GeneratedPaper.objects.select_related(
        'blueprint__subject', 'blueprint__exam_plan__class_fk', 'generated_by'
    ).prefetch_related('approvals').order_by('-created_at')

    if status_filter:
        papers = papers.filter(status=status_filter)

    pending_count  = GeneratedPaper.objects.exclude(status__in=['LOCKED', 'REJECTED']).count()
    locked_count   = GeneratedPaper.objects.filter(status='LOCKED').count()
    rejected_count = GeneratedPaper.objects.filter(status='REJECTED').count()

    return render(request, 'exam_system/admin_paper_queue.html', {
        'papers': papers,
        'status_choices': GeneratedPaper.STATUS_CHOICES,
        'status_filter': status_filter,
        'pending_count': pending_count,
        'locked_count': locked_count,
        'rejected_count': rejected_count,
    })


# @login_required
# def paper_approval_detail(request, paper_id):
#     """4-level approval workflow."""
#     paper     = get_object_or_404(GeneratedPaper, id=paper_id)
#     approvals = paper.approvals.all().order_by('stage')
#     questions = paper.questions.all().order_by('question_type')

#     if request.method == 'POST':
#         stage   = request.POST.get('stage')
#         action  = request.POST.get('action')
#         remarks = request.POST.get('remarks', '')

#         approval             = get_object_or_404(PaperApproval, paper=paper, stage=stage)
#         approval.status      = 'APPROVED' if action == 'approve' else 'REJECTED'
#         approval.reviewed_by = request.user
#         approval.remarks     = remarks
#         approval.save()

#         if action == 'approve':
#             if stage == 'TEACHER':
#                 messages.success(request, "Approved by the Subject Teacher! You can now upload the PDF.")
#                 return redirect('upload_pdf_for_paper', paper_id=paper.id)

#             if paper.approvals.filter(status='APPROVED').count() == 4:
#                 paper.status = 'LOCKED'
#                 messages.success(request, "Paper fully approved and locked!")
#             else:
#                 paper.status = 'REVIEW'
#                 messages.success(request, f"Stage '{stage}' approved. Waiting for the next reviewer.")
#         else:
#             paper.status = 'REJECTED'
#             messages.error(request, f"Paper rejected at the '{stage}' stage.")

#         paper.save()
#         return redirect('paper_approval_detail', paper_id=paper.id)

#     return render(request, 'exam_system/paper_approval_detail.html', {
#         'paper':     paper,
#         'approvals': approvals,
#         'questions': questions,
#     })



  

@login_required
def paper_approval_detail(request, paper_id):
    """4-level approval workflow."""
    paper     = get_object_or_404(GeneratedPaper, id=paper_id)
    approvals = paper.approvals.all().order_by('stage')
    questions = paper.questions.all().order_by('question_type')

    if request.method == 'POST':
        stage   = request.POST.get('stage')
        action  = request.POST.get('action')
        remarks = request.POST.get('remarks', '')

        approval             = get_object_or_404(PaperApproval, paper=paper, stage=stage)
        approval.status      = 'APPROVED' if action == 'approve' else 'REJECTED'
        approval.reviewed_by = request.user
        approval.remarks     = remarks
        approval.save()

        if action == 'approve':
            all_approved = paper.approvals.filter(status='APPROVED').count() == 4

            if all_approved:
                # ── Sab 4 stages approve ho chuke — lock karo aur PDF banao ──
                paper.status = 'LOCKED'
                paper.save()
                try:
                    generate_paper_pdf(paper)
                    messages.success(request, "Paper fully approved and locked! PDF is ready to download.")
                except Exception as e:
                    messages.error(request, f"Approved, but PDF generation failed: {str(e)}")
                return redirect('paper_approval_detail', paper_id=paper.id)

            # Abhi tak sab approve nahi hue
            paper.status = 'REVIEW'
            paper.save()

            if stage == 'TEACHER':
                messages.success(
                    request,
                    "Approved by the Subject Teacher! You can optionally upload a supporting "
                    "PDF here, or wait for the remaining approvals."
                )
                return redirect('upload_pdf_for_paper', paper_id=paper.id)

            messages.success(request, f"Stage '{stage}' approved. Waiting for the next reviewer.")

        else:
            paper.status = 'REJECTED'
            paper.save()
            messages.error(request, f"Paper rejected at the '{stage}' stage.")

        return redirect('paper_approval_detail', paper_id=paper.id)

    return render(request, 'exam_system/paper_approval_detail.html', {
        'paper':     paper,
        'approvals': approvals,
        'questions': questions,
    })
    

@login_required
def upload_pdf_for_paper(request, paper_id):
    """Subject Teacher PDF upload kare → Groq AI se questions → Paper mein add."""
    paper     = get_object_or_404(GeneratedPaper, id=paper_id)
    blueprint = paper.blueprint

    if request.method == 'POST':
        pdf_file   = request.FILES.get('pdf_file')
        difficulty = request.POST.get('difficulty', 'MEDIUM')

        if not pdf_file:
            messages.error(request, "Please upload a PDF file.")
            return redirect('upload_pdf_for_paper', paper_id=paper.id)

        if not pdf_file.name.lower().endswith('.pdf'):
            messages.error(request, "Only PDF files are allowed.")
            return redirect('upload_pdf_for_paper', paper_id=paper.id)

        if pdf_file.size > 15 * 1024 * 1024:
            messages.error(request, "File must not be larger than 15MB.")
            return redirect('upload_pdf_for_paper', paper_id=paper.id)

        try:
            text = _extract_pdf_text(pdf_file)

            if not text or len(text.strip()) < 50:
                messages.error(request, "Could not extract text from this PDF. Please use a text-based PDF.")
                return redirect('upload_pdf_for_paper', paper_id=paper.id)

            rules = blueprint.rules.all()
            if not rules.exists():
                messages.error(request, "This blueprint has no rules defined yet.")
                return redirect('upload_pdf_for_paper', paper_id=paper.id)

            groq_client = Groq(api_key=settings.GROQ_API_KEY)

            bank, _ = QuestionBank.objects.get_or_create(
                subject=blueprint.subject,
                class_fk=blueprint.exam_plan.class_fk,
                academic_year=blueprint.exam_plan.academic_year,
                defaults={'created_by': request.user},
            )

            total_saved = 0

            for rule in rules:
                type_map = {
                    'MCQ':        'multiple-choice questions with 4 options (A,B,C,D) and one correct answer',
                    'SHORT':      'short-answer questions with model answer',
                    'LONG':       'long/essay questions with model answer',
                    'CONCEPTUAL': 'conceptual questions with model answer',
                    'PRACTICAL':  'practical questions with model answer',
                }

                prompt = f"""
You are an expert exam question generator for {blueprint.subject.name} — Class {blueprint.exam_plan.class_fk.class_name}.

Based on this content, generate exactly {rule.count} {type_map.get(rule.question_type, 'questions')}.
Difficulty: {difficulty}.

Content:
\"\"\"
{text[:5000]}
\"\"\"

Return ONLY a valid JSON array. No explanation, no markdown.

For MCQ:
{{"type":"MCQ","question":"...?","option_a":"...","option_b":"...","option_c":"...","option_d":"...","correct_answer":"option_a","marks":{rule.marks_each}}}

For SHORT/LONG:
{{"type":"{rule.question_type}","question":"...?","option_a":null,"option_b":null,"option_c":null,"option_d":null,"correct_answer":"model answer here","marks":{rule.marks_each}}}

Generate exactly {rule.count} questions now:"""

                try:
                    generated = _groq_generate(groq_client, prompt)
                except json.JSONDecodeError:
                    messages.warning(request, f"AI response was unexpected for {rule.question_type}. Skipped.")
                    continue

                for q_data in generated:
                    q_text = q_data.get('question', '').strip()
                    if not q_text:
                        continue

                    question = Question.objects.create(
                        bank=bank,
                        question_type=rule.question_type,
                        text=q_text,
                        marks=q_data.get('marks', rule.marks_each),
                        difficulty=difficulty,
                        option_a=q_data.get('option_a'),
                        option_b=q_data.get('option_b'),
                        option_c=q_data.get('option_c'),
                        option_d=q_data.get('option_d'),
                        correct_answer=q_data.get('correct_answer', ''),
                        topic_tag=f"PDF: {pdf_file.name}",
                        ai_generated=True,
                        human_approved=True,
                    )
                    paper.questions.add(question)
                    total_saved += 1

            paper.status = 'REVIEW'
            paper.save()

            messages.success(
                request,
                f"{total_saved} questions generated from the PDF and added to the paper!"
            )
            return redirect('paper_approval_detail', paper_id=paper.id)

        except Exception as e:
            import traceback
            traceback.print_exc()
            messages.error(request, f"Error: {str(e)}")

    rules   = blueprint.rules.all()
    total_q = sum(r.count for r in rules)

    return render(request, 'exam_system/upload_pdf_for_paper.html', {
        'paper':     paper,
        'blueprint': blueprint,
        'rules':     rules,
        'total_q':   total_q,
    })


@login_required
def download_paper(request, paper_id):
    """Secure paper download."""
    paper = get_object_or_404(GeneratedPaper, id=paper_id)

    PaperAccessLog.objects.create(
        paper=paper,
        accessed_by=request.user,
        action='DOWNLOAD',
        ip_address=request.META.get('REMOTE_ADDR'),
    )

    if not paper.is_unlocked():
        messages.error(
            request,
            f"This paper is still locked. Unlock time: {paper.unlock_time:%d %b %Y %I:%M %p}"
        )
        return redirect('paper_approval_detail', paper_id=paper.id)

    if paper.status != 'LOCKED':
        messages.error(request, "This paper is not approved yet. Download is not allowed.")
        return redirect('paper_approval_detail', paper_id=paper.id)

    if paper.pdf_file:
        response = HttpResponse(paper.pdf_file, content_type='application/pdf')
        response['Content-Disposition'] = (
            f'attachment; filename="paper_{paper.id}_{paper.paper_set}.pdf"'
        )
        return response

    messages.error(request, "No PDF file is available.")
    return redirect('paper_approval_detail', paper_id=paper.id)


# =============================================================
# SECTION 8: EXAM CONDUCT
# =============================================================

@login_required
def exam_conduct_dashboard(request, schedule_id):
    schedule     = get_object_or_404(ExamSchedule, id=schedule_id)
    seating      = ExamSeatingPlan.objects.filter(schedule=schedule).select_related('student')
    attendance   = ExamAttendance.objects.filter(schedule=schedule).select_related('student')
    attended_ids = set(attendance.filter(status='PRESENT').values_list('student_id', flat=True))

    return render(request, 'exam_system/exam_conduct_dashboard.html', {
        'schedule':     schedule,
        'seating':      seating,
        'attendance':   attendance,
        'attended_ids': attended_ids,
    })


@login_required
def mark_exam_attendance(request, schedule_id):
    schedule = get_object_or_404(ExamSchedule, id=schedule_id)
    teacher  = get_object_or_404(Teacher, user=request.user)

    is_invigilator = InvigilatorDuty.objects.filter(
        schedule=schedule, teacher=teacher
    ).exists()

    if not is_invigilator and not request.user.is_staff:
        return HttpResponse("You are not the invigilator for this exam.")

    students = Student.objects.filter(
        class_fk=schedule.exam_plan.class_fk
    ).order_by('roll_no')

    if request.method == 'POST':
        for student in students:
            status = request.POST.get(f'status_{student.id}', 'ABSENT')
            ExamAttendance.objects.update_or_create(
                schedule=schedule,
                student=student,
                defaults={'status': status, 'marked_by': teacher},
            )
        messages.success(request, "Exam attendance marked.")
        return redirect('exam_conduct_dashboard', schedule_id=schedule.id)

    existing = {
        ea.student_id: ea.status
        for ea in ExamAttendance.objects.filter(schedule=schedule)
    }

    return render(request, 'exam_system/mark_exam_attendance.html', {
        'schedule': schedule,
        'students': students,
        'existing': existing,
    })


@login_required
def auto_generate_seating(request, schedule_id):
    schedule = get_object_or_404(ExamSchedule, id=schedule_id)

    if not request.user.is_staff:
        messages.error(request, "Only an admin can generate the seating plan.")
        return redirect('exam_conduct_dashboard', schedule_id=schedule.id)

    students = Student.objects.filter(
        class_fk=schedule.exam_plan.class_fk
    ).order_by('roll_no')

    ExamSeatingPlan.objects.filter(schedule=schedule).delete()

    for i, student in enumerate(students, start=1):
        ExamSeatingPlan.objects.create(
            schedule=schedule,
            student=student,
            seat_number=f"S{i:03d}",
            room=schedule.room,
        )

    messages.success(request, f"Seating plan generated for {students.count()} students.")
    return redirect('exam_conduct_dashboard', schedule_id=schedule.id)


# =============================================================
# SECTION 9: MARKING
# =============================================================

@login_required
def answer_sheet_list(request, schedule_id):
    schedule = get_object_or_404(ExamSchedule, id=schedule_id)
    sheets   = AnswerSheet.objects.filter(
        schedule=schedule
    ).select_related('student').prefetch_related('scores')

    return render(request, 'exam_system/answer_sheet_list.html', {
        'schedule': schedule,
        'sheets':   sheets,
    })


@login_required
def mark_answer_sheet(request, sheet_id):
    sheet       = get_object_or_404(AnswerSheet, id=sheet_id)
    questions   = sheet.paper.questions.all() if sheet.paper else []
    scores_dict = {
        s.question_id: s
        for s in QuestionScore.objects.filter(answer_sheet=sheet)
    }

    if request.method == 'POST':
        with transaction.atomic():
            for question in questions:
                teacher_score = request.POST.get(f'score_{question.id}')
                remarks       = request.POST.get(f'remarks_{question.id}', '')

                if teacher_score not in (None, ''):
                    score_obj, _ = QuestionScore.objects.get_or_create(
                        answer_sheet=sheet, question=question
                    )
                    score_obj.teacher_score   = teacher_score
                    score_obj.teacher_remarks = remarks
                    score_obj.verified_by     = request.user
                    score_obj.save()

        messages.success(request, f"Result saved for {sheet.student.name}.")
        return redirect('answer_sheet_list', schedule_id=sheet.schedule.id)

    return render(request, 'exam_system/mark_answer_sheet.html', {
        'sheet':       sheet,
        'questions':   questions,
        'scores_dict': scores_dict,
    })


# =============================================================
# SECTION 10: RESULTS + ANALYTICS
# =============================================================

@login_required
def compile_exam_results(request, schedule_id):
    schedule = get_object_or_404(ExamSchedule, id=schedule_id)

    if not request.user.is_staff:
        messages.error(request, "Only an admin can compile results.")
        return redirect('answer_sheet_list', schedule_id=schedule.id)

    if request.method == 'POST':
        try:
            compiled_count = compile_results(schedule)
            messages.success(request, f"Results compiled for {compiled_count} students.")
        except Exception as e:
            messages.error(request, f"Result compilation failed: {str(e)}")
        return redirect('exam_results_list', schedule_id=schedule.id)

    return render(request, 'exam_system/compile_results_confirm.html', {
        'schedule': schedule,
    })


@login_required
def exam_results_list(request, schedule_id):
    schedule = get_object_or_404(ExamSchedule, id=schedule_id)
    results  = CentralizedResult.objects.filter(
        answer_sheet__schedule=schedule
    ).select_related('answer_sheet__student').order_by('class_position')

    pass_count = results.filter(is_pass=True).count()
    fail_count = results.filter(is_pass=False).count()
    total      = results.count()

    return render(request, 'exam_system/exam_results_list.html', {
        'schedule':   schedule,
        'results':    results,
        'pass_count': pass_count,
        'fail_count': fail_count,
        'total':      total,
        'pass_rate':  round((pass_count / total * 100), 1) if total else 0,
    })


@login_required
def analytics_dashboard(request):
    from django.db.models import Count, Avg

    academic_year = get_active_year()
    plans = ExamPlan.objects.filter(
        academic_year=academic_year,
        is_published=True,
    ).prefetch_related('schedules__exam_attendance')

    subject_stats = CentralizedResult.objects.filter(
        answer_sheet__schedule__exam_plan__academic_year=academic_year
    ).values(
        'answer_sheet__schedule__subject__name'
    ).annotate(
        avg_pct=Avg('percentage'),
        total=Count('id'),
    ).order_by('-avg_pct')

    grade_dist = CentralizedResult.objects.filter(
        answer_sheet__schedule__exam_plan__academic_year=academic_year
    ).values('grade').annotate(count=Count('id')).order_by('grade')

    return render(request, 'exam_system/analytics_dashboard.html', {
        'academic_year': academic_year,
        'plans':         plans,
        'subject_stats': subject_stats,
        'grade_dist':    grade_dist,
    })

# =============================================================
# exam_views.py
# Ye code aapke existing teacher_dashboard/views.py mein
# ADD karna hai — same style, same patterns
# =============================================================

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from django.http import HttpResponse, JsonResponse
from django.db import transaction
import json

# Aapke existing imports (already aapke views.py mein hain)
from teacher_dashboard.models import Teacher
from student_profile.models import Student
from admin_panel.models import (
    Class, Section, Subject, AcademicYear,
    AssignedPeriod
)

# Naye exam system ke models
from exam_system.models import (
    QuestionBank, Question,
    ExamPlan, ExamSchedule, PaperBlueprint, BlueprintRule,
    GeneratedPaper, PaperApproval, PaperAccessLog,
    ExamSeatingPlan, InvigilatorDuty,
    ExamAttendance, AnswerSheet, QuestionScore,
    CentralizedResult,
)

# AI service (alag file mein — neeche diya hai)
from exam_system.services import generate_questions_ai, generate_paper_from_blueprint, compile_results


# =============================================================
# HELPER — aapka existing pattern same rakha
# =============================================================

def get_active_year():
    return AcademicYear.objects.filter(is_active=True).first()


# =============================================================
# SECTION 1: QUESTION BANK VIEWS
# (Subject Coordinator / Teacher use karta hai)
# =============================================================

@login_required
def question_bank_list(request):
    """
    Sab question banks dikhao.
    Admin ya coordinator ke liye.
    """
    academic_year = get_active_year()
    banks = QuestionBank.objects.filter(
        academic_year=academic_year
    ).select_related('subject', 'class_fk', 'created_by')

    return render(request, 'exam_system/question_bank_list.html', {
        'banks': banks,
        'academic_year': academic_year,
    })


@login_required
def question_bank_detail(request, bank_id):
    """
    Ek bank ke sab questions.
    Filter by type/difficulty.
    """
    bank = get_object_or_404(QuestionBank, id=bank_id)

    q_type  = request.GET.get('type', '')
    diff    = request.GET.get('difficulty', '')
    approved_only = request.GET.get('approved', '')

    questions = bank.questions.all()

    if q_type:
        questions = questions.filter(question_type=q_type)
    if diff:
        questions = questions.filter(difficulty=diff)
    if approved_only == '1':
        questions = questions.filter(human_approved=True)

    return render(request, 'exam_system/question_bank_detail.html', {
        'bank': bank,
        'questions': questions,
        'q_types': Question.QUESTION_TYPES,
        'difficulties': Question.DIFFICULTY_LEVELS,
    })


@login_required
def add_question_to_bank(request, bank_id):
    """
    Teacher manually question add kare.
    Aapke existing add_question view ki tarah.
    """
    bank = get_object_or_404(QuestionBank, id=bank_id)

    if request.method == 'POST':
        Question.objects.create(
            bank=bank,
            question_type=request.POST.get('question_type'),
            text=request.POST.get('text'),
            marks=request.POST.get('marks', 1),
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
        messages.success(request, "Question added successfully.")
        return redirect('question_bank_detail', bank_id=bank.id)

    return render(request, 'exam_system/add_question.html', {
        'bank': bank,
        'q_types': Question.QUESTION_TYPES,
        'difficulties': Question.DIFFICULTY_LEVELS,
        'bloom_levels': Question.BLOOM_LEVELS,
    })


@login_required
def approve_question(request, question_id):
    """
    Coordinator ya Academic Head question approve kare.
    """
    question = get_object_or_404(Question, id=question_id)

    if request.method == 'POST':
        question.human_approved = True
        question.approved_by = request.user
        question.save()
        messages.success(request, f"Question approved.")
        return redirect('question_bank_detail', bank_id=question.bank.id)

    return render(request, 'exam_system/approve_question.html', {
        'question': question,
    })


@login_required
def ai_generate_questions(request, bank_id):
    """
    AI se questions generate karo.
    Celery task ya synchronous — aapki choice.
    """
    bank = get_object_or_404(QuestionBank, id=bank_id)

    if request.method == 'POST':
        topic       = request.POST.get('topic', '')
        difficulty  = request.POST.get('difficulty', 'MEDIUM')
        q_type      = request.POST.get('question_type', 'MCQ')
        count       = int(request.POST.get('count', 5))

        try:
            generated = generate_questions_ai(
                topic=topic,
                difficulty=difficulty,
                question_type=q_type,
                count=count,
                subject_name=bank.subject.name,
                class_name=bank.class_fk.class_name,
            )

            for q_data in generated:
                Question.objects.create(
                    bank=bank,
                    question_type=q_type,
                    text=q_data.get('question', ''),
                    marks=q_data.get('marks', 1),
                    difficulty=difficulty,
                    correct_answer=q_data.get('answer', ''),
                    option_a=q_data.get('option_a'),
                    option_b=q_data.get('option_b'),
                    option_c=q_data.get('option_c'),
                    option_d=q_data.get('option_d'),
                    topic_tag=topic,
                    ai_generated=True,
                    human_approved=False,   # review baad mein hogi
                )

            messages.success(request, f"{len(generated)} questions AI se generate ho gaye. Review karo.")
        except Exception as e:
            messages.error(request, f"AI generation failed: {str(e)}")

        return redirect('question_bank_detail', bank_id=bank.id)

    return render(request, 'exam_system/ai_generate_questions.html', {
        'bank': bank,
        'difficulties': Question.DIFFICULTY_LEVELS,
        'q_types': Question.QUESTION_TYPES,
    })


# =============================================================
# SECTION 2: EXAM PLAN + BLUEPRINT VIEWS
# (Examination Controller / Head Office)
# =============================================================

@login_required
def exam_plan_list(request):
    """
    Sab exam plans — filter by year/type.
    """
    academic_year = get_active_year()
    plans = ExamPlan.objects.filter(
        academic_year=academic_year
    ).prefetch_related('schedules').order_by('-created_at')

    return render(request, 'exam_system/exam_plan_list.html', {
        'plans': plans,
        'exam_types': ExamPlan.EXAM_TYPES,
    })


@login_required
def create_exam_plan(request):
    """
    Naya exam plan banao.
    Head Office ya Examination Controller.
    """
    academic_year = get_active_year()

    if request.method == 'POST':
        plan = ExamPlan.objects.create(
            title=request.POST.get('title'),
            academic_year=academic_year,
            exam_type=request.POST.get('exam_type'),
            class_fk_id=request.POST.get('class_id'),
            start_date=request.POST.get('start_date'),
            end_date=request.POST.get('end_date'),
            created_by=request.user,
        )
        messages.success(request, f"Exam plan '{plan.title}' create ho gaya.")
        return redirect('exam_plan_detail', plan_id=plan.id)

    classes = Class.objects.all()
    return render(request, 'exam_system/create_exam_plan.html', {
        'classes': classes,
        'exam_types': ExamPlan.EXAM_TYPES,
        'academic_year': academic_year,
    })


@login_required
def exam_plan_detail(request, plan_id):
    """
    Ek plan ka detail — schedules + blueprints.
    """
    plan = get_object_or_404(ExamPlan, id=plan_id)
    schedules = plan.schedules.select_related('subject').all()
    blueprints = plan.blueprints.select_related('subject').prefetch_related('rules').all()

    return render(request, 'exam_system/exam_plan_detail.html', {
        'plan': plan,
        'schedules': schedules,
        'blueprints': blueprints,
    })


@login_required
def add_exam_schedule(request, plan_id):
    """
    Exam plan mein subject ka date/time add karo.
    """
    plan = get_object_or_404(ExamPlan, id=plan_id)

    if request.method == 'POST':
        ExamSchedule.objects.create(
            exam_plan=plan,
            subject_id=request.POST.get('subject_id'),
            exam_date=request.POST.get('exam_date'),
            start_time=request.POST.get('start_time'),
            end_time=request.POST.get('end_time'),
            room=request.POST.get('room', ''),
        )
        messages.success(request, "Schedule add ho gaya.")
        return redirect('exam_plan_detail', plan_id=plan.id)

    # Class ke subjects
    subjects = Subject.objects.filter(
        assignedperiod__class_fk=plan.class_fk
    ).distinct()

    return render(request, 'exam_system/add_schedule.html', {
        'plan': plan,
        'subjects': subjects,
    })


@login_required
def create_blueprint(request, plan_id, subject_id):
    """
    Blueprint banao — marks distribution define karo.
    """
    plan    = get_object_or_404(ExamPlan, id=plan_id)
    subject = get_object_or_404(Subject, id=subject_id)

    blueprint, created = PaperBlueprint.objects.get_or_create(
        exam_plan=plan,
        subject=subject,
        defaults={'created_by': request.user}
    )

    if request.method == 'POST':
        # Total marks update
        blueprint.total_marks   = request.POST.get('total_marks', 100)
        blueprint.passing_marks = request.POST.get('passing_marks', 40)
        blueprint.save()

        # Rules save karo
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
        'plan': plan,
        'subject': subject,
        'blueprint': blueprint,
        'q_types': Question.QUESTION_TYPES,
    })


# =============================================================
# SECTION 3: PAPER GENERATION + APPROVAL VIEWS
# =============================================================

@login_required
def generate_paper_view(request, blueprint_id):
    """
    AI ya manual paper generate karo blueprint se.
    Aapke generate_lesson_plan_for_topic ki tarah.
    """
    blueprint = get_object_or_404(PaperBlueprint, id=blueprint_id)

    if request.method == 'POST':
        paper_set = request.POST.get('paper_set', 'SINGLE')
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

                # Blueprint ke rules se questions select karo
                selected_questions = generate_paper_from_blueprint(blueprint)
                paper.questions.set(selected_questions)

                # Initial approval workflow create karo
                stages = ['TEACHER', 'COORDINATOR', 'ACADEMIC_HEAD', 'CONTROLLER']
                for stage in stages:
                    PaperApproval.objects.create(
                        paper=paper,
                        stage=stage,
                        status='PENDING',
                    )

                messages.success(request, f"Paper Set {paper_set} generate ho gaya. Review ke liye bheja.")
                return redirect('paper_approval_detail', paper_id=paper.id)

        except Exception as e:
            messages.error(request, f"Paper generation failed: {str(e)}")
            return redirect('exam_plan_detail', plan_id=blueprint.exam_plan.id)

    sections = Section.objects.filter(class_fk=blueprint.exam_plan.class_fk)

    return render(request, 'exam_system/generate_paper.html', {
        'blueprint': blueprint,
        'sections': sections,
        'set_choices': GeneratedPaper.SET_CHOICES,
    })


@login_required
def paper_approval_detail(request, paper_id):
    """
    4-level approval workflow.
    Aapke teacher_appraisal_submit ki tarah — stage-wise.
    """
    paper = get_object_or_404(GeneratedPaper, id=paper_id)
    approvals = paper.approvals.all().order_by('stage')
    questions = paper.questions.all().order_by('question_type')

    if request.method == 'POST':
        stage  = request.POST.get('stage')
        action = request.POST.get('action')   # 'approve' or 'reject'
        remarks = request.POST.get('remarks', '')

        approval = get_object_or_404(PaperApproval, paper=paper, stage=stage)
        approval.status      = 'APPROVED' if action == 'approve' else 'REJECTED'
        approval.reviewed_by = request.user
        approval.remarks     = remarks
        approval.save()

        # Agar sab approved to paper LOCKED karo
        if action == 'approve':
            all_approved = paper.approvals.filter(status='APPROVED').count() == 4
            if all_approved:
                paper.status = 'LOCKED'
                paper.save()
                messages.success(request, "Paper fully approved aur locked ho gaya!")
            else:
                paper.status = 'REVIEW'
                paper.save()
                messages.success(request, f"Stage '{stage}' approved. Next reviewer ka wait karo.")
        else:
            paper.status = 'REJECTED'
            paper.save()
            messages.error(request, f"Paper '{stage}' stage pe reject ho gaya.")

        return redirect('paper_approval_detail', paper_id=paper.id)

    return render(request, 'exam_system/paper_approval_detail.html', {
        'paper': paper,
        'approvals': approvals,
        'questions': questions,
    })


@login_required
def download_paper(request, paper_id):
    """
    Secure paper download — sirf unlock time ke baad.
    Aapke PaperAccessLog mein log hoga.
    """
    paper = get_object_or_404(GeneratedPaper, id=paper_id)

    # Access log
    PaperAccessLog.objects.create(
        paper=paper,
        accessed_by=request.user,
        action='DOWNLOAD',
        ip_address=request.META.get('REMOTE_ADDR'),
    )

    # Time lock check
    if not paper.is_unlocked():
        messages.error(
            request,
            f"Paper abhi locked hai. Unlock time: {paper.unlock_time:%d %b %Y %I:%M %p}"
        )
        return redirect('paper_approval_detail', paper_id=paper.id)

    # Status check
    if paper.status != 'LOCKED':
        messages.error(request, "Paper approved nahi hai. Download allowed nahi.")
        return redirect('paper_approval_detail', paper_id=paper.id)

    if paper.pdf_file:
        response = HttpResponse(paper.pdf_file, content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="paper_{paper.id}_{paper.paper_set}.pdf"'
        return response

    messages.error(request, "PDF file available nahi hai.")
    return redirect('paper_approval_detail', paper_id=paper.id)


# =============================================================
# SECTION 4: EXAM CONDUCT VIEWS
# (Campus Admin / Invigilator)
# =============================================================

@login_required
def exam_conduct_dashboard(request, schedule_id):
    """
    Ek exam schedule ka conduct dashboard.
    Invigilator ke liye — seating + attendance.
    """
    schedule = get_object_or_404(ExamSchedule, id=schedule_id)

    seating = ExamSeatingPlan.objects.filter(
        schedule=schedule
    ).select_related('student')

    attendance = ExamAttendance.objects.filter(
        schedule=schedule
    ).select_related('student')

    attended_ids = set(attendance.filter(status='PRESENT').values_list('student_id', flat=True))

    return render(request, 'exam_system/exam_conduct_dashboard.html', {
        'schedule': schedule,
        'seating': seating,
        'attendance': attendance,
        'attended_ids': attended_ids,
    })


@login_required
def mark_exam_attendance(request, schedule_id):
    """
    Exam attendance mark karo.
    Aapke existing mark_attendance view ki tarah.
    """
    schedule = get_object_or_404(ExamSchedule, id=schedule_id)

    # Invigilator check
    teacher = get_object_or_404(Teacher, user=request.user)
    is_invigilator = InvigilatorDuty.objects.filter(
        schedule=schedule, teacher=teacher
    ).exists()

    if not is_invigilator and not request.user.is_staff:
        return HttpResponse("❌ Aap is exam ke invigilator nahi hain.")

    students = Student.objects.filter(
        class_fk=schedule.exam_plan.class_fk
    ).order_by('roll_no')

    if request.method == 'POST':
        for student in students:
            status = request.POST.get(f'status_{student.id}', 'ABSENT')
            ExamAttendance.objects.update_or_create(
                schedule=schedule,
                student=student,
                defaults={
                    'status': status,
                    'marked_by': teacher,
                }
            )
        messages.success(request, "Exam attendance mark ho gayi.")
        return redirect('exam_conduct_dashboard', schedule_id=schedule.id)

    # Existing attendance (agar pehle se mark ki ho)
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
    """
    Auto seating plan generate karo.
    Students ko roll_no se sort karke seat assign karo.
    """
    schedule = get_object_or_404(ExamSchedule, id=schedule_id)

    if not request.user.is_staff:
        messages.error(request, "Sirf admin seating generate kar sakta hai.")
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

    messages.success(request, f"{students.count()} students ki seating plan ban gayi.")
    return redirect('exam_conduct_dashboard', schedule_id=schedule.id)


# =============================================================
# SECTION 5: MARKING VIEWS
# (Teacher / AI)
# =============================================================

@login_required
def answer_sheet_list(request, schedule_id):
    """
    Ek schedule ke sab answer sheets.
    Teacher in pe marks dega.
    """
    schedule = get_object_or_404(ExamSchedule, id=schedule_id)
    sheets = AnswerSheet.objects.filter(
        schedule=schedule
    ).select_related('student').prefetch_related('scores')

    return render(request, 'exam_system/answer_sheet_list.html', {
        'schedule': schedule,
        'sheets': sheets,
    })


@login_required
def mark_answer_sheet(request, sheet_id):
    """
    Teacher ek student ka answer sheet mark kare.
    AI score pehle se aata hai — teacher verify/override kare.
    Aapke upload_result view ki tarah.
    """
    sheet = get_object_or_404(AnswerSheet, id=sheet_id)
    questions = sheet.paper.questions.all() if sheet.paper else []

    # Existing scores
    scores_dict = {
        s.question_id: s
        for s in QuestionScore.objects.filter(answer_sheet=sheet)
    }

    if request.method == 'POST':
        with transaction.atomic():
            for question in questions:
                teacher_score = request.POST.get(f'score_{question.id}')
                remarks       = request.POST.get(f'remarks_{question.id}', '')

                if teacher_score is not None and teacher_score != '':
                    score_obj, _ = QuestionScore.objects.get_or_create(
                        answer_sheet=sheet,
                        question=question,
                    )
                    score_obj.teacher_score   = teacher_score
                    score_obj.teacher_remarks = remarks
                    score_obj.verified_by     = request.user
                    score_obj.save()

        messages.success(request, f"{sheet.student.name} ka result save ho gaya.")
        return redirect('answer_sheet_list', schedule_id=sheet.schedule.id)

    return render(request, 'exam_system/mark_answer_sheet.html', {
        'sheet': sheet,
        'questions': questions,
        'scores_dict': scores_dict,
    })


# =============================================================
# SECTION 6: RESULT COMPILATION + ANALYTICS
# =============================================================

@login_required
def compile_exam_results(request, schedule_id):
    """
    Sab answer sheets ke scores aggregate karo.
    CentralizedResult model mein save karo.
    Admin / Exam Controller ke liye.
    """
    schedule = get_object_or_404(ExamSchedule, id=schedule_id)

    if not request.user.is_staff:
        messages.error(request, "Sirf admin results compile kar sakta hai.")
        return redirect('answer_sheet_list', schedule_id=schedule.id)

    if request.method == 'POST':
        try:
            compiled_count = compile_results(schedule)
            messages.success(request, f"{compiled_count} students ke results compile ho gaye.")
        except Exception as e:
            messages.error(request, f"Result compilation failed: {str(e)}")

        return redirect('exam_results_list', schedule_id=schedule.id)

    return render(request, 'exam_system/compile_results_confirm.html', {
        'schedule': schedule,
    })


@login_required
def exam_results_list(request, schedule_id):
    """
    Compiled results dikhao with ranking.
    Aapke merge_result view ki tarah.
    """
    schedule = get_object_or_404(ExamSchedule, id=schedule_id)
    results = CentralizedResult.objects.filter(
        answer_sheet__schedule=schedule
    ).select_related(
        'answer_sheet__student'
    ).order_by('class_position')

    pass_count = results.filter(is_pass=True).count()
    fail_count = results.filter(is_pass=False).count()
    total = results.count()

    return render(request, 'exam_system/exam_results_list.html', {
        'schedule': schedule,
        'results': results,
        'pass_count': pass_count,
        'fail_count': fail_count,
        'total': total,
        'pass_rate': round((pass_count / total * 100), 1) if total else 0,
    })


@login_required
def analytics_dashboard(request):
    """
    Head Office analytics — campus-wise comparison.
    Aapke appraisal dashboard ki tarah — aggregated data.
    """
    academic_year = get_active_year()

    plans = ExamPlan.objects.filter(
        academic_year=academic_year,
        is_published=True,
    ).prefetch_related('schedules__exam_attendance')

    # Subject-wise pass rates
    from django.db.models import Count, Avg

    subject_stats = CentralizedResult.objects.filter(
        answer_sheet__schedule__exam_plan__academic_year=academic_year
    ).values(
        'answer_sheet__schedule__subject__name'
    ).annotate(
        avg_pct=Avg('percentage'),
        total=Count('id'),
    ).order_by('-avg_pct')

    # Grade distribution
    grade_dist = CentralizedResult.objects.filter(
        answer_sheet__schedule__exam_plan__academic_year=academic_year
    ).values('grade').annotate(count=Count('id')).order_by('grade')

    return render(request, 'exam_system/analytics_dashboard.html', {
        'academic_year': academic_year,
        'plans': plans,
        'subject_stats': subject_stats,
        'grade_dist': grade_dist,
    })

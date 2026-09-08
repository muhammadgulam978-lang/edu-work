"""Action gates for legacy routes that previously checked authentication alone."""
from django.core.exceptions import PermissionDenied


EXAM_ROUTES = {
    'question_bank_list': ('questionbank', 'view'),
    'question_bank_detail': ('questionbank', 'view'),
    'delete_question_bank': ('questionbank', 'delete'),
    'add_question_to_bank': ('question', 'add'),
    'edit_question': ('question', 'change'),
    'approve_question': ('question', 'change'),
    'toggle_approve_question': ('question', 'change'),
    'bulk_approve_questions': ('question', 'change'),
    'ai_generate_questions': ('question', 'add'),
    'upload_book_for_bank': ('question', 'add'),
    'generate_questions_from_pdf': ('question', 'add'),
    'exam_plan_list': ('examplan', 'view'),
    'exam_plan_detail': ('examplan', 'view'),
    'create_exam_plan': ('examplan', 'add'),
    'add_exam_schedule': ('examschedule', 'add'),
    'create_blueprint': ('paperblueprint', 'add'),
    'generate_paper_view': ('generatedpaper', 'add'),
    'admin_paper_queue': ('generatedpaper', 'view'),
    'paper_approval_detail': ('paperapproval', 'view'),
    'upload_pdf_for_paper': ('generatedpaper', 'change'),
    'download_paper': ('generatedpaper', 'view'),
    'exam_conduct_dashboard': ('examschedule', 'view'),
    'mark_exam_attendance': ('examattendance', 'add'),
    'auto_generate_seating': ('examseatingplan', 'add'),
    'answer_sheet_list': ('answersheet', 'view'),
    'mark_answer_sheet': ('questionscore', 'change'),
    'compile_exam_results': ('centralizedresult', 'add'),
    'exam_results_list': ('centralizedresult', 'view'),
    'analytics_dashboard': ('centralizedresult', 'view'),
    'analytics_data': ('centralizedresult', 'view'),
}


def check_route(request, callback, kwargs):
    name, module = callback.__name__, callback.__module__
    if module.startswith('exam_system.'):
        rule = EXAM_ROUTES.get(name)
        if rule is None:
            raise PermissionDenied('This examination endpoint has no authorization policy.')
        model, action = rule
        if name == 'question_bank_list' and request.method == 'POST':
            action = 'add'
        if name == 'paper_approval_detail' and request.method == 'POST':
            action = 'change'
        if not request.user.has_perm(f'exam_system.{action}_{model}'):
            raise PermissionDenied('You do not have permission for this examination action.')
        if 'sheet_id' in kwargs:
            from exam_system.models import AnswerSheet
            from admin_panel.models import AssignedPeriod
            sheet = AnswerSheet.objects.filter(pk=kwargs['sheet_id']).select_related('schedule__subject', 'student').first()
            if sheet:
                if not AssignedPeriod.objects.filter(teacher__user=request.user,
                        subject_id=sheet.schedule.subject_id, class_fk_id=sheet.student.class_fk_id,
                        section_id=sheet.student.section_id).exists():
                    raise PermissionDenied('You are not assigned to mark this student and subject.')
        if 'bank_id' in kwargs or 'question_id' in kwargs:
            from exam_system.access import banks_for
            from exam_system.models import Question
            bank_id = kwargs.get('bank_id')
            if bank_id is None:
                bank_id = Question.objects.filter(pk=kwargs['question_id']).values_list('bank_id', flat=True).first()
            if not banks_for(request.user).filter(pk=bank_id).exists():
                raise PermissionDenied('The question bank is outside your assignment.')
        if name == 'question_bank_list' and request.method == 'POST':
            from admin_panel.models import AssignedPeriod
            if not AssignedPeriod.objects.filter(teacher__user=request.user,
                    class_fk_id=request.POST.get('class_id'), subject_id=request.POST.get('subject_id'),
                    section__academic_year__is_active=True).exists():
                raise PermissionDenied('Creating a bank requires an active class and subject assignment.')
        if 'question_id' in kwargs or (name == 'bulk_approve_questions' and request.method == 'POST'):
            from exam_system.models import GeneratedPaper
            ids = [kwargs['question_id']] if 'question_id' in kwargs else request.POST.getlist('question_ids')
            if request.method == 'POST' and GeneratedPaper.objects.filter(status='LOCKED', questions__pk__in=ids).exists():
                raise PermissionDenied('Questions in locked papers cannot change.')
            if request.method == 'POST':
                from exam_system.access import invalidate_reviews
                for paper in GeneratedPaper.objects.filter(questions__pk__in=ids).distinct():
                    invalidate_reviews(paper)
    if module == 'edupilot_core.crud_views':
        from edupilot_core.crud_views import get_config_or_404
        model = get_config_or_404(kwargs['model_name'])['model']
        action = {'crud_list_view': 'view', 'crud_create_view': 'add',
                  'crud_update_view': 'change', 'crud_delete_view': 'delete'}.get(name)
        if not action or not request.user.has_perm(f'{model._meta.app_label}.{action}_{model._meta.model_name}'):
            raise PermissionDenied('You do not have permission for this operation.')

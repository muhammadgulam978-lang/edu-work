from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.db.models import Q
from django.db.models import F

from .models import GeneratedPaper, PaperApproval, PaperAccessLog

STAGES = ('TEACHER', 'COORDINATOR', 'ACADEMIC_HEAD', 'CONTROLLER')


def banks_for(user):
    from .models import QuestionBank
    from access_control.models import RecordScope
    from access_control.policy import permitted_assignment
    if not user.is_authenticated or not user.is_active:
        return QuestionBank.objects.none()
    teacher = getattr(user, 'teacher', None)
    if teacher:
        return QuestionBank.objects.filter(
            subject__assignedperiod__teacher=teacher,
            class_fk=F('subject__assignedperiod__class_fk'),
            academic_year=F('subject__assignedperiod__section__academic_year'),
        ).distinct()
    owners = RecordScope.objects.filter(resource='exam_system.questionbank').select_related('campus')
    ids = [owner.object_id for owner in owners if permitted_assignment(user, 'view', owner)]
    return QuestionBank.objects.filter(pk__in=ids)


def visible_papers(user):
    if not user.is_authenticated or not user.is_active:
        return GeneratedPaper.objects.none()
    # Technical administrator status is not a paper-content assignment.
    papers = GeneratedPaper.objects.filter(
        Q(generated_by=user) | Q(approvals__assigned_to=user)
    ).distinct()
    # Controllers only see content after HOD approval.
    allowed = []
    for paper in papers.prefetch_related('approvals'):
        reviews = list(paper.approvals.all())
        stages = {r.stage for r in reviews if r.assigned_to_id == user.pk}
        if paper.generated_by_id == user.pk or stages - {'CONTROLLER'}:
            allowed.append(paper.pk)
        elif 'CONTROLLER' in stages and any(r.stage == 'ACADEMIC_HEAD' and r.status == 'APPROVED' for r in reviews):
            allowed.append(paper.pk)
    return GeneratedPaper.objects.filter(pk__in=allowed)


def require_paper(user, paper, *, edit=False, download=False):
    if not visible_papers(user).filter(pk=paper.pk).exists():
        raise PermissionDenied('You are not assigned to this paper at its current stage.')
    if edit and (paper.generated_by_id != user.pk or paper.status == 'LOCKED'):
        raise PermissionDenied('Only the assigned setter can edit an unlocked paper.')
    if download and (paper.status != 'LOCKED' or not paper.is_unlocked() or not paper.approvals.filter(
            stage='CONTROLLER', assigned_to=user, status='APPROVED').exists()):
        raise PermissionDenied('Paper release is not authorized for this account or time.')


@transaction.atomic
def decide_paper(user, paper_id, stage, action, remarks=''):
    paper = GeneratedPaper.objects.select_for_update().get(pk=paper_id)
    require_paper(user, paper)
    if stage not in STAGES or action not in {'approve', 'reject'}:
        raise ValidationError('Invalid review action or stage.')
    if paper.status == 'LOCKED':
        raise ValidationError('A locked paper cannot be changed.')
    approval = PaperApproval.objects.select_for_update().get(paper=paper, stage=stage)
    teacher_owner = stage == 'TEACHER' and paper.generated_by_id == user.pk
    if not teacher_owner and approval.assigned_to_id != user.pk:
        raise PermissionDenied('You are not the assigned reviewer.')
    if stage != 'TEACHER' and paper.generated_by_id == user.pk:
        raise PermissionDenied('A paper setter cannot approve their own paper.')
    previous = STAGES[:STAGES.index(stage)]
    if paper.approvals.filter(stage__in=previous, status='APPROVED').count() != len(previous):
        raise ValidationError('Previous review stages must be approved first.')
    if approval.status != 'PENDING':
        raise ValidationError('This stage has already been decided.')
    if action == 'reject' and not remarks.strip():
        raise ValidationError('A rejection reason is required.')
    if action == 'approve' and (not paper.questions.exists() or paper.questions.filter(human_approved=False).exists()):
        raise ValidationError('Every question needs human approval before paper approval.')
    approval.status = 'APPROVED' if action == 'approve' else 'REJECTED'
    approval.reviewed_by, approval.remarks = user, remarks
    approval.save(update_fields=['status', 'reviewed_by', 'remarks', 'timestamp'])
    paper.status = 'REJECTED' if action == 'reject' else 'REVIEW'
    if action == 'approve' and stage == 'CONTROLLER':
        paper.status = 'LOCKED'
    paper.save(update_fields=['status'])
    from access_control.models import AuditEvent
    AuditEvent.objects.create(actor=user, action='paper.' + action, resource='exam_system.generatedpaper',
                              object_id=str(paper.pk), outcome=paper.status, reason=remarks,
                              evidence={'stage': stage})
    return paper


def invalidate_reviews(paper):
    if paper.status == 'LOCKED':
        raise ValidationError('Locked paper content cannot change.')
    paper.approvals.update(status='PENDING', reviewed_by=None, remarks='')
    paper.status = 'DRAFT'
    paper.save(update_fields=['status'])

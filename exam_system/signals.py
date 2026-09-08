from django.core.exceptions import ValidationError
from decimal import Decimal, InvalidOperation
from django.db.models.signals import pre_save, pre_delete, m2m_changed
from django.dispatch import receiver

from .models import GeneratedPaper, Question, QuestionScore


@receiver(pre_save, sender=QuestionScore)
def protect_published_marks(sender, instance, **kwargs):
    if instance.answer_sheet.schedule.exam_plan.is_published:
        raise ValidationError('Published marks are locked and require an approved correction.')
    if instance.teacher_score is not None:
        try:
            amount = Decimal(str(instance.teacher_score))
        except (InvalidOperation, ValueError):
            raise ValidationError('The mark must be a valid number.')
        if not amount.is_finite() or amount < 0 or amount > instance.question.marks:
            raise ValidationError('The mark must be between zero and the question maximum.')


@receiver(pre_save, sender=Question)
def protect_reviewed_question(sender, instance, **kwargs):
    if not instance.pk:
        return
    old = Question.objects.get(pk=instance.pk)
    changed = any(getattr(old, f.attname) != getattr(instance, f.attname)
                  for f in Question._meta.concrete_fields if f.name != 'id')
    if not changed:
        return
    papers = GeneratedPaper.objects.filter(questions=instance)
    if papers.filter(status='LOCKED').exists():
        raise ValidationError('This question belongs to a locked paper. Create a new version instead.')
    content_changed = any(getattr(old, f.attname) != getattr(instance, f.attname)
                          for f in Question._meta.concrete_fields
                          if f.name not in {'id', 'human_approved', 'approved_by', 'created_at'})
    if content_changed:
        instance.human_approved, instance.approved_by_id = False, None
    from .access import invalidate_reviews
    for paper in papers:
        invalidate_reviews(paper)


@receiver(pre_delete, sender=Question)
def prevent_locked_question_deletion(sender, instance, **kwargs):
    if GeneratedPaper.objects.filter(questions=instance, status='LOCKED').exists():
        raise ValidationError('Questions belonging to locked papers cannot be deleted.')


@receiver(m2m_changed, sender=GeneratedPaper.questions.through)
def protect_paper_content(sender, instance, action, reverse, pk_set, **kwargs):
    if action not in {'pre_add', 'pre_remove', 'pre_clear'}:
        return
    papers = GeneratedPaper.objects.filter(questions=instance) if reverse else GeneratedPaper.objects.filter(pk=instance.pk)
    if reverse and pk_set:
        papers = GeneratedPaper.objects.filter(pk__in=pk_set)
    if papers.filter(status='LOCKED').exists():
        raise ValidationError('Locked paper content cannot change.')
    from .access import invalidate_reviews
    for paper in papers:
        invalidate_reviews(paper)

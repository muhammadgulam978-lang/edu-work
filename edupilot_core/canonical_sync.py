from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver

from student_profile.models import Student as PortalStudent
from teacher_dashboard.models import Teacher as PortalTeacher

from .models import (
    AutomationJobDetail,
    CanonicalMappingAudit,
    FeeVoucher,
    NotificationQueue,
    SalaryAutomationJobDetail,
    SalaryStructure,
    SalaryVoucher,
    Student,
    StudentBalance,
    StudentFeeAssignment,
    StudentLedger,
    Teacher,
)


def ensure_legacy_student(portal_student):
    legacy = Student.objects.filter(canonical_student=portal_student).first()
    if legacy:
        return legacy

    identifiers = [portal_student.student_id]
    if portal_student.user_id:
        identifiers.append(portal_student.user.username)
    legacy = Student.objects.filter(
        admission_number__in=[value for value in identifiers if value]
    ).first()
    if legacy and not legacy.canonical_student_id:
        legacy.canonical_student = portal_student
        legacy.save(update_fields=['canonical_student'])
        return legacy

    base_identifier = portal_student.student_id or f"PORTAL-{portal_student.pk}"
    identifier = base_identifier
    suffix = 1
    while Student.objects.filter(admission_number=identifier).exists():
        identifier = f"{base_identifier}-{suffix}"
        suffix += 1

    class_name = portal_student.class_fk.class_name if portal_student.class_fk_id else ''
    return Student.objects.create(
        full_name=portal_student.name,
        admission_number=identifier,
        student_id=portal_student.student_id,
        current_class=class_name,
        is_active=True,
        canonical_student=portal_student,
    )


def ensure_legacy_teacher(portal_teacher):
    legacy = Teacher.objects.filter(canonical_teacher=portal_teacher).first()
    if legacy:
        return legacy

    teacher_id = portal_teacher.user.username if portal_teacher.user_id else ''
    if teacher_id:
        legacy = Teacher.objects.filter(teacher_id__iexact=teacher_id).first()
        if legacy and not legacy.canonical_teacher_id:
            legacy.canonical_teacher = portal_teacher
            legacy.save(update_fields=['canonical_teacher'])
            return legacy

    legacy = Teacher.objects.filter(email__iexact=portal_teacher.email).first()
    if legacy and not legacy.canonical_teacher_id:
        legacy.canonical_teacher = portal_teacher
        legacy.save(update_fields=['canonical_teacher'])
        return legacy

    base_identifier = teacher_id or f"PORTAL-{portal_teacher.pk}"
    identifier = base_identifier
    suffix = 1
    while Teacher.objects.filter(teacher_id=identifier).exists():
        identifier = f"{base_identifier}-{suffix}"
        suffix += 1

    return Teacher.objects.create(
        name=portal_teacher.name,
        teacher_id=identifier,
        email=portal_teacher.email,
        phone=portal_teacher.phone or '',
        department=portal_teacher.department or '',
        joining_date=portal_teacher.joining_date,
        is_active=portal_teacher.status == 'active',
        canonical_teacher=portal_teacher,
    )


@receiver(post_save, sender=PortalStudent)
def sync_portal_student(sender, instance, **kwargs):
    legacy = ensure_legacy_student(instance)
    CanonicalMappingAudit.objects.update_or_create(
        entity_type='STUDENT',
        legacy_pk=legacy.pk,
        defaults={
            'canonical_pk': instance.pk,
            'status': 'MATCHED',
            'matched_by': 'portal_sync',
            'details': 'Canonical student synchronized to automation.',
        },
    )


@receiver(post_save, sender=PortalTeacher)
def sync_portal_teacher(sender, instance, **kwargs):
    legacy = ensure_legacy_teacher(instance)
    CanonicalMappingAudit.objects.update_or_create(
        entity_type='TEACHER',
        legacy_pk=legacy.pk,
        defaults={
            'canonical_pk': instance.pk,
            'status': 'MATCHED',
            'matched_by': 'portal_sync',
            'details': 'Canonical teacher synchronized to automation.',
        },
    )


def _populate_student_link(sender, instance, **kwargs):
    if not instance.canonical_student_id and instance.student_id:
        instance.canonical_student = instance.student.canonical_student


def _populate_teacher_link(sender, instance, **kwargs):
    if not instance.canonical_teacher_id and instance.teacher_id:
        instance.canonical_teacher = instance.teacher.canonical_teacher


for model in (
    StudentFeeAssignment,
    StudentLedger,
    StudentBalance,
    FeeVoucher,
    AutomationJobDetail,
):
    pre_save.connect(
        _populate_student_link,
        sender=model,
        dispatch_uid=f'edupilot_core.populate_student_link.{model.__name__}',
    )

for model in (SalaryStructure, SalaryVoucher, SalaryAutomationJobDetail):
    pre_save.connect(
        _populate_teacher_link,
        sender=model,
        dispatch_uid=f'edupilot_core.populate_teacher_link.{model.__name__}',
    )


@receiver(pre_save, sender=NotificationQueue)
def populate_notification_links(sender, instance, **kwargs):
    if instance.student_id and not instance.canonical_student_id:
        instance.canonical_student = instance.student.canonical_student
    if instance.teacher_id and not instance.canonical_teacher_id:
        instance.canonical_teacher = instance.teacher.canonical_teacher

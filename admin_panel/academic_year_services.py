from django.core.exceptions import ValidationError
from django.db import transaction

from .models import AcademicYear


@transaction.atomic
def save_academic_year(form, user):
    # Lock the complete existing set so simultaneous activations cannot both win.
    list(AcademicYear.objects.select_for_update().values_list('pk', flat=True))
    year = form.save(commit=False)
    year.full_clean()
    if year.is_active:
        AcademicYear.objects.exclude(pk=year.pk).filter(is_active=True).update(is_active=False, status='closed')
        year.status = 'active'
    elif year.status == 'active':
        year.status = 'closed'
    year.save()
    from access_control.models import AuditEvent
    AuditEvent.objects.create(actor=user, action='academic_year.save', resource='admin_panel.academicyear',
                              object_id=str(year.pk), outcome=year.status)
    return year


@transaction.atomic
def close_academic_year(year_id, user):
    year = AcademicYear.objects.select_for_update().get(pk=year_id)
    if year.status == 'archived':
        raise ValidationError('Archived years cannot be reopened or changed.')
    year.is_active, year.status = False, 'closed'
    year.save(update_fields=['is_active', 'status'])
    from access_control.models import AuditEvent
    AuditEvent.objects.create(actor=user, action='academic_year.close', resource='admin_panel.academicyear',
                              object_id=str(year.pk), outcome='closed')
    return year

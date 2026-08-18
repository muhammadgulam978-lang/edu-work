from django.db import migrations


def sync_existing_canonical_records(apps, schema_editor):
    LegacyStudent = apps.get_model('edupilot_core', 'Student')
    PortalStudent = apps.get_model('student_profile', 'Student')
    LegacyTeacher = apps.get_model('edupilot_core', 'Teacher')
    PortalTeacher = apps.get_model('teacher_dashboard', 'Teacher')
    Audit = apps.get_model('edupilot_core', 'CanonicalMappingAudit')

    for portal in PortalStudent.objects.select_related('user', 'class_fk').all().iterator():
        if LegacyStudent.objects.filter(canonical_student_id=portal.pk).exists():
            continue

        base_identifier = portal.student_id or f'PORTAL-{portal.pk}'
        identifier = base_identifier
        suffix = 1
        while LegacyStudent.objects.filter(admission_number=identifier).exists():
            identifier = f'{base_identifier}-{suffix}'
            suffix += 1

        class_name = portal.class_fk.class_name if portal.class_fk_id else ''
        legacy = LegacyStudent.objects.create(
            full_name=portal.name,
            admission_number=identifier,
            student_id=portal.student_id,
            current_class=class_name,
            is_active=True,
            canonical_student_id=portal.pk,
        )
        Audit.objects.update_or_create(
            entity_type='STUDENT',
            legacy_pk=legacy.pk,
            defaults={
                'canonical_pk': portal.pk,
                'status': 'MATCHED',
                'matched_by': 'portal_sync',
                'details': 'Automation compatibility record created from canonical student.',
            },
        )

    for portal in PortalTeacher.objects.select_related('user', 'employee').all().iterator():
        if LegacyTeacher.objects.filter(canonical_teacher_id=portal.pk).exists():
            continue

        base_identifier = (
            portal.user.username if portal.user_id else f'PORTAL-{portal.pk}'
        )
        identifier = base_identifier
        suffix = 1
        while LegacyTeacher.objects.filter(teacher_id=identifier).exists():
            identifier = f'{base_identifier}-{suffix}'
            suffix += 1

        legacy = LegacyTeacher.objects.create(
            name=portal.name,
            teacher_id=identifier,
            email=portal.email,
            phone=str(portal.phone or ''),
            department=portal.department or '',
            joining_date=portal.joining_date,
            is_active=portal.status == 'active',
            canonical_teacher_id=portal.pk,
        )
        Audit.objects.update_or_create(
            entity_type='TEACHER',
            legacy_pk=legacy.pk,
            defaults={
                'canonical_pk': portal.pk,
                'status': 'MATCHED',
                'matched_by': 'portal_sync',
                'details': 'Automation compatibility record created from canonical teacher.',
            },
        )


class Migration(migrations.Migration):

    dependencies = [
        ('edupilot_core', '0019_automationjobdetail_canonical_student_and_more'),
    ]

    operations = [
        migrations.RunPython(
            sync_existing_canonical_records,
            migrations.RunPython.noop,
        ),
    ]

import calendar
import re
from datetime import date
from decimal import Decimal

from django.contrib.auth.models import Group, User
from django.contrib.auth.hashers import make_password
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from parent_dashboard.models import Parent, StudentGuardian
from student_profile.models import Student
from edupilot_core.canonical_sync import ensure_legacy_student

from .models import Admission, ClassTeacher, StudentAdmissionWorkflow


REQUIRED_PAYLOAD_FIELDS = (
    'name', 'date_of_birth', 'gender', 'email', 'phone', 'nationality', 'address',
    'campus', 'branch', 'ref_no', 'admission_date', 'academic_year_id',
    'class_id', 'section_id', 'roll_no', 'fee_plan_id', 'voucher_month',
    'voucher_issue_date', 'voucher_due_date',
)

DEFERRED_LABELS = {
    'phone': 'Student phone', 'nationality': 'Nationality', 'address': 'Address',
    'campus': 'Campus', 'branch': 'Branch', 'academic_year_id': 'Academic year',
    'class_id': 'Class', 'section_id': 'Section', 'fee_plan_id': 'Fee plan',
}


def calculate_completeness(workflow):
    payload = workflow.payload or {}
    checks = [bool(payload.get(field)) for field in REQUIRED_PAYLOAD_FIELDS]
    checks.extend([
        workflow.guardians.filter(is_primary=True).exists(),
        bool(workflow.student_username),
        bool(workflow.student_password_hash),
        workflow.documents.filter(document_type__in=['B_FORM', 'BIRTH_CERTIFICATE']).exists(),
        workflow.documents.filter(document_type='GUARDIAN_CNIC').exists(),
    ])
    return round(sum(checks) * 100 / len(checks)) if checks else 0


def _required(payload, field, label, errors):
    if not payload.get(field):
        errors.append(f'{label} is required.')


def validate_workflow(workflow, for_approval=False):
    from edupilot_core.models import FeePlan

    payload = workflow.payload or {}
    errors = []
    labels = {
        'name': 'Student name', 'date_of_birth': 'Date of birth', 'gender': 'Gender',
        'email': 'Student email', 'phone': 'Phone', 'nationality': 'Nationality',
        'address': 'Address', 'campus': 'Campus', 'branch': 'Branch',
        'ref_no': 'Reference number', 'admission_date': 'Admission date',
        'academic_year_id': 'Academic year', 'class_id': 'Class', 'section_id': 'Section',
        'roll_no': 'Roll number', 'fee_plan_id': 'Fee plan',
        'voucher_month': 'First voucher month', 'voucher_issue_date': 'Voucher issue date',
        'voucher_due_date': 'Voucher due date',
    }
    # Admission must remain available when operational details are incomplete.
    # Database-critical identity values are supplied safely during enrollment;
    # guardians, documents, placement and finance can be completed later.

    email = payload.get('email', '').strip()
    student_id = payload.get('student_id', '').strip()
    if email and Student.objects.filter(email__iexact=email).exclude(
        pk=workflow.canonical_student_id
    ).exists():
        errors.append('A student with this email already exists.')
    if student_id and Student.objects.filter(student_id__iexact=student_id).exclude(
        pk=workflow.canonical_student_id
    ).exists():
        errors.append('A student with this Student ID already exists.')
    if workflow.student_username and User.objects.filter(
        username__iexact=workflow.student_username
    ).exclude(pk=getattr(workflow.canonical_student, 'user_id', None)).exists():
        errors.append('Student username is already in use.')

    try:
        academic_year = workflow_academic_year(workflow)
        if academic_year and not academic_year.is_active:
            payload['academic_year_id'] = ''
        section = workflow_section(workflow)
        if section:
            enrolled = Student.objects.filter(section=section).exclude(
                pk=workflow.canonical_student_id
            ).count()
            if enrolled >= section.capacity and not payload.get('capacity_override'):
                payload['capacity_override'] = True
        fee_plan = FeePlan.objects.filter(pk=payload.get('fee_plan_id')).first()
        class_obj = workflow_class(workflow)
        if fee_plan and class_obj and fee_plan.class_name.casefold() != class_obj.class_name.casefold():
            payload['fee_plan_id'] = ''
        if fee_plan and academic_year and fee_plan.session != academic_year.year:
            payload['fee_plan_id'] = ''
    except (TypeError, ValueError):
        # Stale browser selections must not block enrollment. They remain
        # visible in the deferred list and can be corrected after enrollment.
        for field in ('academic_year_id', 'class_id', 'section_id', 'fee_plan_id'):
            payload[field] = ''

    workflow.payload = payload
    workflow.save(update_fields=['payload', 'updated_at'])

    return errors


def _unique_value(model, field, preferred, fallback, exclude_pk=None):
    value = (preferred or '').strip()
    matches = model.objects.filter(**{f'{field}__iexact': value}) if value else model.objects.none()
    if exclude_pk:
        matches = matches.exclude(pk=exclude_pk)
    if value and not matches.exists():
        return value
    candidate = fallback
    suffix = 1
    while model.objects.filter(**{f'{field}__iexact': candidate}).exists():
        suffix += 1
        candidate = f'{fallback}-{suffix}'
    return candidate


def prepare_deferred_enrollment(workflow):
    """Fill only database-critical values and record everything left for later."""
    payload = dict(workflow.payload or {})
    token = re.sub(r'[^A-Za-z0-9]', '', workflow.reference_number)[-10:] or str(workflow.pk)
    payload['name'] = payload.get('name') or f'Student {workflow.reference_number}'
    current_pk = workflow.canonical_student_id
    payload['student_id'] = _unique_value(
        Student, 'student_id', payload.get('student_id'), f'PENDING-{token}', current_pk
    )
    payload['email'] = _unique_value(
        Student, 'email', payload.get('email'), f'pending-{token}@pending.edupilot.local', current_pk
    )
    payload['date_of_birth'] = payload.get('date_of_birth') or payload.get('admission_date') or date.today().isoformat()
    payload['admission_date'] = payload.get('admission_date') or date.today().isoformat()
    payload['gender'] = payload.get('gender') or 'Other'
    payload['roll_no'] = payload.get('roll_no') or f'PENDING-{token}'
    payload['ref_no'] = payload.get('ref_no') or workflow.reference_number

    class_obj = workflow_class(workflow)
    academic_year = workflow_academic_year(workflow)
    from edupilot_core.models import FeePlan
    fee_plan = FeePlan.objects.filter(pk=payload.get('fee_plan_id')).first()
    if fee_plan and (
        (class_obj and fee_plan.class_name.casefold() != class_obj.class_name.casefold())
        or (academic_year and fee_plan.session != academic_year.year)
    ):
        payload['fee_plan_id'] = ''

    deferred = [label for field, label in DEFERRED_LABELS.items() if not payload.get(field)]
    if not workflow.guardians.exists():
        deferred.append('Parent / guardian')
    if not workflow.documents.exists():
        deferred.append('Admission documents')
    if not payload.get('fee_plan_id'):
        deferred.extend(['First fee assignment', 'First voucher'])
    payload['deferred_items'] = list(dict.fromkeys(deferred))
    payload['capacity_override'] = True
    workflow.payload = payload
    username_matches = User.objects.filter(username__iexact=workflow.student_username)
    if workflow.canonical_student_id and workflow.canonical_student.user_id:
        username_matches = username_matches.exclude(pk=workflow.canonical_student.user_id)
    if not workflow.student_username or username_matches.exists():
        base = re.sub(r'[^a-z0-9_.]', '', payload['student_id'].lower()) or f'student{workflow.pk}'
        username = base
        suffix = 1
        while User.objects.filter(username__iexact=username).exists():
            suffix += 1
            username = f'{base}{suffix}'
        workflow.student_username = username
    workflow.save(update_fields=['payload', 'student_username', 'updated_at'])
    return payload


def workflow_academic_year(workflow):
    from .models import AcademicYear
    try:
        return AcademicYear.objects.filter(pk=(workflow.payload or {}).get('academic_year_id')).first()
    except (TypeError, ValueError):
        return None


def workflow_class(workflow):
    from .models import Class
    try:
        return Class.objects.filter(pk=(workflow.payload or {}).get('class_id')).first()
    except (TypeError, ValueError):
        return None


def workflow_section(workflow):
    from .models import Section
    try:
        return Section.objects.filter(pk=(workflow.payload or {}).get('section_id')).first()
    except (TypeError, ValueError):
        return None


def sync_admission_record(workflow, status=None):
    p = workflow.payload
    primary = workflow.guardians.filter(is_primary=True).first()
    defaults = {
        'campus': p.get('campus', ''), 'academic_year': workflow_academic_year(workflow),
        'section': workflow_section(workflow), 'branch': p.get('branch', ''),
        'ref_no': p.get('ref_no', ''), 'name': p.get('name', ''),
        'class_fk': workflow_class(workflow), 'dob': p.get('date_of_birth'),
        'gender': p.get('gender', '').lower(), 'email': p.get('email', ''),
        'contact': p.get('phone', ''), 'address': p.get('address', ''),
        'admission_date': p.get('admission_date'),
        'father_name': primary.full_name if primary else 'Not provided',
        'mother_name': p.get('mother_name') or 'Not provided',
        'father_contact': primary.phone if primary else '',
        'father_cnic': primary.cnic if primary else '',
        'father_email': primary.email if primary else '',
        'father_occupation': primary.occupation if primary else '',
        'nationality': p.get('nationality', ''),
        'admission_status': status or 'pending',
    }
    admission = workflow.admission or Admission()
    for field, value in defaults.items():
        setattr(admission, field, value)
    if p.get('student_id'):
        admission.student_id = p['student_id']
    admission.save()
    if workflow.admission_id != admission.pk:
        workflow.admission = admission
        workflow.save(update_fields=['admission', 'updated_at'])
    return admission


def submit_for_review(workflow, user):
    prepare_deferred_enrollment(workflow)
    errors = validate_workflow(workflow, for_approval=False)
    if errors:
        raise ValidationError(errors)
    sync_admission_record(workflow, 'pending')
    workflow.status = StudentAdmissionWorkflow.STATUS_PENDING
    workflow.submitted_at = timezone.now()
    workflow.updated_by = user
    workflow.completeness = calculate_completeness(workflow)
    workflow.save()
    return workflow


def _create_user(username, password_hash, email, group_name, full_name):
    first, _, last = full_name.strip().partition(' ')
    user = User(username=username, email=email, first_name=first, last_name=last)
    user.password = password_hash
    user.save()
    group, _ = Group.objects.get_or_create(name=group_name)
    user.groups.add(group)
    return user


def _voucher_number(student_id, month, year):
    clean_id = re.sub(r'[^A-Za-z0-9]', '', student_id)
    return f'V-{clean_id}-{month[:3].upper()}-{year}'


def _create_initial_voucher(workflow, student, legacy_student):
    from edupilot_core.models import FeePlanDetail, FeeVoucher, FeeVoucherItem, StudentFeeAssignment

    p = workflow.payload
    assignment, _ = StudentFeeAssignment.objects.update_or_create(
        student=legacy_student,
        defaults={
            'canonical_student': student,
            'fee_plan_id': p['fee_plan_id'],
            'transport_route_id': p.get('transport_route_id') or None,
            'scholarship_id': p.get('scholarship_id') or None,
        },
    )
    details = list(FeePlanDetail.objects.filter(fee_plan=assignment.fee_plan).select_related('fee_head'))
    gross = sum((item.amount for item in details), Decimal('0'))
    if assignment.transport_route_id:
        gross += assignment.transport_route.amount
    discount = Decimal('0')
    if assignment.scholarship_id:
        scholarship = assignment.scholarship
        discount = (
            gross * scholarship.value / Decimal('100')
            if scholarship.discount_type == 'percentage' else scholarship.value
        )
    discount = min(discount, gross)
    issue_date = date.fromisoformat(p['voucher_issue_date'])
    due_date = date.fromisoformat(p['voucher_due_date'])
    month = p['voucher_month']
    voucher, created = FeeVoucher.objects.get_or_create(
        student=legacy_student, month=month, year=issue_date.year,
        defaults={
            'voucher_no': _voucher_number(student.student_id, month, issue_date.year),
            'canonical_student': student, 'issue_date': issue_date, 'due_date': due_date,
            'gross_amount': gross, 'discount': discount, 'previous_due': Decimal('0'),
            'net_amount': gross - discount, 'status': 'UNPAID',
        },
    )
    if created:
        FeeVoucherItem.objects.bulk_create([
            FeeVoucherItem(voucher=voucher, fee_head=item.fee_head, amount=item.amount)
            for item in details
        ])
    return voucher


def _finish_voucher(voucher_id, workflow_id):
    from edupilot_core.models import FeeVoucher
    from edupilot_core.services import PDFGeneratorService
    from edupilot_core.voucher_delivery import distribute_voucher
    try:
        voucher = FeeVoucher.objects.get(pk=voucher_id)
        PDFGeneratorService.generate_voucher_pdf(voucher)
        distribute_voucher(voucher.pk)
        StudentAdmissionWorkflow.objects.filter(pk=workflow_id).update(last_error='')
    except Exception as exc:
        StudentAdmissionWorkflow.objects.filter(pk=workflow_id).update(
            last_error=f'Voucher delivery failed: {exc}'
        )


@transaction.atomic
def approve_and_enroll(workflow, user):
    from edupilot_core.canonical_sync import ensure_legacy_student

    workflow = StudentAdmissionWorkflow.objects.select_for_update().get(pk=workflow.pk)
    if workflow.canonical_student_id:
        return sync_enrolled_student(workflow)
    prepare_deferred_enrollment(workflow)
    errors = validate_workflow(workflow, for_approval=True)
    if errors:
        raise ValidationError(errors)
    p = workflow.payload
    admission = sync_admission_record(workflow, 'approved')
    primary = workflow.guardians.filter(is_primary=True).first()
    student_user = _create_user(
        workflow.student_username, workflow.student_password_hash or make_password(None),
        p['email'], 'Student', p['name']
    )
    student = Student.objects.create(
        user=student_user, student_id=admission.student_id, name=p['name'],
        father_name=primary.full_name if primary else 'Add later', mother_name=p.get('mother_name') or 'Add later',
        academic_year=workflow_academic_year(workflow), class_fk=workflow_class(workflow),
        section=workflow_section(workflow), roll_no=p['roll_no'], phone=p.get('phone') or None,
        gender=p['gender'].title(), date_of_birth=p['date_of_birth'], email=p['email'],
        nationality=p.get('nationality', ''), address=p.get('address', ''),
        blood_group=p.get('blood_group', ''), medical_notes=p.get('medical_notes', ''),
        emergency_contact_name=p.get('emergency_contact_name', ''),
        emergency_contact_phone=p.get('emergency_contact_phone', ''),
        admission_date=p.get('admission_date'), previous_school=p.get('previous_school', ''),
    )
    photo_document = workflow.documents.filter(document_type='STUDENT_PHOTO').first()
    if photo_document:
        student.photo = photo_document.file
        student.save(update_fields=['photo'])
    for guardian in workflow.guardians.all():
        parent = guardian.existing_parent
        if parent is None:
            parent_user = _create_user(
                guardian.username or f'parent.{student.student_id.lower()}.{guardian.pk}',
                guardian.password_hash or make_password(None), guardian.email,
                'Parent', guardian.full_name,
            ) if guardian.portal_access else None
            parent = Parent.objects.create(
                user=parent_user, full_name=guardian.full_name, phone=guardian.phone or None,
                email=guardian.email or None, address=guardian.address or None,
                occupation=guardian.occupation or None,
            )
        parent.students.add(student)
        StudentGuardian.objects.update_or_create(
            parent=parent, student=student,
            defaults={
                'relationship': guardian.relationship, 'is_primary': guardian.is_primary,
                'portal_access': guardian.portal_access,
                'notifications_enabled': guardian.notifications_enabled,
            },
        )
    workflow.documents.update(canonical_student=student)
    legacy_student = ensure_legacy_student(student)
    voucher = None
    if p.get('fee_plan_id') and p.get('voucher_month') and p.get('voucher_issue_date') and p.get('voucher_due_date'):
        voucher = _create_initial_voucher(workflow, student, legacy_student)
    now = timezone.now()
    workflow.canonical_student = student
    workflow.initial_voucher_pk = voucher.pk if voucher else None
    workflow.status = StudentAdmissionWorkflow.STATUS_APPROVED
    workflow.approved_by = user
    workflow.approved_at = now
    workflow.enrolled_at = now
    workflow.completeness = calculate_completeness(workflow)
    workflow.updated_by = user
    workflow.save()
    if voucher:
        transaction.on_commit(lambda: _finish_voucher(voucher.pk, workflow.pk))
    return student


def sync_enrolled_student(workflow):
    """Apply later wizard edits to the already enrolled canonical student."""
    student = workflow.canonical_student
    p = prepare_deferred_enrollment(workflow)
    primary = workflow.guardians.filter(is_primary=True).first()
    values = {
        'name': p['name'], 'student_id': p['student_id'], 'email': p['email'],
        'phone': p.get('phone') or None, 'gender': p['gender'].title(),
        'date_of_birth': p['date_of_birth'], 'nationality': p.get('nationality', ''),
        'address': p.get('address', ''), 'blood_group': p.get('blood_group', ''),
        'medical_notes': p.get('medical_notes', ''),
        'emergency_contact_name': p.get('emergency_contact_name', ''),
        'emergency_contact_phone': p.get('emergency_contact_phone', ''),
        'admission_date': p.get('admission_date'), 'previous_school': p.get('previous_school', ''),
        'academic_year': workflow_academic_year(workflow), 'class_fk': workflow_class(workflow),
        'section': workflow_section(workflow), 'roll_no': p['roll_no'],
        'father_name': primary.full_name if primary else student.father_name or 'Add later',
        'mother_name': p.get('mother_name') or student.mother_name or 'Add later',
    }
    for field, value in values.items():
        setattr(student, field, value)

    photo_document = workflow.documents.filter(document_type='STUDENT_PHOTO').first()
    if photo_document:
        student.photo = photo_document.file
    student.save()
    workflow.documents.update(canonical_student=student)

    legacy_student = ensure_legacy_student(student)
    legacy_student.full_name = student.name
    legacy_student.student_id = student.student_id
    legacy_student.current_class = student.class_fk.class_name if student.class_fk_id else ''
    legacy_student.is_active = True
    legacy_student.save(update_fields=['full_name', 'student_id', 'current_class', 'is_active'])
    if student.user_id:
        student.user.username = workflow.student_username
        student.user.email = p['email']
        if workflow.student_password_hash:
            student.user.password = workflow.student_password_hash
        student.user.save()

    for guardian in workflow.guardians.all():
        parent = guardian.existing_parent
        link = StudentGuardian.objects.filter(student=student, relationship=guardian.relationship).first()
        if parent is None and link:
            parent = link.parent
        if parent is None:
            parent_user = None
            if guardian.portal_access:
                username = guardian.username or f'parent.{student.student_id.lower()}'
                if User.objects.filter(username__iexact=username).exists():
                    username = f'{username}.{guardian.pk}'
                password_hash = guardian.password_hash or make_password(None)
                parent_user = _create_user(
                    username, password_hash, guardian.email, 'Parent', guardian.full_name
                )
            parent = Parent.objects.create(
                user=parent_user, full_name=guardian.full_name or 'Guardian',
                phone=guardian.phone or None, email=guardian.email or None,
                address=guardian.address or None, occupation=guardian.occupation or None,
            )
        parent.students.add(student)
        StudentGuardian.objects.update_or_create(
            parent=parent, student=student,
            defaults={
                'relationship': guardian.relationship or 'Guardian',
                'is_primary': guardian.is_primary, 'portal_access': guardian.portal_access,
                'notifications_enabled': guardian.notifications_enabled,
            },
        )

    if not workflow.initial_voucher_pk and p.get('fee_plan_id') and p.get('voucher_month') \
            and p.get('voucher_issue_date') and p.get('voucher_due_date'):
        voucher = _create_initial_voucher(workflow, student, legacy_student)
        workflow.initial_voucher_pk = voucher.pk
        transaction.on_commit(lambda: _finish_voucher(voucher.pk, workflow.pk))
    sync_admission_record(workflow, 'approved')
    workflow.completeness = calculate_completeness(workflow)
    workflow.updated_at = timezone.now()
    workflow.save(update_fields=['initial_voucher_pk', 'completeness', 'updated_at'])
    return student


def retry_voucher_delivery(workflow):
    if not workflow.initial_voucher_pk:
        raise ValidationError('No voucher is linked to this enrollment.')
    _finish_voucher(workflow.initial_voucher_pk, workflow.pk)

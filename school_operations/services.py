from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from access_control.models import RecordScope, AuditEvent
from access_control.policy import require_action
from access_control.crypto import encrypt_text, decrypt_text
from .models import LibraryBook, LibraryLoan, LabAsset, LabBooking, HealthCase


def ownership(record):
    owner = RecordScope.objects.get(resource=record._meta.label_lower, object_id=record.pk)
    if owner.campus_id != record.campus_id or owner.institution_id != record.campus.institution_id:
        raise PermissionDenied('This record has inconsistent campus ownership.')
    return owner


def prospective_owner(model, campus, dimensions=None):
    return RecordScope(institution=campus.institution, campus=campus,
                       resource=model._meta.label_lower, object_id=0, dimensions=dimensions or {})


def register_owner(record, dimensions=None):
    return RecordScope.objects.create(institution=record.campus.institution, campus=record.campus,
                                      resource=record._meta.label_lower, object_id=record.pk, dimensions=dimensions or {})


def audit(user, assignment, obj, action, evidence=None):
    AuditEvent.objects.create(actor=user, institution=obj.campus.institution, assignment=assignment,
                              action=action, resource=obj._meta.label_lower, object_id=str(obj.pk),
                              outcome='allowed', evidence=evidence or {})


def student_dimensions(student, campus):
    owner = RecordScope.objects.filter(resource='student_profile.student', object_id=student.pk,
                                       institution=campus.institution, campus=campus).first()
    if not owner:
        raise ValidationError('The student must be mapped to this campus before proceeding.')
    return {**owner.dimensions, 'student': [student.pk]}


@transaction.atomic
def create_inventory(user, model, campus, values, **context):
    if model not in {LibraryBook, LabAsset}:
        raise ValidationError('Unsupported inventory type.')
    owner = prospective_owner(model, campus)
    assignment = require_action(user, 'create', owner, **context)
    allowed = {LibraryBook: {'title', 'author', 'isbn', 'copies'},
               LabAsset: {'name', 'laboratory', 'inventory_code', 'quantity', 'safety_notes'}}[model]
    if set(values) - allowed:
        raise ValidationError('Unexpected inventory fields.')
    obj = model(campus=campus, created_by=user, **values)
    obj.full_clean()
    obj.save()
    register_owner(obj)
    audit(user, assignment, obj, 'inventory.create')
    return obj


@transaction.atomic
def issue_book(user, book_id, student, due_on, **context):
    book = LibraryBook.objects.select_for_update().select_related('campus__institution').get(pk=book_id, archived=False)
    require_action(user, 'view', ownership(book), **context)
    dimensions = student_dimensions(student, book.campus)
    assignment = require_action(user, 'create', prospective_owner(LibraryLoan, book.campus, dimensions), **context)
    if due_on < timezone.localdate():
        raise ValidationError('The due date cannot be in the past.')
    if book.loans.filter(returned_at__isnull=True).count() >= book.copies:
        raise ValidationError('No copies are currently available.')
    if book.loans.filter(student=student, returned_at__isnull=True).exists():
        raise ValidationError('This student already has an open loan for this book.')
    loan = LibraryLoan(campus=book.campus, created_by=user, book=book, student=student, due_on=due_on)
    loan.full_clean()
    loan.save()
    register_owner(loan, dimensions)
    audit(user, assignment, loan, 'library.issue')
    return loan


@transaction.atomic
def return_book(user, loan_id, condition, **context):
    loan = LibraryLoan.objects.select_for_update().select_related('campus__institution').get(pk=loan_id)
    assignment = require_action(user, 'edit', ownership(loan), **context)
    if loan.returned_at:
        return loan
    loan.returned_at, loan.return_condition = timezone.now(), condition
    loan.full_clean()
    loan.save(update_fields=['returned_at', 'return_condition'])
    audit(user, assignment, loan, 'library.return')
    return loan


@transaction.atomic
def book_lab(user, asset_id, starts_at, ends_at, purpose, **context):
    asset = LabAsset.objects.select_for_update().select_related('campus__institution').get(pk=asset_id, archived=False)
    require_action(user, 'view', ownership(asset), **context)
    assignment = require_action(user, 'create', prospective_owner(LabBooking, asset.campus), **context)
    obj = LabBooking(campus=asset.campus, created_by=user, asset=asset, starts_at=starts_at,
                      ends_at=ends_at, purpose=purpose)
    obj.full_clean()
    if starts_at < timezone.now():
        raise ValidationError('Bookings must start in the future.')
    obj.save()
    register_owner(obj)
    audit(user, assignment, obj, 'lab.request')
    return obj


@transaction.atomic
def decide_booking(user, booking_id, approve, **context):
    obj = LabBooking.objects.select_for_update().select_related('campus__institution').get(pk=booking_id)
    assignment = require_action(user, 'approve', ownership(obj), **context)
    if obj.created_by_id == user.pk:
        raise PermissionDenied('An independent reviewer must decide this booking.')
    if obj.status != 'pending':
        raise ValidationError('This booking has already been decided.')
    # Serialize competing approvals on the equipment row.
    LabAsset.objects.select_for_update().get(pk=obj.asset_id)
    if approve and LabBooking.objects.filter(asset_id=obj.asset_id, status='approved',
            starts_at__lt=obj.ends_at, ends_at__gt=obj.starts_at).exclude(pk=obj.pk).exists():
        raise ValidationError('This equipment is already booked during that time.')
    obj.status, obj.decided_by = ('approved' if approve else 'rejected'), user
    obj.save(update_fields=['status', 'decided_by'])
    audit(user, assignment, obj, 'lab.' + obj.status)
    return obj


@transaction.atomic
def create_case(user, campus, student, category, notes, consent_reference, follow_up_on=None, **context):
    dimensions = student_dimensions(student, campus)
    assignment = require_action(user, 'create', prospective_owner(HealthCase, campus, dimensions), **context)
    if not context.get('mfa_verified'):
        raise PermissionDenied('Verify your authenticator before opening a confidential case.')
    if not notes.strip() or not consent_reference.strip():
        raise ValidationError('Case notes and a consent or safeguarding authority reference are required.')
    obj = HealthCase(campus=campus, created_by=user, assigned_to=user, student=student, category=category,
                     encrypted_notes=encrypt_text(notes), consent_reference=consent_reference, follow_up_on=follow_up_on)
    obj.full_clean()
    obj.save()
    register_owner(obj, dimensions)
    audit(user, assignment, obj, 'health.create')
    return obj


def read_case(user, case_id, **context):
    obj = HealthCase.objects.select_related('campus__institution').get(pk=case_id)
    assignment = require_action(user, 'view', ownership(obj), **context)
    if not context.get('mfa_verified') or obj.assigned_to_id != user.pk:
        raise PermissionDenied('Only the assigned case worker with verified identity may read these notes.')
    audit(user, assignment, obj, 'health.view')
    return obj, decrypt_text(obj.encrypted_notes)


@transaction.atomic
def cancel_booking(user, booking_id, **context):
    obj = LabBooking.objects.select_for_update().select_related('campus__institution').get(pk=booking_id)
    assignment = require_action(user, 'edit', ownership(obj), **context)
    if obj.created_by_id != user.pk:
        raise PermissionDenied('Only the requester may cancel this booking.')
    if obj.status not in {'pending', 'approved'} or obj.starts_at <= timezone.now():
        raise ValidationError('Only a pending or approved future booking may be cancelled.')
    obj.status = 'cancelled'
    obj.save(update_fields=['status'])
    audit(user, assignment, obj, 'lab.cancel')
    return obj


@transaction.atomic
def close_case(user, case_id, **context):
    obj = HealthCase.objects.select_for_update().select_related('campus__institution').get(pk=case_id)
    assignment = require_action(user, 'edit', ownership(obj), **context)
    if not context.get('mfa_verified') or obj.assigned_to_id != user.pk:
        raise PermissionDenied('Only the assigned case worker with verified identity may close this case.')
    if obj.closed_at:
        return obj
    obj.closed_at = timezone.now()
    obj.save(update_fields=['closed_at'])
    audit(user, assignment, obj, 'health.close')
    return obj

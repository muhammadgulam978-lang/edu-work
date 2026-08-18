from datetime import date
from decimal import Decimal, InvalidOperation

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.hashers import make_password
from django.contrib.auth.models import User
from django.contrib.auth.password_validation import validate_password
from django.utils.crypto import get_random_string
from django.core.exceptions import ValidationError
from django.db.models import Q
from django.db import transaction
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from edupilot_core.models import FeeHead, FeePlan, FeePlanDetail, Scholarship, TransportRoute
from parent_dashboard.models import Parent

from .admission_services import (
    approve_and_enroll,
    calculate_completeness,
    prepare_deferred_enrollment,
    retry_voucher_delivery,
    sync_enrolled_student,
    submit_for_review,
)
from .models import (
    AcademicYear,
    AdmissionDocument,
    AdmissionGuardian,
    Class,
    ClassTeacher,
    Section,
    StudentAdmissionWorkflow,
)


PAYLOAD_FIELDS = (
    'name', 'date_of_birth', 'gender', 'email', 'phone', 'nationality', 'address',
    'mother_name', 'blood_group', 'medical_notes', 'emergency_contact_name',
    'emergency_contact_phone', 'campus', 'branch', 'ref_no', 'admission_date',
    'academic_year_id', 'previous_school', 'admission_notes', 'student_id',
    'class_id', 'section_id', 'roll_no', 'fee_plan_id', 'scholarship_id',
    'transport_route_id', 'voucher_month', 'voucher_issue_date', 'voucher_due_date',
)


def _clean_payload(request, existing=None):
    payload = dict(existing or {})
    for field in PAYLOAD_FIELDS:
        if field in request.POST:
            payload[field] = request.POST.get(field, '').strip()
    payload['transport_enabled'] = request.POST.get('transport_enabled') == 'on'
    if not payload['transport_enabled']:
        payload['transport_route_id'] = ''
    return payload


def _save_guardians(workflow, request):
    rows = zip(
        request.POST.getlist('guardian_id'),
        request.POST.getlist('guardian_existing_parent'),
        request.POST.getlist('guardian_full_name'),
        request.POST.getlist('guardian_relationship'),
        request.POST.getlist('guardian_cnic'),
        request.POST.getlist('guardian_email'),
        request.POST.getlist('guardian_phone'),
        request.POST.getlist('guardian_occupation'),
        request.POST.getlist('guardian_address'),
        request.POST.getlist('guardian_primary'),
        request.POST.getlist('guardian_portal_access'),
        request.POST.getlist('guardian_notifications'),
        request.POST.getlist('guardian_username'),
        request.POST.getlist('guardian_password'),
    )
    retained = []
    primary_saved = False
    for row in rows:
        (guardian_id, parent_id, full_name, relationship, cnic, email, phone, occupation,
         address, is_primary, portal_access, notifications, username, password) = row
        if not full_name.strip() and not parent_id:
            continue
        parent = Parent.objects.filter(pk=parent_id).first() if parent_id else None
        if parent:
            full_name = parent.full_name
            email = parent.email or email
            phone = parent.phone or phone
            occupation = parent.occupation or occupation
            address = parent.address or address
        guardian = (
            workflow.guardians.filter(pk=guardian_id).first()
            if guardian_id else None
        ) or AdmissionGuardian(workflow=workflow)
        guardian.existing_parent = parent
        guardian.full_name = full_name.strip()
        guardian.relationship = relationship.strip() or 'Guardian'
        guardian.cnic = cnic.strip()
        guardian.email = email.strip()
        guardian.phone = phone.strip()
        guardian.occupation = occupation.strip()
        guardian.address = address.strip()
        guardian.is_primary = is_primary == '1' and not primary_saved
        primary_saved = primary_saved or guardian.is_primary
        guardian.portal_access = portal_access == '1'
        guardian.notifications_enabled = notifications == '1'
        guardian.username = '' if parent else username.strip()
        if password and not parent:
            try:
                validate_password(password)
            except ValidationError:
                password = ''
            if password:
                guardian.password_hash = make_password(password)
        guardian.save()
        retained.append(guardian.pk)
    workflow.guardians.exclude(pk__in=retained).delete()
    if retained and not workflow.guardians.filter(is_primary=True).exists():
        workflow.guardians.filter(pk=retained[0]).update(is_primary=True)


def _save_documents(workflow, request):
    required = {'B_FORM', 'GUARDIAN_CNIC'}
    for document_type, _label in AdmissionDocument.DOCUMENT_CHOICES:
        upload = request.FILES.get(f'document_{document_type}')
        if not upload:
            continue
        if upload.size > 10 * 1024 * 1024:
            continue
        allowed = ('.pdf', '.png', '.jpg', '.jpeg')
        if not upload.name.lower().endswith(allowed):
            continue
        if document_type == 'STUDENT_PHOTO' and not upload.name.lower().endswith(('.png', '.jpg', '.jpeg')):
            continue
        AdmissionDocument.objects.update_or_create(
            workflow=workflow, document_type=document_type,
            defaults={
                'file': upload, 'is_required': document_type in required,
                'uploaded_by': request.user,
            },
        )


def _save_workflow(request, workflow):
    workflow.payload = _clean_payload(request, workflow.payload)
    workflow.current_step = min(7, max(1, int(request.POST.get('current_step') or 1)))
    workflow.student_username = request.POST.get('student_username', workflow.student_username).strip()
    password = request.POST.get('student_password', '')
    confirmation = request.POST.get('student_password_confirm', '')
    if password:
        try:
            if password != confirmation:
                raise ValidationError('Student passwords do not match.')
            validate_password(password)
        except ValidationError:
            password = ''
        if password:
            workflow.student_password_hash = make_password(password)
    workflow.updated_by = request.user
    workflow.save()
    if not workflow.payload.get('ref_no'):
        workflow.payload['ref_no'] = f'ADM-{timezone.now():%Y}-{workflow.pk:05d}'
        workflow.save(update_fields=['payload', 'updated_at'])
    _save_guardians(workflow, request)
    _save_documents(workflow, request)
    workflow.completeness = calculate_completeness(workflow)
    workflow.save(update_fields=['completeness', 'updated_at'])
    if workflow.canonical_student_id:
        sync_enrolled_student(workflow)
    return workflow


def _temporary_password(label):
    """Issue a strong, display-once password without storing plaintext."""
    return f"Edu@{label}{get_random_string(8, 'abcdefghjkmnpqrstuvwxyzABCDEFGHJKMNPQRSTUVWXYZ23456789')}!"


def _prepare_enrollment_credentials(workflow, request):
    """Ensure new portal accounts have a known password for the one-time receipt."""
    prepare_deferred_enrollment(workflow)
    student_password = request.POST.get('student_password', '').strip()
    if not student_password:
        student_password = _temporary_password('Student')
    validate_password(student_password)
    workflow.student_password_hash = make_password(student_password)
    workflow.save(update_fields=['student_password_hash', 'updated_at'])

    posted_guardian_passwords = {
        username.strip(): password
        for username, password in zip(
            request.POST.getlist('guardian_username'),
            request.POST.getlist('guardian_password'),
        )
        if username.strip() and password
    }
    guardians = []
    for guardian in workflow.guardians.select_related('existing_parent__user'):
        if guardian.existing_parent_id:
            parent_user = guardian.existing_parent.user
            guardians.append({
                'name': guardian.full_name,
                'relationship': guardian.relationship,
                'username': parent_user.username if parent_user else 'No portal account',
                'password': '',
                'existing': True,
            })
            continue
        if not guardian.portal_access:
            guardians.append({
                'name': guardian.full_name,
                'relationship': guardian.relationship,
                'username': 'Portal access disabled',
                'password': '',
                'existing': False,
            })
            continue
        if not guardian.username or User.objects.filter(username__iexact=guardian.username).exists():
            base = f"parent.{(workflow.payload or {}).get('student_id') or workflow.pk}".lower()
            guardian.username = base
            suffix = 1
            while User.objects.filter(username__iexact=guardian.username).exists():
                suffix += 1
                guardian.username = f'{base}.{suffix}'
        password = posted_guardian_passwords.get(guardian.username) or _temporary_password('Parent')
        validate_password(password)
        guardian.password_hash = make_password(password)
        guardian.save(update_fields=['username', 'password_hash'])
        guardians.append({
            'name': guardian.full_name,
            'relationship': guardian.relationship,
            'username': guardian.username,
            'password': password,
            'existing': False,
        })
    return {
        'student': {
            'username': workflow.student_username,
            'password': student_password,
        },
        'guardians': guardians,
    }


def _applications(request):
    queryset = StudentAdmissionWorkflow.objects.select_related(
        'canonical_student', 'admission'
    ).prefetch_related('guardians')
    query = request.GET.get('q', '').strip()
    status = request.GET.get('status', '').strip()
    year = request.GET.get('academic_year', '').strip()
    class_id = request.GET.get('class_id', '').strip()
    section_id = request.GET.get('section_id', '').strip()
    if query:
        queryset = queryset.filter(
            Q(payload__name__icontains=query) | Q(payload__ref_no__icontains=query)
            | Q(payload__email__icontains=query) | Q(payload__student_id__icontains=query)
            | Q(guardians__full_name__icontains=query) | Q(guardians__email__icontains=query)
        ).distinct()
    if status:
        queryset = queryset.filter(status=status)
    if year:
        queryset = queryset.filter(payload__academic_year_id=year)
    if class_id:
        queryset = queryset.filter(payload__class_id=class_id)
    if section_id:
        queryset = queryset.filter(payload__section_id=section_id)
    return queryset


@login_required
def student_admissions(request):
    tab = request.GET.get('tab', 'applications')
    workflow_id = request.GET.get('workflow') or request.POST.get('workflow_id')
    workflow = None
    if workflow_id:
        workflow = get_object_or_404(
            StudentAdmissionWorkflow.objects.prefetch_related('guardians', 'documents'),
            pk=workflow_id,
        )
    if request.method == 'POST':
        action = request.POST.get('action', 'save_draft')
        if workflow is None:
            workflow = StudentAdmissionWorkflow.objects.create(
                created_by=request.user, updated_by=request.user
            )
        try:
            _save_workflow(request, workflow)
            if action == 'submit_review':
                submit_for_review(workflow, request.user)
                messages.success(request, 'Admission submitted for review.')
                return redirect('student_admissions')
            if action == 'approve_enroll':
                if not request.user.has_perm('admin_panel.change_admission') and not request.user.is_superuser:
                    raise ValidationError('You do not have permission to approve admissions.')
                issued_credentials = _prepare_enrollment_credentials(workflow, request)
                student = approve_and_enroll(workflow, request.user)
                if not student.user or not student.user.check_password(issued_credentials['student']['password']):
                    raise ValidationError('Student portal credentials could not be verified.')
                for guardian in issued_credentials['guardians']:
                    if guardian['password']:
                        account = User.objects.filter(username=guardian['username']).first()
                        if not account or not account.check_password(guardian['password']):
                            raise ValidationError(f"Portal credentials for {guardian['name']} could not be verified.")
                request.session[f'admission_credentials_{workflow.pk}'] = issued_credentials
                messages.success(request, f'{student.name} was enrolled and the first voucher was created.')
                return redirect('admission_enrollment_profile', pk=workflow.pk)
            if action == 'reject':
                if not request.user.has_perm('admin_panel.change_admission') and not request.user.is_superuser:
                    raise ValidationError('You do not have permission to reject admissions.')
                reason = request.POST.get('rejection_reason', '').strip()
                if not reason:
                    raise ValidationError('A rejection reason is required.')
                workflow.status = StudentAdmissionWorkflow.STATUS_REJECTED
                workflow.rejection_reason = reason
                workflow.updated_by = request.user
                workflow.save()
                messages.success(request, 'Admission rejected and retained for audit.')
                return redirect('student_admissions')
            messages.success(
                request,
                'Enrollment details updated.' if workflow.canonical_student_id else 'Admission draft saved.'
            )
            if workflow.canonical_student_id and request.GET.get('edit') == '1':
                return redirect('admission_enrollment_profile', pk=workflow.pk)
            next_step = min(7, workflow.current_step + (1 if action == 'save_continue' else 0))
            return redirect(f"{request.path}?tab=new&workflow={workflow.pk}&step={next_step}")
        except ValidationError as exc:
            for error in exc.messages:
                messages.error(request, error)
            tab = 'new'

    applications = list(_applications(request)[:250])
    application_class_ids = {
        item.payload.get('class_id') for item in applications if item.payload.get('class_id')
    }
    application_section_ids = {
        item.payload.get('section_id') for item in applications if item.payload.get('section_id')
    }
    application_classes = {
        str(pk): name for pk, name in Class.objects.filter(pk__in=application_class_ids)
        .values_list('pk', 'class_name')
    }
    application_sections = {
        str(pk): name for pk, name in Section.objects.filter(pk__in=application_section_ids)
        .values_list('pk', 'section_name')
    }
    for item in applications:
        class_name = application_classes.get(str(item.payload.get('class_id')), 'Class pending')
        section_name = application_sections.get(str(item.payload.get('section_id')), 'Section pending')
        item.placement_display = f'{class_name} / {section_name}'
    counts = {
        key.lower(): StudentAdmissionWorkflow.objects.filter(status=key).count()
        for key in ('DRAFT', 'PENDING', 'APPROVED', 'REJECTED')
    }
    selected_step = int(request.GET.get('step') or (workflow.current_step if workflow else 1))
    context = {
        'tab': tab, 'workflow': workflow, 'applications': applications,
        'counts': counts, 'selected_step': min(7, max(1, selected_step)),
        'academic_years': AcademicYear.objects.order_by('-year'),
        'classes': Class.objects.order_by('class_name'),
        'sections': Section.objects.select_related('class_fk', 'academic_year').order_by('class_fk__class_name', 'section_name'),
        'fee_plans': FeePlan.objects.order_by('class_name', 'name'),
        'fee_heads': FeeHead.objects.filter(status=True).order_by('name'),
        'scholarships': Scholarship.objects.order_by('name'),
        'transport_routes': TransportRoute.objects.order_by('route_name'),
        'parents': Parent.objects.select_related('user').order_by('full_name'),
        'document_choices': AdmissionDocument.DOCUMENT_CHOICES,
        'status_choices': StudentAdmissionWorkflow.STATUS_CHOICES,
        'months': [
            'January', 'February', 'March', 'April', 'May', 'June',
            'July', 'August', 'September', 'October', 'November', 'December',
        ],
        'blood_groups': ['A+', 'A-', 'B+', 'B-', 'AB+', 'AB-', 'O+', 'O-'],
        'today': date.today().isoformat(),
    }
    return render(request, 'admin_panel/student_admissions.html', context)


@login_required
def admission_lookups(request):
    class_id = request.GET.get('class_id')
    year_id = request.GET.get('academic_year_id')
    sections = Section.objects.filter(class_fk_id=class_id, academic_year_id=year_id)
    result = []
    for section in sections:
        enrolled = section.student_set.count()
        assignment = ClassTeacher.objects.filter(
            class_fk_id=class_id, section=section, academic_year_id=year_id
        ).select_related('teacher').first()
        result.append({
            'id': section.pk, 'name': section.section_name, 'capacity': section.capacity,
            'enrolled': enrolled, 'remaining': max(0, section.capacity - enrolled),
            'teacher': assignment.teacher.name if assignment else '',
        })
    class_obj = Class.objects.filter(pk=class_id).first()
    academic_year = AcademicYear.objects.filter(pk=year_id).first()
    fee_plans = []
    if class_obj and academic_year:
        fee_plans = [
            {'id': plan.pk, 'label': f'{plan.name} - {plan.class_name} ({plan.session})'}
            for plan in FeePlan.objects.filter(
                class_name__iexact=class_obj.class_name,
                session__iexact=academic_year.year,
            ).order_by('name')
        ]
    return JsonResponse({'sections': result, 'fee_plans': fee_plans})


@login_required
@require_POST
def admission_create_fee_plan(request):
    if not request.user.is_superuser and not request.user.has_perm('admin_panel.change_admission'):
        return JsonResponse({'success': False, 'error': 'You do not have permission to create fee plans.'}, status=403)

    class_obj = Class.objects.filter(pk=request.POST.get('class_id')).first()
    academic_year = AcademicYear.objects.filter(pk=request.POST.get('academic_year_id')).first()
    name = request.POST.get('name', '').strip()
    if not class_obj or not academic_year or not name:
        return JsonResponse({'success': False, 'error': 'Class, academic year and plan name are required.'}, status=400)

    details = []
    for head in FeeHead.objects.filter(status=True):
        raw_amount = request.POST.get(f'head_{head.pk}', '').strip()
        if not raw_amount:
            continue
        try:
            amount = Decimal(raw_amount)
        except (InvalidOperation, ValueError):
            return JsonResponse({'success': False, 'error': f'Enter a valid amount for {head.name}.'}, status=400)
        if amount > 0:
            details.append((head, amount))
    if not details:
        return JsonResponse({'success': False, 'error': 'Add an amount for at least one fee head.'}, status=400)

    with transaction.atomic():
        plan, created = FeePlan.objects.get_or_create(
            name=name,
            class_name=class_obj.class_name,
            session=academic_year.year,
        )
        if not created and FeePlanDetail.objects.filter(fee_plan=plan).exists():
            return JsonResponse({'success': False, 'error': 'A fee plan with this name already exists.'}, status=400)
        for head, amount in details:
            FeePlanDetail.objects.update_or_create(
                fee_plan=plan, fee_head=head, defaults={'amount': amount}
            )

    return JsonResponse({
        'success': True,
        'plan': {
            'id': plan.pk,
            'label': f'{plan.name} - {plan.class_name} ({plan.session})',
        },
    })


@login_required
def admission_retry_voucher(request, pk):
    if request.method != 'POST':
        return redirect('student_admissions')
    workflow = get_object_or_404(StudentAdmissionWorkflow, pk=pk)
    try:
        retry_voucher_delivery(workflow)
        workflow.refresh_from_db()
        if workflow.last_error:
            messages.error(request, workflow.last_error)
        else:
            messages.success(request, 'Voucher PDF and delivery retried successfully.')
    except ValidationError as exc:
        messages.error(request, exc.message)
    return redirect('student_admissions')


@login_required
def admission_enrollment_profile(request, pk):
    from edupilot_core.models import FeeVoucher
    from parent_dashboard.models import StudentGuardian

    workflow = get_object_or_404(
        StudentAdmissionWorkflow.objects.select_related(
            'canonical_student__user', 'canonical_student__academic_year',
            'canonical_student__class_fk', 'canonical_student__section', 'admission',
            'approved_by',
        ).prefetch_related('guardians', 'documents'),
        pk=pk,
        canonical_student__isnull=False,
    )
    student = workflow.canonical_student
    teacher_assignment = ClassTeacher.objects.filter(
        academic_year=student.academic_year,
        class_fk=student.class_fk,
        section=student.section,
    ).select_related('teacher__user').first()
    voucher = FeeVoucher.objects.filter(pk=workflow.initial_voucher_pk).first()
    guardian_links = list(
        StudentGuardian.objects.filter(student=student)
        .select_related('parent__user')
        .order_by('-is_primary', 'parent__full_name')
    )
    credentials = request.session.pop(f'admission_credentials_{workflow.pk}', None)
    return render(request, 'admin_panel/admission_enrollment_profile.html', {
        'workflow': workflow,
        'student': student,
        'teacher_assignment': teacher_assignment,
        'voucher': voucher,
        'guardian_links': guardian_links,
        'issued_credentials': credentials,
    })

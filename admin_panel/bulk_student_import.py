import secrets
import uuid
from dataclasses import dataclass, field
from datetime import date, datetime

from django.contrib.auth.models import Group, User
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.db import transaction

from edupilot_core.canonical_sync import ensure_legacy_student
from edupilot_core.email_delivery import kick_email_dispatch, queue_account_email
from edupilot_core.models import (
    EmailOutbox,
    FeePlan,
    NotificationQueue,
    Scholarship,
    StudentFeeAssignment,
    TransportRoute,
)
from student_profile.models import Student
from parent_dashboard.models import Parent, StudentGuardian

from .models import AcademicYear, Admission, Class, Section


@dataclass
class BulkStudentImportResult:
    imported: int = 0
    enrolled: int = 0
    fee_ready: int = 0
    skipped: int = 0
    password_reset_required: int = 0
    parents_linked: int = 0
    parent_accounts_created: int = 0
    student_accounts_created: int = 0
    student_logins_ready: int = 0
    parent_logins_ready: int = 0
    credential_emails_queued: int = 0
    messages_queued: int = 0
    parent_data_missing: int = 0
    errors: list[str] = field(default_factory=list)
    student_ids: list[str] = field(default_factory=list)
    parent_ids: list[int] = field(default_factory=list)
    credential_email_ids: list[int] = field(default_factory=list)
    message_ids: list[int] = field(default_factory=list)
    credentials: list[dict] = field(default_factory=list)
    scanned_rows: int = 0
    last_row_number: int = 1
    complete: bool = True


@dataclass
class BulkStudentPreviewResult:
    total_rows: int = 0
    valid_rows: int = 0
    invalid_rows: int = 0
    duplicate_rows: int = 0
    parent_rows: int = 0
    existing_parents: int = 0
    new_parents: int = 0
    fee_ready_rows: int = 0
    parent_data_missing: int = 0
    errors: list[str] = field(default_factory=list)
    rows: list[dict] = field(default_factory=list)
    scanned_rows: int = 0
    last_row_number: int = 1
    complete: bool = True
    seen_student_ids: list[str] = field(default_factory=list)
    seen_usernames: list[str] = field(default_factory=list)
    seen_emails: list[str] = field(default_factory=list)


ALIASES = {
    'student_id': (
        'studentid', 'admissionnumber', 'admissionno',
        'childadmissionnumber', 'childstudentid',
    ),
    'campus': ('campus',), 'branch': ('branch',),
    'name': ('studentname', 'name', 'fullname', 'childname', 'studentfullname'),
    'dob': ('dateofbirth', 'dob'), 'gender': ('gender',),
    'email': ('email', 'studentemail'),
    'contact': ('contactno', 'contactnumber', 'phone', 'studentphone'),
    'address': ('address', 'homeaddress'),
    'admission_date': ('admissiondate', 'registrationdate'),
    'father_name': ('fathersname', 'fathername'),
    'father_email': ('fathersemail', 'fatheremail'),
    'academic_year': ('academicyear', 'session'),
    'class_name': ('classname', 'class'), 'section': ('section', 'sectionname'),
    'father_occ': ('fathersoccupation', 'fatheroccupation', 'fathersoccuppation'),
    'mother_name': ('mothersname', 'mothername'),
    'father_contact': ('fathercontactnumber', 'fathercontact', 'fatherphone'),
    'father_cnic': ('fatherscnicno', 'fathercnic', 'cnic'),
    'nationality': ('nationality',),
    'status': ('admissionstatus', 'status', 'isactive'),
    'login_id': ('loginid', 'username'), 'password': ('password',),
    'fee_plan': ('feeplan', 'feeplanname'),
    'transport_route': ('transportroute', 'route'),
    'scholarship': ('scholarship', 'discount'),
    'roll_no': ('rollno', 'rollnumber'),
    'parent_name': ('parentname', 'guardianname'),
    'parent_email': ('parentemail', 'guardianemail'),
    'parent_phone': ('parentphone', 'guardianphone', 'fatherphone'),
    'parent_occupation': ('parentoccupation', 'guardianoccupation'),
    'parent_address': ('parentaddress', 'guardianaddress', 'homeaddress'),
    'parent_relationship': ('parentrelationship', 'guardianrelationship', 'relationship'),
    'parent_login_id': ('parentloginid', 'guardianloginid', 'parentusername'),
    'parent_password': ('parentpassword', 'guardianpassword'),
}

# Headers that identify a teacher/payroll workbook. Some generic columns such as
# Email, Phone and Status overlap with student imports, so a wrong workbook must
# be rejected before those shared fields make its rows appear valid.
TEACHER_WORKBOOK_HEADERS = {
    'teachername', 'teacherid', 'department', 'subject', 'qualification',
    'experienceyears', 'basicsalary', 'houseallowance', 'medicalallowance',
    'transportallowance', 'utilityallowance', 'specialallowance', 'joiningdate',
}


def _text(value):
    if value is None:
        return ''
    if isinstance(value, float) and value.is_integer():
        value = int(value)
    value = str(value).strip()
    return '' if value.lower() in {'none', 'nan'} else value


def _header(value):
    return ''.join(char for char in _text(value).lower() if char.isalnum())


def _date(value):
    if value is None:
        return None
    if hasattr(value, 'date') and callable(value.date):
        return value.date()
    if isinstance(value, date):
        return value
    value = _text(value)
    for fmt in ('%d-%b-%Y', '%d/%m/%Y', '%Y-%m-%d', '%d-%m-%Y', '%d %b %Y'):
        try:
            return datetime.strptime(value, fmt).date()
        except ValueError:
            continue
    return None


def _is_real_email(value):
    if not value or value.lower().endswith('.local'):
        return False
    try:
        validate_email(value)
        return True
    except ValidationError:
        return False


def _available_username(preferred, existing_usernames):
    base = ''.join(char if char.isalnum() or char in '._-' else '_' for char in preferred.lower())
    base = base.strip('._-') or f'user_{uuid.uuid4().hex[:8]}'
    candidate = base[:140]
    suffix = 1
    while candidate.lower() in existing_usernames:
        suffix += 1
        candidate = f'{base[:130]}_{suffix}'
    existing_usernames.add(candidate.lower())
    return candidate


def _generated_password():
    return f'Edu@{secrets.token_urlsafe(9)}'


def _worksheet_reader(worksheet):
    header_row = next(worksheet.iter_rows(min_row=1, max_row=1, values_only=True), ())
    normalized_headers = {_header(value) for value in header_row if _header(value)}
    teacher_headers = normalized_headers & TEACHER_WORKBOOK_HEADERS
    if len(teacher_headers) >= 2:
        raise ValueError(
            'This is a teacher-format workbook, not a student workbook. '
            'Please upload it from Bulk Upload Teachers.'
        )
    alias_to_field = {
        alias: field_name for field_name, aliases in ALIASES.items() for alias in aliases
    }
    headers = {}
    mapped_fields = {}
    duplicate_headers = []
    for index, value in enumerate(header_row):
        normalized = _header(value)
        if not normalized:
            continue
        field_name = alias_to_field.get(normalized)
        if normalized in headers:
            duplicate_headers.append(_text(value))
            continue
        headers[normalized] = index
        if field_name:
            mapped_fields.setdefault(field_name, index)
    if not headers:
        raise ValueError('Excel first row must contain column headers.')
    if duplicate_headers:
        names = ', '.join(sorted(set(duplicate_headers)))
        raise ValueError(f'Duplicate Excel headers were found: {names}. Keep each header once.')
    if not mapped_fields:
        raise ValueError('No supported student columns were found in the first row.')

    def cell(row, field):
        for alias in ALIASES[field]:
            index = headers.get(alias)
            if index is not None and index < len(row):
                return _text(row[index])
        return ''

    def has_mapped_data(row):
        return any(index < len(row) and _text(row[index]) for index in mapped_fields.values())

    return headers, cell, has_mapped_data


def select_student_worksheet(workbook):
    """Select the worksheet containing the strongest supported student header set."""
    alias_set = {alias for aliases in ALIASES.values() for alias in aliases}
    candidates = []
    teacher_workbook_found = False
    for position, worksheet in enumerate(workbook.worksheets):
        header_row = next(worksheet.iter_rows(min_row=1, max_row=1, values_only=True), ())
        normalized_headers = {_header(value) for value in header_row if _header(value)}
        if len(normalized_headers & TEACHER_WORKBOOK_HEADERS) >= 2:
            teacher_workbook_found = True
            continue
        score = sum(1 for value in header_row if _header(value) in alias_set)
        if score:
            candidates.append((score, -position, worksheet))
    if not candidates:
        if teacher_workbook_found:
            raise ValueError(
                'This is a teacher-format workbook, not a student workbook. '
                'Please upload it from Bulk Upload Teachers.'
            )
        raise ValueError(
            'No worksheet with supported student column headers was found. '
            'If this is a teacher file, use Bulk Upload Teachers.'
        )
    worksheet = max(candidates, key=lambda item: (item[0], item[1]))[2]
    _worksheet_reader(worksheet)
    return worksheet


def preview_students_from_worksheet(
    worksheet, active_year, sample_limit=12, *, start_row=2, max_rows=None, seen=None
):
    """Validate a worksheet without creating users or school records."""
    result = BulkStudentPreviewResult()
    _headers, cell, has_mapped_data = _worksheet_reader(worksheet)
    existing_usernames = {v.lower() for v in User.objects.values_list('username', flat=True)}
    existing_student_ids = {v.lower() for v in Student.objects.values_list('student_id', flat=True) if v}
    existing_emails = {v.lower() for v in Student.objects.values_list('email', flat=True) if v}
    seen = seen or {}
    workbook_usernames = {value.lower() for value in seen.get('usernames', [])}
    workbook_student_ids = {value.lower() for value in seen.get('student_ids', [])}
    workbook_emails = {value.lower() for value in seen.get('emails', [])}
    seen_usernames = existing_usernames | workbook_usernames
    seen_student_ids = existing_student_ids | workbook_student_ids
    seen_emails = existing_emails | workbook_emails
    parent_emails = {
        value.strip().lower()
        for value in Parent.objects.exclude(email__isnull=True).values_list('email', flat=True)
        if value and value.strip()
    }
    parent_phones = {
        value.strip()
        for value in Parent.objects.exclude(phone__isnull=True).values_list('phone', flat=True)
        if value and value.strip()
    }
    class_names = {obj.class_name.lower() for obj in Class.objects.all()}
    year_names = {obj.year.lower() for obj in AcademicYear.objects.all()}
    fee_plans = list(FeePlan.objects.all())
    fee_plan_names = {obj.name.lower() for obj in fee_plans}

    max_row = worksheet.max_row or 1
    if start_row > max_row:
        result.last_row_number = max_row
        result.complete = True
        result.seen_student_ids = sorted(workbook_student_ids)
        result.seen_usernames = sorted(workbook_usernames)
        result.seen_emails = sorted(workbook_emails)
        return result
    end_row = max_row if max_rows is None else min(max_row, start_row + max_rows - 1)
    result.last_row_number = max(1, end_row)
    result.complete = end_row >= max_row
    for row_number, row in enumerate(
        worksheet.iter_rows(min_row=start_row, max_row=end_row, values_only=True), start=start_row
    ):
        result.scanned_rows += 1
        if not has_mapped_data(row):
            continue
        result.total_rows += 1
        errors = []
        duplicate = False
        student_id = cell(row, 'student_id')
        login_id = cell(row, 'login_id')
        email = cell(row, 'email')
        class_name = cell(row, 'class_name')
        requested_year = cell(row, 'academic_year')
        fee_plan_name = cell(row, 'fee_plan')
        parent_email = cell(row, 'parent_email') or cell(row, 'father_email')
        parent_phone = cell(row, 'parent_phone') or cell(row, 'father_contact')
        parent_name = cell(row, 'parent_name') or cell(row, 'father_name')

        if student_id and student_id.lower() in seen_student_ids:
            errors.append(f"Student ID '{student_id}' already exists or is repeated")
            duplicate = True
        if login_id and login_id.lower() in seen_usernames:
            errors.append(f"Login ID '{login_id}' already exists or is repeated")
            duplicate = True
        if email and email.lower() in seen_emails:
            errors.append(f"Student email '{email}' already exists or is repeated")
            duplicate = True
        if requested_year and requested_year.lower() not in year_names:
            errors.append(
                f"Academic year '{requested_year}' is not configured; active year {active_year.year} will be used"
            )
        if class_name and class_name.lower() not in class_names:
            errors.append(f"Class '{class_name}' is not configured; student will be imported without placement")
        if fee_plan_name and fee_plan_name.lower() not in fee_plan_names:
            errors.append(f"Fee plan '{fee_plan_name}' is not configured")

        parent_supplied = any((
            parent_name, parent_email, parent_phone,
            cell(row, 'parent_login_id'), cell(row, 'parent_password'),
        ))
        if parent_supplied:
            result.parent_rows += 1
            if ((parent_email and parent_email.lower() in parent_emails)
                    or (parent_phone and parent_phone in parent_phones)):
                result.existing_parents += 1
            else:
                result.new_parents += 1
        else:
            result.parent_data_missing += 1

        fee_ready = False
        if fee_plan_name and fee_plan_name.lower() in fee_plan_names:
            fee_ready = True
        elif class_name:
            matching = [p for p in fee_plans if p.class_name.lower() == class_name.lower()]
            fee_ready = any(p.session.lower() == (requested_year or active_year.year).lower() for p in matching)
            fee_ready = fee_ready or len(matching) == 1
        elif len(fee_plans) == 1:
            fee_ready = True
        if fee_ready:
            result.fee_ready_rows += 1

        blocking_errors = [
            error for error in errors
            if 'will be used' not in error and 'without placement' not in error
        ]
        if blocking_errors:
            result.invalid_rows += 1
            if duplicate:
                result.duplicate_rows += 1
            if len(result.errors) < 100:
                result.errors.append(f"Row {row_number}: {'; '.join(errors)}")
            status = 'invalid'
        else:
            result.valid_rows += 1
            status = 'warning' if errors else 'valid'

        if not blocking_errors:
            if student_id:
                seen_student_ids.add(student_id.lower())
                workbook_student_ids.add(student_id.lower())
            if login_id:
                seen_usernames.add(login_id.lower())
                workbook_usernames.add(login_id.lower())
            if email:
                seen_emails.add(email.lower())
                workbook_emails.add(email.lower())
        if len(result.rows) < sample_limit:
            result.rows.append({
                'row_number': row_number,
                'student_id': student_id or 'Generated automatically',
                'name': cell(row, 'name') or 'N/A',
                'class_name': class_name or 'Not assigned',
                'parent': parent_name or 'Not supplied',
                'fee_status': 'Ready' if fee_ready else 'Not assigned',
                'status': status,
                'message': '; '.join(errors) if errors else 'Ready to import',
            })
    result.seen_student_ids = sorted(workbook_student_ids)
    result.seen_usernames = sorted(workbook_usernames)
    result.seen_emails = sorted(workbook_emails)
    return result


def import_students_from_worksheet(
    worksheet, active_year, *, start_row=2, max_rows=None, dispatch_emails=True,
    credential_created_by=None,
):
    """Import a streaming worksheet without retaining its rows in memory."""
    result = BulkStudentImportResult()
    _headers, cell, has_mapped_data = _worksheet_reader(worksheet)

    student_group, _ = Group.objects.get_or_create(name='Student')
    existing_usernames = {v.lower() for v in User.objects.values_list('username', flat=True)}
    existing_student_ids = {v.lower() for v in Student.objects.values_list('student_id', flat=True) if v}
    existing_emails = {v.lower() for v in Student.objects.values_list('email', flat=True) if v}
    parent_by_email = {
        parent.email.strip().lower(): parent
        for parent in Parent.objects.select_related('user').exclude(email__isnull=True)
        if parent.email and parent.email.strip()
    }
    parent_by_phone = {
        parent.phone.strip(): parent
        for parent in Parent.objects.select_related('user').exclude(phone__isnull=True)
        if parent.phone and parent.phone.strip()
    }
    class_map = {obj.class_name.lower(): obj for obj in Class.objects.all()}
    year_map = {obj.year.lower(): obj for obj in AcademicYear.objects.all()}
    fee_plans = list(FeePlan.objects.all())
    fee_plan_map = {obj.name.lower(): obj for obj in fee_plans}
    route_map = {obj.route_name.lower(): obj for obj in TransportRoute.objects.all()}
    scholarship_map = {obj.name.lower(): obj for obj in Scholarship.objects.all()}
    section_map = {
        (obj.class_fk_id, obj.academic_year_id, obj.section_name.lower()): obj
        for obj in Section.objects.select_related('class_fk', 'academic_year')
    }
    classes_with_sections = {
        (class_id, year_id) for class_id, year_id, _name in section_map
    }
    today = date.today()

    max_row = worksheet.max_row or 1
    end_row = max_row if max_rows is None else min(max_row, start_row + max_rows - 1)
    result.last_row_number = max(1, end_row)
    result.complete = end_row >= max_row

    for row_number, row in enumerate(
        worksheet.iter_rows(min_row=start_row, max_row=end_row, values_only=True), start=start_row
    ):
        result.scanned_rows += 1
        if not has_mapped_data(row):
            continue
        try:
            student_id = cell(row, 'student_id') or f"STU-{uuid.uuid4().hex[:12].upper()}"
            name = cell(row, 'name') or 'N/A'
            login_id = cell(row, 'login_id') or f"student_{student_id.lower().replace('-', '_')}"
            email = cell(row, 'email') or f'{login_id}@students.edupilot.local'
            from .bulk_credentials import generate_unique_student_password
            password = generate_unique_student_password()

            if student_id.lower() in existing_student_ids:
                raise ValueError(f"Student ID '{student_id}' already exists")
            if login_id.lower() in existing_usernames:
                raise ValueError(f"Login ID '{login_id}' already exists")
            if email.lower() in existing_emails:
                raise ValueError(f"Student email '{email}' already exists")
            requested_year = cell(row, 'academic_year').lower()
            academic_year = year_map.get(requested_year) or active_year
            class_obj = class_map.get(cell(row, 'class_name').lower()) if cell(row, 'class_name') else None
            section_obj = None
            if class_obj and cell(row, 'section'):
                section_obj = section_map.get(
                    (class_obj.pk, academic_year.pk, cell(row, 'section').lower())
                )
            admission_class = class_obj
            if class_obj and not section_obj and (class_obj.pk, academic_year.pk) not in classes_with_sections:
                # Class is optional. Do not reject an otherwise valid row when its
                # academic section setup has not been created yet.
                admission_class = None

            raw_gender = cell(row, 'gender').lower()
            gender = {'female': 'Female', 'other': 'Other'}.get(raw_gender, 'Male')
            raw_status = cell(row, 'status').lower() or 'approved'
            status = {
                'active': 'approved', 'approved': 'approved',
                'inactive': 'rejected', 'rejected': 'rejected',
                'pending': 'pending', 'yes': 'approved', 'true': 'approved', '1': 'approved',
                'no': 'rejected', 'false': 'rejected', '0': 'rejected',
            }.get(raw_status, 'approved')

            fee_plan = fee_plan_map.get(cell(row, 'fee_plan').lower()) if cell(row, 'fee_plan') else None
            if cell(row, 'fee_plan') and not fee_plan:
                raise ValueError(f"Fee plan '{cell(row, 'fee_plan')}' is not configured")
            if not fee_plan and class_obj:
                matching = [p for p in fee_plans if p.class_name.lower() == class_obj.class_name.lower()]
                fee_plan = next((p for p in matching if p.session.lower() == academic_year.year.lower()), None)
                if not fee_plan and len(matching) == 1:
                    fee_plan = matching[0]
            if not fee_plan and len(fee_plans) == 1:
                fee_plan = fee_plans[0]

            with transaction.atomic():
                admission = Admission.objects.create(
                    student_id=student_id,
                    campus=cell(row, 'campus') or 'N/A',
                    branch=cell(row, 'branch') or 'N/A',
                    ref_no=f'BULK-{student_id}',
                    name=name,
                    dob=_date(cell(row, 'dob')) or today,
                    gender=gender.lower() if gender != 'Other' else None,
                    email=email,
                    contact=cell(row, 'contact') or 'N/A',
                    address=cell(row, 'address') or 'N/A',
                    admission_date=_date(cell(row, 'admission_date')) or today,
                    father_name=cell(row, 'father_name') or 'N/A',
                    father_email=cell(row, 'father_email') or None,
                    mother_name=cell(row, 'mother_name') or 'N/A',
                    father_contact=cell(row, 'father_contact') or 'N/A',
                    father_cnic=cell(row, 'father_cnic') or 'N/A',
                    father_occupation=cell(row, 'father_occ') or 'N/A',
                    academic_year=academic_year,
                    class_fk=admission_class,
                    section=section_obj,
                    admission_status=status,
                    nationality=cell(row, 'nationality') or 'N/A',
                )

                if status == 'approved':
                    user = User(username=login_id, email=email, first_name=name[:150])
                    user.set_password(password)
                    user.save()
                    user.groups.add(student_group)
                    result.student_accounts_created += 1
                    if user.has_usable_password():
                        result.student_logins_ready += 1
                    result.credentials.append({
                        'role': 'Student',
                        'name': name,
                        'login_id': user.username,
                        'password': password,
                        'email': email,
                        'student_id': student_id,
                    })
                    portal_student = Student.objects.create(
                        user=user,
                        academic_year=academic_year,
                        student_id=student_id,
                        name=name,
                        father_name=cell(row, 'father_name') or 'N/A',
                        mother_name=cell(row, 'mother_name') or 'N/A',
                        class_fk=admission.class_fk,
                        section=section_obj or admission.section,
                        roll_no=cell(row, 'roll_no') or student_id,
                        phone=cell(row, 'contact') or None,
                        gender=gender,
                        date_of_birth=_date(cell(row, 'dob')) or today,
                        email=email,
                        nationality=cell(row, 'nationality') or 'N/A',
                        address=cell(row, 'address') or 'N/A',
                        admission_date=_date(cell(row, 'admission_date')) or today,
                    )
                    from .bulk_credentials import store_bulk_student_credential
                    store_bulk_student_credential(
                        portal_student, password, created_by=credential_created_by
                    )
                    result.student_ids.append(portal_student.student_id)
                    legacy_student = ensure_legacy_student(portal_student)
                    if queue_account_email(
                        user=user, password=password, role='student', display_name=name
                    ):
                        result.credential_emails_queued += 1
                        outbox = EmailOutbox.objects.filter(
                            dedupe_key=f'account-welcome:{user.pk}'
                        ).only('pk').first()
                        if outbox:
                            result.credential_email_ids.append(outbox.pk)

                    student_phone = cell(row, 'contact')
                    if student_phone and student_phone.upper() != 'N/A':
                        notification = NotificationQueue.objects.create(
                            student=legacy_student,
                            canonical_student=portal_student,
                            notification_type='SMS',
                            content=(
                                f'Your EduPilot Student Portal account is ready. '
                                f'Login ID: {user.username}'
                            ),
                            status='PENDING',
                        )
                        result.messages_queued += 1
                        result.message_ids.append(notification.pk)

                    parent_name = cell(row, 'parent_name') or cell(row, 'father_name')
                    parent_email = cell(row, 'parent_email') or cell(row, 'father_email')
                    parent_phone = cell(row, 'parent_phone') or cell(row, 'father_contact')
                    parent_supplied = any((
                        parent_name, parent_email, parent_phone,
                        cell(row, 'parent_login_id'), cell(row, 'parent_password'),
                    ))
                    if parent_supplied:
                        parent = (
                            parent_by_email.get(parent_email.lower()) if parent_email else None
                        ) or (parent_by_phone.get(parent_phone) if parent_phone else None)
                        if parent is None:
                            parent = Parent.objects.create(
                                full_name=parent_name or 'N/A',
                                email=parent_email or None,
                                phone=parent_phone or None,
                                occupation=cell(row, 'parent_occupation') or cell(row, 'father_occ') or None,
                                address=cell(row, 'parent_address') or cell(row, 'address') or None,
                            )
                            if parent_email:
                                parent_by_email[parent_email.lower()] = parent
                            if parent_phone:
                                parent_by_phone[parent_phone] = parent

                        parent_password = cell(row, 'parent_password')
                        if not parent.user_id:
                            preferred_parent_login = (
                                cell(row, 'parent_login_id')
                                or f"parent_{student_id.lower().replace('-', '_')}"
                            )
                            parent_login = _available_username(preferred_parent_login, existing_usernames)
                            if parent_password:
                                validate_password(parent_password)
                            else:
                                parent_password = _generated_password()
                            parent_user = User(
                                username=parent_login,
                                email=parent_email or '',
                                first_name=(parent.full_name or 'Parent')[:150],
                            )
                            parent_user.set_password(parent_password)
                            parent_user.save()
                            parent_group, _ = Group.objects.get_or_create(name='Parent')
                            parent_user.groups.add(parent_group)
                            parent.user = parent_user
                            parent.save(update_fields=['user'])
                            result.parent_accounts_created += 1
                            if parent_user.has_usable_password():
                                result.parent_logins_ready += 1
                            result.credentials.append({
                                'role': 'Parent',
                                'name': parent.full_name or 'Parent',
                                'login_id': parent_user.username,
                                'password': parent_password,
                                'email': parent_email or '',
                                'student_id': student_id,
                            })
                            if queue_account_email(
                                user=parent_user,
                                password=parent_password,
                                role='parent',
                                display_name=parent.full_name,
                            ):
                                result.credential_emails_queued += 1
                                outbox = EmailOutbox.objects.filter(
                                    dedupe_key=f'account-welcome:{parent_user.pk}'
                                ).only('pk').first()
                                if outbox:
                                    result.credential_email_ids.append(outbox.pk)
                            if parent_phone and parent_phone.upper() != 'N/A':
                                notification = NotificationQueue.objects.create(
                                    student=legacy_student,
                                    canonical_student=portal_student,
                                    notification_type='SMS',
                                    content=(
                                        f'Your EduPilot Parent Portal account is ready. '
                                        f'Login ID: {parent_user.username}'
                                    ),
                                    status='PENDING',
                                )
                                result.messages_queued += 1
                                result.message_ids.append(notification.pk)

                        parent.students.add(portal_student)
                        StudentGuardian.objects.update_or_create(
                            parent=parent,
                            student=portal_student,
                            defaults={
                                'relationship': cell(row, 'parent_relationship') or 'Father',
                                'is_primary': not portal_student.guardian_links.filter(is_primary=True).exists(),
                                'portal_access': True,
                                'notifications_enabled': True,
                            },
                        )
                        result.parents_linked += 1
                        if parent.pk not in result.parent_ids:
                            result.parent_ids.append(parent.pk)
                    else:
                        result.parent_data_missing += 1
                    result.enrolled += 1
                    if fee_plan:
                        StudentFeeAssignment.objects.update_or_create(
                            student=legacy_student,
                            defaults={
                                'canonical_student': portal_student,
                                'fee_plan': fee_plan,
                                'transport_route': route_map.get(cell(row, 'transport_route').lower()),
                                'scholarship': scholarship_map.get(cell(row, 'scholarship').lower()),
                            },
                        )
                        result.fee_ready += 1

            existing_student_ids.add(student_id.lower())
            existing_usernames.add(login_id.lower())
            existing_emails.add(email.lower())
            result.imported += 1
        except Exception as exc:
            result.skipped += 1
            if len(result.errors) < 50:
                result.errors.append(f'Row {row_number}: {exc}')

    if dispatch_emails and result.credential_emails_queued:
        kick_email_dispatch()
    return result

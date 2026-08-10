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
    FeePlan,
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
    credential_emails_queued: int = 0
    errors: list[str] = field(default_factory=list)


ALIASES = {
    'student_id': ('studentid', 'admissionnumber', 'admissionno'),
    'campus': ('campus',), 'branch': ('branch',),
    'name': ('studentname', 'name', 'fullname'),
    'dob': ('dateofbirth', 'dob'), 'gender': ('gender',),
    'email': ('email', 'studentemail'),
    'contact': ('contactno', 'contactnumber', 'phone', 'studentphone'),
    'address': ('address',), 'admission_date': ('admissiondate',),
    'father_name': ('fathersname', 'fathername'),
    'father_email': ('fathersemail', 'fatheremail'),
    'academic_year': ('academicyear', 'session'),
    'class_name': ('classname', 'class'), 'section': ('section', 'sectionname'),
    'father_occ': ('fathersoccupation', 'fatheroccupation', 'fathersoccuppation'),
    'mother_name': ('mothersname', 'mothername'),
    'father_contact': ('fathercontactnumber', 'fathercontact'),
    'father_cnic': ('fatherscnicno', 'fathercnic', 'cnic'),
    'nationality': ('nationality',), 'status': ('admissionstatus', 'status'),
    'login_id': ('loginid', 'username'), 'password': ('password',),
    'fee_plan': ('feeplan', 'feeplanname'),
    'transport_route': ('transportroute', 'route'),
    'scholarship': ('scholarship', 'discount'),
    'roll_no': ('rollno', 'rollnumber'),
    'parent_name': ('parentname', 'guardianname'),
    'parent_email': ('parentemail', 'guardianemail'),
    'parent_phone': ('parentphone', 'guardianphone'),
    'parent_occupation': ('parentoccupation', 'guardianoccupation'),
    'parent_address': ('parentaddress', 'guardianaddress'),
    'parent_relationship': ('parentrelationship', 'guardianrelationship', 'relationship'),
    'parent_login_id': ('parentloginid', 'guardianloginid', 'parentusername'),
    'parent_password': ('parentpassword', 'guardianpassword'),
}


def _text(value):
    if value is None:
        return ''
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


def import_students_from_worksheet(worksheet, active_year):
    """Import a streaming worksheet without retaining its rows in memory."""
    result = BulkStudentImportResult()
    header_row = next(worksheet.iter_rows(min_row=1, max_row=1, values_only=True), ())
    headers = {_header(value): index for index, value in enumerate(header_row) if _text(value)}
    if not headers:
        raise ValueError('Excel first row must contain column headers.')

    def cell(row, field):
        for alias in ALIASES[field]:
            index = headers.get(alias)
            if index is not None and index < len(row):
                return _text(row[index])
        return ''

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

    for row_number, row in enumerate(worksheet.iter_rows(min_row=2, values_only=True), start=2):
        if not any(value not in (None, '') for value in row):
            continue
        try:
            student_id = cell(row, 'student_id') or f"STU-{uuid.uuid4().hex[:12].upper()}"
            name = cell(row, 'name') or 'N/A'
            login_id = cell(row, 'login_id') or f"student_{student_id.lower().replace('-', '_')}"
            email = cell(row, 'email') or f'{login_id}@students.edupilot.local'
            password = cell(row, 'password')

            if student_id.lower() in existing_student_ids:
                raise ValueError(f"Student ID '{student_id}' already exists")
            if login_id.lower() in existing_usernames:
                raise ValueError(f"Login ID '{login_id}' already exists")
            if email.lower() in existing_emails:
                raise ValueError(f"Student email '{email}' already exists")
            if password:
                validate_password(password)
            elif _is_real_email(email):
                password = _generated_password()

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
                'pending': 'pending',
            }.get(raw_status, 'approved')

            fee_plan = fee_plan_map.get(cell(row, 'fee_plan').lower()) if cell(row, 'fee_plan') else None
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
                    if password:
                        user.set_password(password)
                    else:
                        user.set_unusable_password()
                        result.password_reset_required += 1
                    user.save()
                    user.groups.add(student_group)
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
                    legacy_student = ensure_legacy_student(portal_student)
                    if queue_account_email(
                        user=user, password=password, role='student', display_name=name
                    ):
                        result.credential_emails_queued += 1

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
                            elif _is_real_email(parent_email):
                                parent_password = _generated_password()
                            parent_user = User(
                                username=parent_login,
                                email=parent_email or '',
                                first_name=(parent.full_name or 'Parent')[:150],
                            )
                            if parent_password:
                                parent_user.set_password(parent_password)
                            else:
                                parent_user.set_unusable_password()
                                result.password_reset_required += 1
                            parent_user.save()
                            parent_group, _ = Group.objects.get_or_create(name='Parent')
                            parent_user.groups.add(parent_group)
                            parent.user = parent_user
                            parent.save(update_fields=['user'])
                            result.parent_accounts_created += 1
                            if queue_account_email(
                                user=parent_user,
                                password=parent_password,
                                role='parent',
                                display_name=parent.full_name,
                            ):
                                result.credential_emails_queued += 1

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

    if result.credential_emails_queued:
        kick_email_dispatch()
    return result

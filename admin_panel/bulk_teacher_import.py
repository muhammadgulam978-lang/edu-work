from dataclasses import dataclass, field
from datetime import date, datetime

from django.contrib.auth.models import Group, User
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.db import transaction

from teacher_dashboard.models import Teacher

from .models import Subject


@dataclass
class BulkTeacherImportResult:
    imported: int = 0
    skipped: int = 0
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


ALIASES = {
    'teacher_id': ('id', 'teacherid', 'teacher_id'),
    'name': ('name', 'fullname', 'teachername'),
    'email': ('email', 'teacheremail'),
    'phone': ('phonenumber', 'phone', 'contactnumber'),
    'gender': ('gender',),
    'date_of_birth': ('dateofbirth', 'date_of_birth', 'dob'),
    'qualification': ('qualification',),
    'experience': ('experience', 'experienceyears'),
    'address': ('address',),
    'faculty_group': ('facultygroup', 'faculty_group'),
    'department': ('department',),
    'subjects': ('subject', 'subjects'),
    'image': ('image', 'photo'),
    'joining_date': ('joiningdate', 'joining_date'),
    'status': ('status',),
    'login_id': ('loginid', 'login_id', 'username'),
    'password': ('password',),
}


def _text(value):
    if value is None:
        return ''
    if isinstance(value, float) and value.is_integer():
        value = int(value)
    value = str(value).strip()
    return '' if value.lower() in {'none', 'nan'} else value


def _header(value):
    return ''.join(char for char in _text(value).lower() if char.isalnum() or char == '_')


def _date(value):
    if value is None:
        return None
    if hasattr(value, 'date') and callable(value.date):
        return value.date()
    if isinstance(value, date):
        return value
    for fmt in ('%d-%b-%Y', '%d/%m/%Y', '%Y-%m-%d', '%d-%m-%Y', '%d %b %Y'):
        try:
            return datetime.strptime(_text(value), fmt).date()
        except ValueError:
            continue
    return None


def _experience(value):
    text = _text(value).lower().replace('years', '').replace('year', '').strip()
    if not text:
        return 0
    parsed = int(float(text))
    if parsed < 0:
        raise ValueError('Experience cannot be negative')
    return parsed


def _required_valid_date(value, label):
    text = _text(value)
    parsed = _date(value)
    if text and parsed is None:
        raise ValueError(f"{label} '{text}' is not a supported date")
    return parsed


def _reader(worksheet):
    raw_headers = next(worksheet.iter_rows(min_row=1, max_row=1, values_only=True), ())
    alias_map = {_header(alias): field for field, aliases in ALIASES.items() for alias in aliases}
    indexes = {}
    normalized_seen = set()
    duplicates = []
    for index, raw in enumerate(raw_headers):
        normalized = _header(raw)
        if not normalized:
            continue
        if normalized in normalized_seen:
            duplicates.append(_text(raw))
            continue
        normalized_seen.add(normalized)
        field = alias_map.get(normalized)
        if field:
            indexes[field] = index
    if duplicates:
        raise ValueError(f"Duplicate Excel headers found: {', '.join(sorted(set(duplicates)))}")
    missing = [field for field in ('name', 'email', 'login_id', 'password') if field not in indexes]
    if missing:
        raise ValueError(f"Required teacher columns are missing: {', '.join(missing)}")

    def cell(row, field):
        index = indexes.get(field)
        return _text(row[index]) if index is not None and index < len(row) else ''

    def populated(row):
        return any(index < len(row) and _text(row[index]) for index in indexes.values())

    return indexes, cell, populated


def select_teacher_worksheet(workbook):
    supported = {_header(alias) for aliases in ALIASES.values() for alias in aliases}
    candidates = []
    for position, worksheet in enumerate(workbook.worksheets):
        row = next(worksheet.iter_rows(min_row=1, max_row=1, values_only=True), ())
        score = sum(1 for value in row if _header(value) in supported)
        if score:
            candidates.append((score, -position, worksheet))
    if not candidates:
        raise ValueError('No worksheet with supported teacher headers was found.')
    worksheet = max(candidates, key=lambda item: (item[0], item[1]))[2]
    _reader(worksheet)
    return worksheet


def import_teachers_from_worksheet(worksheet):
    result = BulkTeacherImportResult()
    _indexes, cell, populated = _reader(worksheet)
    teacher_group, _ = Group.objects.get_or_create(name='Teacher')
    qualifications = {choice for choice, _label in Teacher.QUALIFICATION_CHOICES}
    faculties = {choice for choice, _label in Teacher.FACULTY_CHOICES}
    subject_map = {subject.name.lower(): subject for subject in Subject.objects.all()}
    existing_usernames = {value.lower() for value in User.objects.values_list('username', flat=True)}
    existing_user_emails = {
        value.lower() for value in User.objects.exclude(email='').values_list('email', flat=True)
    }
    existing_teacher_emails = {
        value.lower() for value in Teacher.objects.values_list('email', flat=True)
    }

    for row_number, row in enumerate(worksheet.iter_rows(min_row=2, values_only=True), start=2):
        if not populated(row):
            continue
        try:
            name = cell(row, 'name')
            email = cell(row, 'email')
            login_id = cell(row, 'login_id')
            password = cell(row, 'password')
            if not all((name, email, login_id, password)):
                raise ValueError('Name, Email, Login_Id and Password are required')
            try:
                validate_email(email)
            except ValidationError:
                raise ValueError(f"Email '{email}' is invalid")
            if email.lower() in existing_user_emails or email.lower() in existing_teacher_emails:
                raise ValueError(f"Email '{email}' already exists")
            if login_id.lower() in existing_usernames:
                raise ValueError(f"Login ID '{login_id}' already exists")
            validate_password(password)

            gender = cell(row, 'gender').title() or 'Male'
            if gender not in {'Male', 'Female'}:
                raise ValueError("Gender must be 'Male' or 'Female'")
            raw_qualification = cell(row, 'qualification') or 'Matric'
            qualification_aliases = {
                'phd': 'PhD',
                'masters': 'Masters', 'master': 'Masters', 'ms': 'Masters',
                'msc': 'Masters', 'ma': 'Masters', 'mba': 'Masters',
                'bachelor': 'Bachelor', 'bachelors': 'Bachelor', 'bs': 'Bachelor',
                'bsc': 'Bachelor', 'ba': 'Bachelor', 'be': 'Bachelor',
                'diploma': 'Diploma', 'matric': 'Matric',
                'intermediate': 'Intermediate', 'fa': 'Intermediate', 'fsc': 'Intermediate',
            }
            qualification = qualification_aliases.get(raw_qualification.lower(), raw_qualification)
            if qualification not in qualifications:
                raise ValueError(f"Qualification '{raw_qualification}' is not configured")
            faculty_values = [
                item.strip() for item in cell(row, 'faculty_group').replace(';', ',').split(',')
                if item.strip()
            ]
            unknown_faculties = [item for item in faculty_values if item not in faculties]
            if unknown_faculties:
                raise ValueError(f"Faculty group is not configured: {', '.join(unknown_faculties)}")
            subject_names = [
                item.strip() for item in cell(row, 'subjects').replace(';', ',').split(',')
                if item.strip()
            ]
            subjects = [subject_map.get(item.lower()) for item in subject_names]
            missing_subjects = [name for name, subject in zip(subject_names, subjects) if subject is None]
            if missing_subjects:
                raise ValueError(f"Subject is not configured: {', '.join(missing_subjects)}")
            raw_status = cell(row, 'status').lower() or 'active'
            status = {'active': 'active', 'inactive': 'inactive', 'on leave': 'inactive'}.get(raw_status)
            if status is None:
                raise ValueError("Status must be Active, Inactive or On Leave")

            with transaction.atomic():
                user = User.objects.create_user(
                    username=login_id,
                    email=email,
                    password=password,
                    first_name=name[:150],
                    is_active=status == 'active',
                )
                user.groups.add(teacher_group)
                teacher = Teacher.objects.create(
                    user=user,
                    name=name,
                    email=email,
                    phone=cell(row, 'phone') or None,
                    gender=gender,
                    date_of_birth=_required_valid_date(cell(row, 'date_of_birth'), 'Date of birth'),
                    qualification=qualification,
                    experience=_experience(cell(row, 'experience')),
                    Address=cell(row, 'address') or None,
                    faculty_group=faculty_values,
                    department=cell(row, 'department') or None,
                    joining_date=_required_valid_date(cell(row, 'joining_date'), 'Joining date'),
                    status=status,
                )
                teacher.subjects.add(*[subject for subject in subjects if subject])

            existing_usernames.add(login_id.lower())
            existing_user_emails.add(email.lower())
            existing_teacher_emails.add(email.lower())
            result.imported += 1
            if cell(row, 'teacher_id'):
                result.warnings.append(
                    f"Row {row_number}: external teacher ID '{cell(row, 'teacher_id')}' was read but the current Teacher model has no ID field for it."
                )
            if cell(row, 'image'):
                result.warnings.append(
                    f"Row {row_number}: image '{cell(row, 'image')}' was not imported because Excel contains no file attachment."
                )
        except Exception as exc:
            result.skipped += 1
            result.errors.append(f'Row {row_number}: {exc}')
    return result

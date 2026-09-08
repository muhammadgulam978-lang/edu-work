from dataclasses import dataclass, field
from datetime import date, datetime

from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.db import transaction

from .models import Department, Designation, Employee, JobType, StaffCategory


@dataclass
class BulkEmployeeImportResult:
    imported: int = 0
    skipped: int = 0
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


ALIASES = {
    'name': ('name', 'fullname', 'employeename'),
    'email': ('email', 'employeeemail'),
    'phone': ('phonenumber', 'phone', 'contactnumber'),
    'staff_category': ('staffcategory', 'category'),
    'job_type': ('jobtype',),
    'department': ('department',),
    'designation': ('designation',),
    'employee_type': ('employeetype',),
    'joining_date': ('joiningdate', 'joining_date'),
    'is_teacher': ('isteacher', 'teacher'),
    'is_active': ('isactive', 'active', 'status'),
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


def _bool(value, default=True):
    text = _text(value).lower()
    if not text:
        return default
    return text in {'yes', 'true', '1', 'active', 'y'}


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
    missing = [f for f in ('name', 'email', 'joining_date') if f not in indexes]
    if missing:
        raise ValueError(f"Required employee columns are missing: {', '.join(missing)}")

    def cell(row, f):
        index = indexes.get(f)
        return _text(row[index]) if index is not None and index < len(row) else ''

    def populated(row):
        return any(index < len(row) and _text(row[index]) for index in indexes.values())

    return indexes, cell, populated


def select_employee_worksheet(workbook):
    supported = {_header(alias) for aliases in ALIASES.values() for alias in aliases}
    candidates = []
    for position, worksheet in enumerate(workbook.worksheets):
        row = next(worksheet.iter_rows(min_row=1, max_row=1, values_only=True), ())
        score = sum(1 for value in row if _header(value) in supported)
        if score:
            candidates.append((score, -position, worksheet))
    if not candidates:
        raise ValueError('No worksheet with supported employee headers was found.')
    worksheet = max(candidates, key=lambda item: (item[0], item[1]))[2]
    _reader(worksheet)
    return worksheet


def import_employees_from_worksheet(worksheet):
    result = BulkEmployeeImportResult()
    _indexes, cell, populated = _reader(worksheet)

    staff_categories = {c.name.lower(): c for c in StaffCategory.objects.all()}
    job_types = {j.name.lower(): j for j in JobType.objects.all()}
    departments = {d.name.lower(): d for d in Department.objects.all()}
    designations = {(d.department_id, d.title.lower()): d for d in Designation.objects.select_related('department')}
    employee_type_choices = {choice for choice, _label in Employee.EMPLOYEE_TYPE_CHOICES}
    existing_emails = {v.lower() for v in Employee.objects.values_list('email', flat=True)}

    for row_number, row in enumerate(worksheet.iter_rows(min_row=2, values_only=True), start=2):
        if not populated(row):
            continue
        try:
            name = cell(row, 'name')
            email = cell(row, 'email')
            if not name or not email:
                raise ValueError('Name and Email are required')
            try:
                validate_email(email)
            except ValidationError:
                raise ValueError(f"Email '{email}' is invalid")
            if email.lower() in existing_emails:
                raise ValueError(f"Email '{email}' already exists")

            joining_date = _date(cell(row, 'joining_date'))
            if joining_date is None:
                raise ValueError(f"Joining date '{cell(row, 'joining_date')}' is not a supported date")

            department = None
            raw_department = cell(row, 'department')
            if raw_department:
                department = departments.get(raw_department.lower())
                if department is None:
                    raise ValueError(f"Department '{raw_department}' is not configured")

            designation = None
            raw_designation = cell(row, 'designation')
            if raw_designation:
                key = (department.id if department else None, raw_designation.lower())
                designation = designations.get(key)
                if designation is None:
                    raise ValueError(
                        f"Designation '{raw_designation}' is not configured for department '{raw_department or '—'}'"
                    )

            staff_category = None
            raw_category = cell(row, 'staff_category')
            if raw_category:
                staff_category = staff_categories.get(raw_category.lower())
                if staff_category is None:
                    raise ValueError(f"Staff category '{raw_category}' is not configured")

            job_type = None
            raw_job_type = cell(row, 'job_type')
            if raw_job_type:
                job_type = job_types.get(raw_job_type.lower())
                if job_type is None:
                    raise ValueError(f"Job type '{raw_job_type}' is not configured")

            raw_employee_type = cell(row, 'employee_type').lower().replace(' ', '_') or 'full_time'
            if raw_employee_type not in employee_type_choices:
                raise ValueError(f"Employee type must be one of: {', '.join(sorted(employee_type_choices))}")

            with transaction.atomic():
                Employee.objects.create(
                    name=name,
                    email=email,
                    phone=cell(row, 'phone') or '',
                    staff_category=staff_category,
                    job_type=job_type,
                    department=department,
                    designation=designation,
                    joining_date=joining_date,
                    employee_type=raw_employee_type,
                    is_teacher=_bool(cell(row, 'is_teacher'), default=False),
                    is_active=_bool(cell(row, 'is_active'), default=True),
                )

            existing_emails.add(email.lower())
            result.imported += 1
        except Exception as exc:
            result.skipped += 1
            result.errors.append(f'Row {row_number}: {exc}')
    return result

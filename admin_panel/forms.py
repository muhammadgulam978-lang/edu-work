from django import forms
from django.contrib.auth.password_validation import validate_password
from django.contrib.auth.models import User, Group, Permission
from .models import (
    Admission, AcademicYear, Class, Section, Subject, Stream,
    AssignedPeriod, CreatePeriod, Book
)
from teacher_dashboard.models import Teacher
from phonenumber_field.formfields import PhoneNumberField as FormPhoneField
from django.apps import apps

# =============================================================
# 🌟 Role-Based Access Control (Using Django Auth Groups)
# =============================================================
from django import forms
from django.contrib.auth.models import Permission, Group

class RoleForm(forms.ModelForm):
    class Meta:
        model = Group
        fields = ['name', 'permissions']

    permissions = forms.ModelMultipleChoiceField(
        queryset=Permission.objects.all().select_related('content_type'),
        widget=forms.CheckboxSelectMultiple,
        required=False,
        label="Select Permissions (Admin Panel Only)"
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Group by content_type__model (model name)
        grouped_permissions = {}
        for perm in self.fields['permissions'].queryset:
            model_name = perm.content_type.model.replace('_', ' ').title()
            grouped_permissions.setdefault(model_name, []).append(perm)
        self.grouped_permissions = grouped_permissions



class AssignRoleForm(forms.Form):
    username = forms.CharField(max_length=150, label="Login ID")
    full_name = forms.CharField(max_length=150, label="Full Name", required=False)
    email = forms.EmailField()
    password = forms.CharField(widget=forms.PasswordInput)
    confirm_password = forms.CharField(widget=forms.PasswordInput)
    role = forms.ModelChoiceField(queryset=Group.objects.all(), label="Assign Role")
    is_active = forms.BooleanField(label="Active Login", required=False, initial=True)
    is_staff = forms.BooleanField(label="Staff Access", required=False)

    def clean_username(self):
        username = self.cleaned_data["username"].strip()
        if User.objects.filter(username__iexact=username).exists():
            raise forms.ValidationError("This login ID already exists.")
        return username

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get("password")
        confirm_password = cleaned_data.get("confirm_password")
        if password and confirm_password and password != confirm_password:
            raise forms.ValidationError("Password and confirm password do not match.")
        if password:
            validate_password(password)
        return cleaned_data

    def clean_is_staff(self):
        role = self.cleaned_data.get("role")
        is_staff = self.cleaned_data.get("is_staff")
        if role and role.name.lower() == "admin":
            return True
        return bool(is_staff)



# =============================================================
# 📋 Admission Form
# =============================================================
class AdmissionForm(forms.ModelForm):
    academic_year = forms.ModelChoiceField(
        queryset=AcademicYear.objects.none(),
        empty_label="Select Academic Year",
        required=True
    )

    class Meta:
        model = Admission
        fields = [
           'campus', 'academic_year', 'branch', 'ref_no', 'name', 'class_fk',
            'dob', 'gender', 'email', 'contact', 'address', 'admission_date',
            'father_name', 'mother_name', 'father_contact','father_email', 'father_occupation','father_cnic',
            'nationality', 'admission_status'
        ]


# =============================================================
# 🏫 Class Form
# =============================================================
class ClassForm(forms.ModelForm):
    class Meta:
        model = Class
        fields = ['class_name', 'group']

    def clean_class_name(self):
        name = self.cleaned_data['class_name']
        qs = Class.objects.filter(class_name__iexact=name)
        if self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise forms.ValidationError("This class name already exists.")
        return name


# =============================================================
# 📆 Academic Year Form
# =============================================================
class AcademicYearForm(forms.ModelForm):
    class Meta:
        model = AcademicYear
        fields = ['year', 'is_active']


# =============================================================
# 🧩 Section Form
# =============================================================
class SectionForm(forms.ModelForm):
    class Meta:
        model = Section
        fields = ['academic_year', 'class_fk', 'section_name', 'capacity']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['academic_year'].queryset = AcademicYear.objects.filter(is_active=True)


# =============================================================
# 📚 Subject Form
# =============================================================
class SubjectForm(forms.ModelForm):
    class Meta:
        model = Subject
        fields = '__all__'

    def __init__(self, *args, **kwargs):
        super(SubjectForm, self).__init__(*args, **kwargs)
        self.fields['academic_year'].queryset = AcademicYear.objects.filter(is_active=True)
        self.fields['stream'].queryset = Stream.objects.all().order_by("stream_name")


# =============================================================
# 👨‍🏫 Teacher Form
# =============================================================
class TeacherForm(forms.ModelForm):
    login_id = forms.CharField(max_length=150, required=False, label="Login ID")
    password = forms.CharField(widget=forms.PasswordInput, required=False)
    confirm_password = forms.CharField(widget=forms.PasswordInput, required=False)
    gender = forms.ChoiceField(
        choices=[('Male', 'Male'), ('Female', 'Female')],
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    phone = FormPhoneField(region="PK")
    date_of_birth = forms.DateField(
        widget=forms.DateInput(attrs={'type': 'date'}),
        input_formats=['%Y-%m-%d', '%d/%m/%Y']
    )
    is_merge = forms.BooleanField(
        required=False,
        label="Merge Class",
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )

    subjects = forms.ModelMultipleChoiceField(
        queryset=Subject.objects.all(),
        widget=forms.SelectMultiple(attrs={'class': 'form-control select2'})
    )

    class Meta:
        model = Teacher
        fields = '__all__'
        widgets = {
            'faculty_group': forms.SelectMultiple(attrs={
                'class': 'form-control select2',
                'multiple': 'multiple'
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['subjects'].label_from_instance = (
            lambda obj: f"{obj.name} ({obj.stream.stream_name}) [{obj.short_code}]"
            if obj.stream else f"{obj.name} [{obj.short_code}]"
        )
        if not self.instance.pk:
            self.fields["login_id"].required = True
            self.fields["password"].required = True
            self.fields["confirm_password"].required = True

    def clean_login_id(self):
        login_id = (self.cleaned_data.get("login_id") or "").strip()
        if login_id and User.objects.filter(username__iexact=login_id).exists():
            raise forms.ValidationError("This login ID already exists.")
        return login_id

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get("password")
        confirm_password = cleaned_data.get("confirm_password")
        if self.instance.pk:
            return cleaned_data
        if password != confirm_password:
            raise forms.ValidationError("Password and confirm password do not match.")
        if password:
            validate_password(password)
        return cleaned_data


# =============================================================
# 🕒 Create Period Form
# =============================================================
class CreatePeriodForm(forms.ModelForm):
    class Meta:
        model = CreatePeriod
        fields = ['day', 'period_name', 'start_time', 'end_time']
        widgets = {
            'start_time': forms.TimeInput(format='%I:%M %p', attrs={'type': 'time'}),
            'end_time': forms.TimeInput(format='%I:%M %p', attrs={'type': 'time'}),
        }


# =============================================================
# 🗓️ Assigned Period Form
# =============================================================
class AssignedPeriodForm(forms.ModelForm):
    is_bypass = forms.BooleanField(
        required=False,
        label="Bypass Validation",
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )

    class Meta:
        model = AssignedPeriod
        fields = ['class_fk', 'section', 'day', 'period', 'subject', 'teacher']
        widgets = {
            'subject': forms.Select(attrs={'id': 'id_subject'}),
            'day': forms.Select(attrs={'id': 'id_day'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        Teacher = apps.get_model('teacher_dashboard', 'Teacher')
        self.fields['teacher'].queryset = Teacher.objects.all()

    def clean(self):
        cleaned_data = super().clean()
        class_fk = cleaned_data.get('class_fk')
        section = cleaned_data.get('section')
        day = cleaned_data.get('day')
        period = cleaned_data.get('period')
        teacher = cleaned_data.get('teacher')
        subject = cleaned_data.get('subject')
        is_bypass = cleaned_data.get('is_bypass')

        if teacher and day and period and class_fk and not is_bypass:
            exists = AssignedPeriod.objects.filter(
                teacher=teacher,
                day=day,
                period=period,
            ).exclude(class_fk=class_fk).exists()

            if exists:
                raise forms.ValidationError(
                    f"Teacher {teacher} is already assigned on {day} during {period} to another class."
                )

            multiple_section_exists = AssignedPeriod.objects.filter(
                teacher=teacher,
                class_fk=class_fk,
                day=day,
                period=period,
            ).exclude(section=section).exists()

            if multiple_section_exists:
                raise forms.ValidationError(
                    f"Teacher {teacher} is already assigned to another section of {class_fk} on {day} during {period}."
                )

            duplicate_exists = AssignedPeriod.objects.filter(
                class_fk=class_fk,
                section=section,
                subject=subject,
                teacher=teacher,
                day=day,
                period=period
            ).exists()

            if duplicate_exists:
                raise forms.ValidationError(
                    "This assignment already exists with the same class, section, subject, teacher, day, and period."
                )

        return cleaned_data


# =============================================================
# 📘 Book Upload Form
# =============================================================
class BookUploadForm(forms.ModelForm):
    class Meta:
        model = Book
        fields = ['title', 'class_for', 'subject', 'pdf_file']


# ================= PERMISSION FORM ====================
from django import forms
from django.contrib.auth.models import Permission

class PermissionForm(forms.Form):
    """
    Displays all Django permissions grouped by app_label.
    Can be used to assign to roles (Groups).
    """
    permissions = forms.ModelMultipleChoiceField(
        queryset=Permission.objects.all(),
        widget=forms.CheckboxSelectMultiple,
        required=False,
        label="Select Permissions"
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        grouped_permissions = {}
        for perm in Permission.objects.select_related('content_type').all():
            prefix = perm.content_type.app_label
            if prefix not in grouped_permissions:
                grouped_permissions[prefix] = []
            grouped_permissions[prefix].append(perm)

        self.grouped_permissions = grouped_permissions



        
from django import forms
from .models import StaffCategory, JobType, Employee

# IMPORTANT: Teacher model is in teacher_dashboard app (as used in your views.py)
from teacher_dashboard.models import Teacher
from admin_panel.models import Subject  # agar Subject yahin hai; warna apni correct app path set kar lena

# -------------------- Staff Category Form --------------------
class StaffCategoryForm(forms.ModelForm):
    class Meta:
        model = StaffCategory
        fields = ['name', 'description']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Category Name'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'placeholder': 'Description', 'rows': 3}),
        }
        
        

# admin_panel/forms.py

from django import forms
from .models import Employee, Subject
from teacher_dashboard.models import Teacher
from phonenumber_field.formfields import PhoneNumberField as FormPhoneField

# admin_panel/forms.py
# admin_panel/forms.py

from django import forms
from .models import Employee, Subject
from teacher_dashboard.models import Teacher
from phonenumber_field.formfields import PhoneNumberField as FormPhoneField

class EmployeeForm(forms.ModelForm):
    # ✅ checkbox
    is_teacher = forms.BooleanField(
        required=False,
        label="Is Teacher?",
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input', 'id': 'id_is_teacher'})
    )

    # ---------- Teacher extra fields ----------
    teacher_gender = forms.ChoiceField(
        required=False,
        choices=[('Male', 'Male'), ('Female', 'Female')],
        widget=forms.Select(attrs={'class': 'form-control'})
    )

    teacher_phone = FormPhoneField(region="PK", required=False)

    teacher_date_of_birth = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
        input_formats=['%Y-%m-%d', '%d/%m/%Y']
    )

    teacher_qualification = forms.ChoiceField(
        required=False,
        choices=Teacher.QUALIFICATION_CHOICES,
        widget=forms.Select(attrs={'class': 'form-control'})
    )

    teacher_experience = forms.IntegerField(
        required=False,
        min_value=0,
        widget=forms.NumberInput(attrs={'class': 'form-control'})
    )

    teacher_address = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )

    teacher_department = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )

    # ✅ EXACT MULTI-SELECT like teacher_form
    teacher_faculty_group = forms.MultipleChoiceField(
        required=False,
        choices=Teacher.FACULTY_CHOICES,
        widget=forms.SelectMultiple(attrs={
            'class': 'form-control select2',
            'multiple': 'multiple'
        })
    )

    # ✅ EXACT MULTI-SELECT like teacher_form
    teacher_subjects = forms.ModelMultipleChoiceField(
        queryset=Subject.objects.all(),
        required=False,
        widget=forms.SelectMultiple(attrs={'class': 'form-control select2'})
    )

    teacher_image = forms.ImageField(required=False)

    class Meta:
        model = Employee
        fields = [
            'name', 'email', 'phone',
            'staff_category', 'job_type',
            'department', 'designation',
            'joining_date', 'is_active',
        ]
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'phone': forms.TextInput(attrs={'class': 'form-control'}),
            'staff_category': forms.Select(attrs={'class': 'form-control'}),
            'job_type': forms.Select(attrs={'class': 'form-control'}),
            'department': forms.Select(attrs={'class': 'form-control'}),
            'designation': forms.Select(attrs={'class': 'form-control'}),
            'joining_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # ✅ subjects label same as teacher form
        self.fields['teacher_subjects'].label_from_instance = (
            lambda obj: f"{obj.name} ({obj.stream.stream_name}) [{obj.short_code}]"
            if getattr(obj, "stream", None) else f"{obj.name} [{obj.short_code}]"
        )

     
# admin_panel/forms.py
from django import forms
from .models import JobType, LeaveType


class JobTypeForm(forms.ModelForm):
    allowed_leave_types = forms.ModelMultipleChoiceField(
        queryset=LeaveType.objects.filter(is_active=True),
        required=False,
        widget=forms.CheckboxSelectMultiple
    )

    class Meta:
        model = JobType
        fields = [
            'name',
            'probation_months',
            'is_leave_eligible',
            'allowed_leave_types',
            'has_benefits',
        ]

        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Job Type Name'
            }),
            'probation_months': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': 'Probation Months'
            }),
            'is_leave_eligible': forms.CheckboxInput(attrs={
                'class': 'form-check-input',
                'id': 'id_is_leave_eligible'
            }),
            'has_benefits': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # ✅ UI default unchecked
        self.fields['is_leave_eligible'].initial = False
        self.fields['has_benefits'].initial = False


        
from django import forms
from .models import LeaveType

class LeaveTypeForm(forms.ModelForm):
    class Meta:
        model = LeaveType
        fields = ['name', 'yearly_quota', 'is_paid', 'is_active']

        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Leave Name'
            }),
            'yearly_quota': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': 'Yearly Quota'
            }),
            'is_paid': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
            'is_active': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
        }


# -------------------- Teacher Form (Only teacher-extra fields) --------------------
class TeacherFromEmployeeForm(forms.ModelForm):
    """
    Ye form Employee wale page ke liye hai.
    Isme teacher ki extra fields hongi — name/email/phone/user yahan se nahi lenge
    (wo employee se auto-fill hongi).
    """

    gender = forms.ChoiceField(
        choices=[('Male', 'Male'), ('Female', 'Female')],
        widget=forms.Select(attrs={'class': 'form-control'})
    )

    date_of_birth = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
        input_formats=['%Y-%m-%d', '%d/%m/%Y']
    )

    is_merge = forms.BooleanField(
        required=False,
        label="Merge Class",
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )

    subjects = forms.ModelMultipleChoiceField(
        required=False,
        queryset=Subject.objects.all(),
        widget=forms.SelectMultiple(attrs={'class': 'form-control select2'})
    )

    class Meta:
        model = Teacher
        # name/email/phone/user exclude => employee se ayega
        exclude = ('user', 'name', 'email', 'phone')
        widgets = {
            # faculty_group MUST be select2 multi (exact same feel)
            'faculty_group': forms.SelectMultiple(attrs={
                'class': 'form-control select2',
                'multiple': 'multiple'
            }),
            'qualification': forms.Select(attrs={'class': 'form-control'}),
            'experience': forms.NumberInput(attrs={'class': 'form-control'}),
            'Address': forms.TextInput(attrs={'class': 'form-control'}),
            'department': forms.TextInput(attrs={'class': 'form-control'}),
            'joining_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'status': forms.Select(attrs={'class': 'form-control'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # subjects label formatting (same as your TeacherForm)
        self.fields['subjects'].label_from_instance = (
            lambda obj: f"{obj.name} ({obj.stream.stream_name}) [{obj.short_code}]"
            if getattr(obj, "stream", None) else f"{obj.name} [{obj.short_code}]"
        )
        

from django import forms
from django.forms import inlineformset_factory

from .models import TeacherAppraisalSubmission, TeacherActivity


class TeacherSubmissionForm(forms.ModelForm):
    achievements = forms.CharField(required=False, widget=forms.Textarea(attrs={"class":"form-control","rows":3}))
    challenges = forms.CharField(required=False, widget=forms.Textarea(attrs={"class":"form-control","rows":3}))
    improvement_plan = forms.CharField(required=False, widget=forms.Textarea(attrs={"class":"form-control","rows":3}))

    class Meta:
        model = TeacherAppraisalSubmission
        fields = ["achievements", "challenges", "improvement_plan"]


TeacherActivityFormSet = inlineformset_factory(
    TeacherAppraisalSubmission,
    TeacherActivity,
    fields=["activity_type", "title", "date", "hours", "notes"],
    extra=1,
    can_delete=True,
    widgets={
        "activity_type": forms.Select(attrs={"class":"form-control"}),
        "title": forms.TextInput(attrs={"class":"form-control"}),
        "date": forms.DateInput(attrs={"type":"date","class":"form-control"}),
        "hours": forms.NumberInput(attrs={"class":"form-control"}),
        "notes": forms.Textarea(attrs={"class":"form-control","rows":2}),
    }
)










from django import forms
from .models import Student

class StudentRegistrationForm(forms.ModelForm):
    class Meta:
        model = Student
        fields = '__all__'
        widgets = {
            'date_of_birth': forms.DateInput(attrs={'type': 'date'}),
            'admission_date': forms.DateInput(attrs={'type': 'date'}),
        }


from .models import (
    ProcurementCategory, Vendor, PurchaseRequest, InventoryItem, StockMovement,
    Vehicle, RouteVehicleAssignment, TransportTrip, VehicleMaintenance, TransportRoute
)


class OperationFormMixin:
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name, field in self.fields.items():
            widget = field.widget
            if isinstance(widget, forms.CheckboxInput):
                widget.attrs.setdefault("class", "form-check-input")
            elif isinstance(widget, forms.Select):
                widget.attrs.setdefault("class", "form-control")
            elif isinstance(widget, forms.Textarea):
                widget.attrs.setdefault("class", "form-control")
                widget.attrs.setdefault("rows", 3)
            else:
                widget.attrs.setdefault("class", "form-control")


class ProcurementCategoryForm(OperationFormMixin, forms.ModelForm):
    class Meta:
        model = ProcurementCategory
        fields = ["name", "description", "is_active"]


class VendorForm(OperationFormMixin, forms.ModelForm):
    class Meta:
        model = Vendor
        fields = ["name", "contact_person", "phone", "email", "address", "status"]


class PurchaseRequestForm(OperationFormMixin, forms.ModelForm):
    class Meta:
        model = PurchaseRequest
        fields = [
            "title", "category", "vendor", "needed_by", "priority",
            "estimated_cost", "status", "description"
        ]
        widgets = {
            "needed_by": forms.DateInput(attrs={"type": "date"}),
        }


class InventoryItemForm(OperationFormMixin, forms.ModelForm):
    class Meta:
        model = InventoryItem
        fields = [
            "name", "sku", "category", "vendor", "quantity",
            "reorder_level", "unit", "unit_cost", "status"
        ]


class StockMovementForm(OperationFormMixin, forms.ModelForm):
    class Meta:
        model = StockMovement
        fields = ["item", "movement_type", "quantity", "note"]


class TransportRouteOperationForm(OperationFormMixin, forms.ModelForm):
    class Meta:
        model = TransportRoute
        fields = ["route_name", "amount"]


class VehicleForm(OperationFormMixin, forms.ModelForm):
    class Meta:
        model = Vehicle
        fields = [
            "vehicle_no", "vehicle_type", "capacity", "driver_name",
            "driver_phone", "registration_expiry", "status", "notes"
        ]
        widgets = {
            "registration_expiry": forms.DateInput(attrs={"type": "date"}),
        }


class RouteVehicleAssignmentForm(OperationFormMixin, forms.ModelForm):
    class Meta:
        model = RouteVehicleAssignment
        fields = ["route", "vehicle", "driver_name", "start_date", "end_date", "is_active"]
        widgets = {
            "start_date": forms.DateInput(attrs={"type": "date"}),
            "end_date": forms.DateInput(attrs={"type": "date"}),
        }


class TransportTripForm(OperationFormMixin, forms.ModelForm):
    class Meta:
        model = TransportTrip
        fields = [
            "route", "vehicle", "service_date", "scheduled_departure",
            "actual_departure", "students_transported", "status", "notes",
        ]
        widgets = {
            "service_date": forms.DateInput(attrs={"type": "date"}),
            "scheduled_departure": forms.TimeInput(attrs={"type": "time"}),
            "actual_departure": forms.TimeInput(attrs={"type": "time"}),
        }


class VehicleMaintenanceForm(OperationFormMixin, forms.ModelForm):
    class Meta:
        model = VehicleMaintenance
        fields = ["vehicle", "maintenance_type", "service_date", "cost", "status", "notes"]
        widgets = {
            "service_date": forms.DateInput(attrs={"type": "date"}),
        }

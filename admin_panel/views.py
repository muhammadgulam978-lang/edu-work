from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login
from django.contrib.auth.forms import AuthenticationForm
from django.contrib import messages
from django.contrib.auth.models import User, Group, Permission
from django.db import transaction
from django.contrib.auth.decorators import permission_required
from django.core.mail import send_mail
from django.conf import settings
from .models import Admission, AcademicYear, Class, Section
from .utils import role_required
from django.http import HttpResponseForbidden
from django.utils.crypto import get_random_string
from django.contrib.auth.hashers import make_password
from django.contrib.auth.decorators import login_required
from django.contrib.auth import authenticate, login

# =================================================================
# ===================== IMPORTS =====================
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from django.contrib.auth.models import User, Group, Permission
from django.http import HttpResponseForbidden
from django.db.models import Q, Sum, Count
from .forms import RoleForm, AssignRoleForm





from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Sum
from django.views.decorators.csrf import csrf_protect
from datetime import date, datetime
from rest_framework.views import APIView
from rest_framework.response import Response
from .models import (
    Student, Transaction, Teacher, Staff, StudentPerformance, FeeVoucher,
    AutomationJob, AutomationJobDetail, get_dashboard_stats, StudentBalance,
    NotificationQueue, SalaryVoucher, FeeGenerationSettings, FeeGenerationLog,
    SalaryAutomationSettings, SalaryAutomationJob, SalaryAutomationJobDetail
)
from .forms import StudentRegistrationForm
from .services import (
    FeeGenerationService, SalaryAutomationService, NotificationDispatcherService,
    FixtureAutomationService
)



# ===================================================
# 🔹 STEP 1 — DEFAULT ROLES CREATOR
# ===================================================
def setup_default_roles():
    default_roles = {
        "Teacher": [
            "view_teacher_dashboard",
            "add_result", "change_result", "view_result",
            "add_assignment", "view_assignment",
            "add_quiz", "view_quiz",
        ],
        "Student": [
            "view_student_dashboard",
            "view_result", "view_assignment", "view_quiz",
        ],
        "Parent": [
            "view_parent_dashboard",
            "view_result", "view_student_progress",
        ],
        "Admin": ["__all__"],
    }

    for role_name, perms in default_roles.items():
        group, created = Group.objects.get_or_create(name=role_name)
        if "__all__" in perms:
            group.permissions.set(Permission.objects.all())
        else:
            permissions = Permission.objects.filter(codename__in=perms)
            group.permissions.set(permissions)
        group.save()

    print("✅ Default roles setup complete!")


# ===================================================
# 🔹 STEP 2 — CREATE CUSTOM ROLE
# ===================================================
@login_required
@permission_required('auth.add_group', raise_exception=True)
def create_role(request):
    if request.method == 'POST':
        form = RoleForm(request.POST)
        if form.is_valid():
            role_name = form.cleaned_data['name'].strip()
            permissions = form.cleaned_data['permissions']

            if Group.objects.filter(name__iexact=role_name).exists():
                messages.error(request, f"❌ Role '{role_name}' already exists.")
                return redirect('create_role')

            group = Group.objects.create(name=role_name)
            group.permissions.set(permissions)
            group.save()

            messages.success(request, f"✅ Role '{role_name}' created successfully!")
            return redirect('list_roles')
    else:
        form = RoleForm()

    return render(request, 'admin_panel/create_role.html', {'form': form})


# ===================================================
# 🔹 STEP 3 — LIST ALL ROLES
# ===================================================
@login_required
@permission_required('auth.view_group', raise_exception=True)
def list_roles(request):
    groups = Group.objects.prefetch_related('permissions').all()
    return render(request, 'admin_panel/list_roles.html', {'groups': groups})


from .models import UserRole


# ===================================================
# 🔹 HELPER — Safe Role Assignment
# ===================================================
def assign_role_to_user(user, group):
    user.groups.set([group])
    UserRole.objects.update_or_create(
        user=user,
        defaults={'role': group}
    )


from teacher_dashboard.models import Assignment, Quiz, LectureNote
from django.contrib.auth.decorators import login_required

@login_required
def admin_view_assignments(request):
    assignments = Assignment.objects.all().order_by('-created_at')
    return render(request, 'admin_panel/admin_view_assignments.html', {'assignments': assignments})

@login_required
def admin_view_quizzes(request):
    quizzes = Quiz.objects.all().order_by('-due_date')
    return render(request, 'admin_panel/admin_view_quizzes.html', {'quizzes': quizzes})

@login_required
def admin_view_diaries(request):
    return render(request, 'admin_panel/admin_view_diaries.html', {})

@login_required
def admin_view_lecture_notes(request):
    notes = LectureNote.objects.all().order_by('-created_at')
    return render(request, 'admin_panel/admin_view_lecture_notes.html', {'notes': notes})


# ===================================================
# 🔹 STEP 4 — ASSIGN ROLE TO USER
# ===================================================
@login_required
@permission_required('auth.change_user', raise_exception=True)
def assign_role(request):
    users_with_roles = User.objects.prefetch_related('groups').all()

    if request.method == 'POST':
        form = AssignRoleForm(request.POST)
        if form.is_valid():
            user = form.cleaned_data['user']
            role = form.cleaned_data['role']

            assign_role_to_user(user, role)
            user.groups.clear()
            user.groups.add(role)
            user.save()

            messages.success(request, f"Role '{role.name}' assigned to '{user.username}'!")
            return redirect('assign_role')
    else:
        form = AssignRoleForm()

    return render(request, 'admin_panel/assign_role.html', {
        'form': form,
        'users_with_roles': users_with_roles
    })


# ===================================================
# 🔹 STEP 5 — DASHBOARDS
# ===================================================
@login_required
@permission_required('teacher_dashboard.view_teacher_dashboard', raise_exception=True)
def teacher_dashboard(request):
    return render(request, 'teacher_dashboard/dashboard.html')


@login_required
@permission_required('student_dashboard.view_student_dashboard', raise_exception=True)
def student_profile(request):
    return render(request, 'student_profile/dashboard.html')


@login_required
@permission_required('parent_dashboard.view_parent_dashboard', raise_exception=True)
def parent_dashboard(request):
    return render(request, 'parent_dashboard/dashboard.html')


@login_required
@permission_required('auth.view_group', raise_exception=True)
def admin_dashboard(request):
    return render(request, "admin_panel/index.html")


# ===================================================
# 🔹 STEP 6 — Access Denied Handler
# ===================================================
def access_denied(request):
    return HttpResponseForbidden("🚫 Access Denied: You don't have permission to view this page.")


# =================================================================
from django.views.decorators.cache import never_cache
from django.contrib.auth import logout
from django.shortcuts import redirect, render
from django.contrib.auth import authenticate, login
from django.contrib import messages


@never_cache
def custom_login(request):
    if request.method == "POST":
        username = request.POST.get("username")
        password = request.POST.get("password")

        user = authenticate(request, username=username, password=password)

        if user is None:
            messages.error(request, "Invalid username/password OR user not active.")
            return render(request, "registration/login.html")

        if not user.is_active:
            messages.error(request, "Your account is inactive. Contact admin.")
            return render(request, "registration/login.html")

        login(request, user)

        if user.is_superuser or user.groups.filter(name__iexact="Admin").exists():
            return redirect("admin_dashboard")

        if user.groups.filter(name__iexact="Teacher").exists():
            return redirect("teacher_dashboard")

        if user.groups.filter(name__iexact="Student").exists():
            return redirect("student_profile_home")

        if user.groups.filter(name__iexact="Parent").exists():
            return redirect("parent_dashboard")

        return redirect("admin_dashboard")

    return render(request, "registration/login.html")


@never_cache
def custom_logout(request):
    logout(request)
    return redirect('login')


# ---------------- CREATE ADMIN USER ----------------
from .utils import group_required


@group_required('Admin')
def create_admin_user(request):
    if request.method == "POST":
        email = request.POST.get("email")
        password = request.POST.get("password")
        username = "admin_" + get_random_string(6)

        with transaction.atomic():
            user = User.objects.create_user(
                username=username,
                email=email,
                password=password,
                is_staff=True
            )
            admin_group, _ = Group.objects.get_or_create(name="Admin")
            user.groups.set([admin_group])

        messages.success(request, "Admin user created successfully.")
        return redirect('admin_dashboard')

    return render(request, 'admin_panel/create_admin_user.html')


@login_required
def admin_panel_dashboard(request):
    return render(request, 'admin_panel/index.html')


# ------------------- user_list -------------------
from collections import OrderedDict
from django.contrib.auth.models import User
from admin_panel.models import UserRole


def user_list(request):
    users = User.objects.all().order_by('email')
    unique = []

    for user in users:
        roles = ", ".join([g.name for g in user.groups.all()]) or "No Role"
        unique.append({
            'username': user.username,
            'email': user.email,
            'role': roles
        })

    return render(request, 'admin_panel/user_list.html', {'users_with_roles': unique})


# ==================== ADMISSION WORK ====================
from django.shortcuts import render, redirect
from .forms import AdmissionForm
from .models import Admission, Class, AcademicYear
from django.core.paginator import Paginator


@permission_required('admin_panel.add_admission', raise_exception=True)
def register_admission(request):
    classes = Class.objects.all()
    active_years = AcademicYear.objects.filter(is_active=True)
    selected_year = None

    if request.method == 'POST':
        selected_year = request.POST.get('academic_year')
        form = AdmissionForm(request.POST)
        form.fields['academic_year'].queryset = active_years
        if form.is_valid():
            admission = form.save(commit=False)
            admission.save()
            messages.success(request, "Admission registered successfully.")
            return redirect('admission_list')
        else:
            print("Form Errors:", form.errors)
    else:
        form = AdmissionForm()
        form.fields['academic_year'].queryset = active_years

    context = {
        'form': form,
        'classes': classes,
        'academic_years': active_years,
        'academic_year': int(selected_year) if selected_year else None,
    }
    return render(request, 'admin_panel/registration.html', context)


@permission_required('admin_panel.view_admission', raise_exception=True)
def admission_list(request):
    active_year = AcademicYear.objects.filter(is_active=True).first()
    if active_year:
        admissions = Admission.objects.filter(academic_year=active_year).order_by('id')
    else:
        admissions = Admission.objects.none()

    return render(request, 'admin_panel/admission_list.html', {'admissions': admissions})


@permission_required('admin_panel.change_admission', raise_exception=True)
def update_admission_status(request, pk):
    if request.method == 'POST':
        admission = get_object_or_404(Admission, pk=pk)
        new_status = request.POST.get('admission_status')
        if new_status in ['pending', 'approved', 'rejected']:
            admission.admission_status = new_status
            admission.save()
    return redirect('admission_list')


def is_section_full(section):
    current_count = Admission.objects.filter(section=section).count()
    return current_count >= section.capacity


# -------------------- reject_reason --------------------
from django.core.mail import send_mail, BadHeaderError


@permission_required('admin_panel.change_admission', raise_exception=True)
def reject_reason(request, admission_id):
    admission = get_object_or_404(Admission, id=admission_id)

    if request.method == 'POST':
        reason = request.POST.get('reason')
        admission.admission_status = 'rejected'
        admission.rejection_reason = reason
        admission.save()

        if admission.email:
            try:
                send_mail(
                    subject="Admission Rejected",
                    message=f"Dear {admission.name},\n\nYour admission has been rejected.\n\nReason: {reason}\n\nRegards,\nSchool Administration",
                    from_email="your@email.com",
                    recipient_list=[admission.email],
                    fail_silently=False,
                )
            except BadHeaderError:
                messages.error(request, "Invalid header found when sending email.")
            except Exception as e:
                messages.error(request, f"Failed to send email: {str(e)}")
        else:
            messages.warning(request, "Student email not found; no email was sent.")

        return redirect('admission_list')

    return render(request, 'admin_panel/reject_reason.html', {'admission': admission})


# -------------------- change_admission_status --------------------

from django.db.models import Max
from parent_dashboard.models import Parent
from student_profile.models import Student


def generate_unique_student_id():
    while True:
        try:
            with transaction.atomic():
                max_id = Student.objects.aggregate(max_num=Max('student_id'))['max_num']
                last_num = int(max_id.replace("STD", "")) if max_id else 0
                new_id = f"STD{last_num + 1:04d}"
                if not Student.objects.filter(student_id=new_id).exists():
                    return new_id
        except Exception:
            continue


from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import permission_required
from django.contrib.auth.models import User, Group
from django.core.mail import send_mail
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.crypto import get_random_string
from django.core.paginator import Paginator
from django.db.models import Q

from .models import Admission
from student_profile.models import Student


@permission_required('admin_panel.change_admission', raise_exception=True)
def change_admission_status(request, admission_id):

    print("\n========== FUNCTION START ==========")

    if request.method != 'POST':
        print(">>> NOT POST - returning")
        return redirect('admission_list')

    admission = get_object_or_404(Admission, id=admission_id)
    status = request.POST.get('admission_status')

    print("STATUS        =", repr(status))
    print("EMAIL         =", admission.email)
    print("FATHER EMAIL  =", admission.father_email)
    print("CURRENT DB STATUS =", admission.admission_status)

    # =========================================================
    # APPROVED
    # =========================================================
    if status == 'approved':
        print(">>> ENTERED APPROVED BLOCK")

        student_exists = Student.objects.filter(email=admission.email).exists() if admission.email else False
        user_exists    = User.objects.filter(email=admission.email).exists()    if admission.email else False

        print("STUDENT EXISTS =", student_exists)
        print("USER EXISTS    =", user_exists)

        if student_exists:
            print(">>> Student pehle se exist karta hai — sirf status update")
            admission.admission_status = 'approved'
            admission.save()
            messages.warning(
                request,
                f"⚠️ Is email '{admission.email}' ka student pehle se exist karta hai. "
                f"Naya account nahi banaya, status approved kar diya."
            )
            print("========== FUNCTION END ==========\n")
            return redirect('admission_list')

        if user_exists:
            print(">>> User exist karta hai — delete karke fresh banao")
            User.objects.filter(email=admission.email).delete()
            print(">>> Old user deleted")

        username = admission.student_id or f"STD{get_random_string(6)}"
        password = get_random_string(8)

        print("USERNAME =", username)
        print("PASSWORD =", password)

        try:
            with transaction.atomic():

                print(">>> Creating User...")
                student_user = User.objects.create_user(
                    username=username,
                    email=admission.email or "",
                    password=password,
                    first_name=admission.name,
                )
                print(">>> User created:", student_user.username)

                student_group, _ = Group.objects.get_or_create(name='Student')
                student_user.groups.set([student_group])
                print(">>> Group assigned")

                print(">>> Creating Student profile...")
                Student.objects.update_or_create(
                    student_id=username,
                    defaults={
                        "user":          student_user,
                        "academic_year": admission.academic_year,
                        "name":          admission.name,
                        "father_name":   admission.father_name,
                        "mother_name":   admission.mother_name,
                        "class_fk":      admission.class_fk,
                        "roll_no":       "TEMP",
                        "phone":         admission.contact,
                        "gender":        admission.gender,
                        "date_of_birth": admission.dob,
                        "email":         admission.email,
                        "section":       admission.section,
                    }
                )
                print(">>> Student profile created")

            admission.admission_status = 'approved'
            admission.save()
            print(">>> Admission status = approved")
            print(">>> STUDENT CREATED SUCCESSFULLY")

            school_name = getattr(settings, 'SCHOOL_NAME', 'EduPilot School')
            site_url    = getattr(settings, 'SITE_URL', 'http://127.0.0.1:8000')
            login_url   = f"{site_url}/auth/login/"

            # =========================================================
            # STUDENT KO EMAIL BHEJO
            # =========================================================
            if admission.email:
                student_email_body = f"""Dear {admission.name},

Congratulations! Your admission has been approved.

=============================
  STUDENT LOGIN DETAILS
=============================
Username : {username}
Password : {password}
Login URL: {login_url}
=============================

Regards,
{school_name}
"""
                print(">>> Sending student email to:", admission.email)

                try:
                    result = send_mail(
                        subject=f"Admission Approved - {school_name}",
                        message=student_email_body,
                        from_email=settings.DEFAULT_FROM_EMAIL,
                        recipient_list=[admission.email],
                        fail_silently=False,
                    )
                    print(">>> STUDENT EMAIL RESULT =", result)

                    if result == 1:
                        print(">>> STUDENT EMAIL SENT SUCCESSFULLY ✓")
                        messages.success(
                            request,
                            f"✅ Student '{admission.name}' approved! "
                            f"Login credentials {admission.email} par send ho gaye."
                        )
                    else:
                        print(">>> STUDENT EMAIL NOT SENT (result != 1)")
                        messages.warning(
                            request,
                            f"⚠️ Student bana lekin email nahi gayi. "
                            f"Username: {username} | Password: {password}"
                        )

                except Exception as email_err:
                    print(">>> STUDENT EMAIL ERROR =", str(email_err))
                    messages.warning(
                        request,
                        f"⚠️ Student bana lekin email fail hui: {str(email_err)} | "
                        f"Username: {username} | Password: {password}"
                    )
            else:
                print(">>> NO STUDENT EMAIL ADDRESS FOUND")
                messages.warning(
                    request,
                    f"⚠️ Student approved lekin email address nahi mila. "
                    f"Username: {username} | Password: {password}"
                )

            # =========================================================
            # ✅ PARENT ACCOUNT BANAO + CREDENTIALS EMAIL BHEJO
            # =========================================================
            parent_email = getattr(admission, 'father_email', None)

            if parent_email:
                print(">>> Processing parent account for:", parent_email)
                try:
                    from parent_dashboard.models import Parent as ParentModel

                    # ── Parent ka Django User account banao ya existing use karo ──
                    parent_user_exists = User.objects.filter(email__iexact=parent_email).exists()

                    if parent_user_exists:
                        # Pehle se ek ya zyada accounts hain
                        # Sab users dhundo, pehla wala use karo, baqi delete karo
                        all_parent_users = User.objects.filter(email__iexact=parent_email).order_by('id')
                        parent_user = all_parent_users.first()
                        # Duplicate users delete karo
                        duplicate_ids = list(all_parent_users.values_list('id', flat=True)[1:])
                        if duplicate_ids:
                            User.objects.filter(id__in=duplicate_ids).delete()
                            print(f">>> {len(duplicate_ids)} duplicate parent users deleted")
                        parent_password = get_random_string(8)
                        parent_user.set_password(parent_password)
                        parent_user.save()
                        parent_username = parent_user.username
                        # Parent group assign karo agar nahi hai
                        parent_group, _ = Group.objects.get_or_create(name='Parent')
                        if not parent_user.groups.filter(name='Parent').exists():
                            parent_user.groups.add(parent_group)
                        print(">>> Existing parent user found — password reset:", parent_username)
                    else:
                        # Naya parent user banao
                        parent_username = f"PAR{get_random_string(6)}"
                        parent_password = get_random_string(8)
                        parent_user = User.objects.create_user(
                            username=parent_username,
                            email=parent_email,
                            password=parent_password,
                            first_name=admission.father_name or "Parent",
                        )
                        parent_group, _ = Group.objects.get_or_create(name='Parent')
                        parent_user.groups.set([parent_group])
                        print(">>> New parent user created:", parent_username)

                    # ── ParentModel bhi banao/update karo ──
                    parent_obj, parent_created = ParentModel.objects.get_or_create(
                        email=parent_email,
                        defaults={
                            'full_name': admission.father_name or "Parent",
                            'phone':     admission.contact or "",
                            'email':     parent_email,
                        }
                    )
                    # Parent user se link karo agar field available hai
                    if hasattr(parent_obj, 'user'):
                        parent_obj.user = parent_user
                        parent_obj.save()

                    # ── Student ko parent se link karo ──
                    student_obj = Student.objects.filter(student_id=username).first()
                    if student_obj:
                        parent_obj.students.add(student_obj)
                        print(">>> Student linked to parent ✓")

                    # ── Parent ko credentials ke saath email bhejo ──
                    parent_email_body = (
                        f"Dear {admission.father_name or 'Parent'} / Guardian,\n\n"
                        f"Assalam o Alaikum,\n\n"
                        f"We are pleased to inform you that your child's admission has been successfully approved.\n\n"
                        f"=============================\n"
                        f"  STUDENT DETAILS\n"
                        f"=============================\n"
                        f"Student Name  : {admission.name}\n"
                        f"Class         : {admission.class_fk}\n"
                        f"=============================\n\n"
                        f"  YOUR PARENT PORTAL LOGIN\n"
                        f"=============================\n"
                        f"Username  : {parent_username}\n"
                        f"Password  : {parent_password}\n"
                        f"Login URL : {login_url}\n"
                        f"=============================\n\n"
                        f"Please use the above credentials to login to the Parent Portal\n"
                        f"and track your child's progress, attendance, and results.\n\n"
                        f"For any queries, please contact the school administration.\n\n"
                        f"Regards,\n"
                        f"{school_name}\n"
                    )

                    parent_result = send_mail(
                        subject=f"Child Admission Approved & Parent Portal Access - {school_name}",
                        message=parent_email_body,
                        from_email=settings.DEFAULT_FROM_EMAIL,
                        recipient_list=[parent_email],
                        fail_silently=False,
                    )
                    print(">>> PARENT EMAIL RESULT =", parent_result)

                    if parent_result == 1:
                        print(">>> PARENT EMAIL WITH CREDENTIALS SENT SUCCESSFULLY ✓")
                        messages.success(
                            request,
                            f"✅ Parent portal credentials '{parent_email}' par send ho gaye. "
                            f"Parent Username: {parent_username}"
                        )
                    else:
                        print(">>> PARENT EMAIL NOT SENT (result != 1)")
                        messages.warning(
                            request,
                            f"⚠️ Parent account bana lekin email nahi gayi. "
                            f"Parent Username: {parent_username} | Password: {parent_password}"
                        )

                except Exception as parent_err:
                    print(">>> PARENT ACCOUNT/EMAIL ERROR =", str(parent_err))
                    messages.warning(
                        request,
                        f"⚠️ Parent account ya email mein masla: {str(parent_err)}"
                    )
            else:
                print(">>> NO PARENT EMAIL (father_email) FOUND — skipping parent account creation")

        except Exception as main_err:
            print(">>> MAIN ERROR =", str(main_err))
            messages.error(request, f"❌ Student account nahi bana: {str(main_err)}")

        print("========== FUNCTION END ==========\n")
        return redirect('admission_list')

    # =========================================================
    # REJECTED / PENDING
    # =========================================================
    print(">>> STATUS is not approved — updating to:", status)
    admission.admission_status = status
    admission.save(update_fields=['admission_status'])
    print("========== FUNCTION END ==========\n")
    return redirect('admission_list')


# -------------------- query --------------------

@permission_required('admin_panel.view_admission', raise_exception=True)
def query(request):
    q_val        = request.GET.get('q', '').strip()
    status       = request.GET.get('status', '')
    academic_year = request.GET.get('academic_year', '')

    admissions = Admission.objects.select_related('section', 'class_fk', 'academic_year')

    if q_val:
        admissions = admissions.filter(
            Q(student_id__icontains=q_val)       |
            Q(name__icontains=q_val)             |
            Q(academic_year__year__icontains=q_val) |
            Q(admission_status__icontains=q_val) |
            Q(class_fk__class_name__icontains=q_val) |
            Q(section__section_name__icontains=q_val) |
            Q(email__icontains=q_val)            |
            Q(contact__icontains=q_val)          |
            Q(father_name__icontains=q_val)      |
            Q(mother_name__icontains=q_val)      |
            Q(campus__icontains=q_val)           |
            Q(branch__icontains=q_val)           |
            Q(ref_no__icontains=q_val)           |
            Q(dob__icontains=q_val)              |
            Q(gender__iexact=q_val)              |
            Q(address__icontains=q_val)          |
            Q(father_cnic__icontains=q_val)
        )

    if status:
        admissions = admissions.filter(admission_status=status)

    if academic_year:
        admissions = admissions.filter(academic_year=academic_year)

    paginator   = Paginator(admissions, 10)
    page_number = request.GET.get("page")
    page_obj    = paginator.get_page(page_number)

    context = {
        'admissions':   admissions,
        'query':        q_val,
        'status':       status,
        'academic_year': academic_year,
        'page_obj':     page_obj,
    }

    return render(request, 'admin_panel/query.html', context)


# -------------------- Classes CRUD --------------------
from django.db.models import Count, Q
from .models import Class
from .forms import ClassForm


@permission_required('admin_panel.view_class', raise_exception=True)
def class_list(request):
    classes = Class.objects.annotate(
        approved_students=Count('admission', filter=Q(admission__admission_status='approved'))
    )
    return render(request, 'admin_panel/class_list.html', {'classes': classes})


@permission_required('admin_panel.add_class', raise_exception=True)
def class_create(request):
    if request.method == 'POST':
        form = ClassForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('class_list')
    else:
        form = ClassForm()
    return render(request, 'admin_panel/class_form.html', {'form': form})


@permission_required('admin_panel.change_class', raise_exception=True)
def class_update(request, pk):
    class_obj = get_object_or_404(Class, pk=pk)
    if request.method == 'POST':
        form = ClassForm(request.POST, instance=class_obj)
        if form.is_valid():
            form.save()
            return redirect('class_list')
    else:
        form = ClassForm(instance=class_obj)
    return render(request, 'admin_panel/class_form.html', {'form': form})


@permission_required('admin_panel.delete_class', raise_exception=True)
def class_delete(request, pk):
    class_obj = get_object_or_404(Class, pk=pk)
    if request.method == 'POST':
        class_obj.delete()
        return redirect('class_list')
    return render(request, 'admin_panel/class_confirm_delete.html', {'class': class_obj})


# -------------------- Academic Year CRUD --------------------
from .models import AcademicYear
from .forms import AcademicYearForm


@permission_required('admin_panel.view_academicyear', raise_exception=True)
def academic_year_list(request):
    years = AcademicYear.objects.all()
    return render(request, 'admin_panel/academic_year_list.html', {'years': years})


@permission_required('admin_panel.add_academicyear', raise_exception=True)
def add_academic_year(request):
    if request.method == 'POST':
        form = AcademicYearForm(request.POST)
        if form.is_valid():
            if form.cleaned_data['is_active']:
                AcademicYear.objects.update(is_active=False)
            form.save()
            return redirect('academic_year_list')
    else:
        form = AcademicYearForm()
    return render(request, 'admin_panel/academic_year_form.html', {'form': form})


@permission_required('admin_panel.change_academicyear', raise_exception=True)
def update_academic_year(request, pk):
    year = get_object_or_404(AcademicYear, pk=pk)
    if request.method == 'POST':
        form = AcademicYearForm(request.POST, instance=year)
        if form.is_valid():
            if form.cleaned_data['is_active']:
                AcademicYear.objects.update(is_active=False)
            form.save()
            return redirect('academic_year_list')
    else:
        form = AcademicYearForm(instance=year)
    return render(request, 'admin_panel/academic_year_form.html', {'form': form})


@permission_required('admin_panel.delete_academicyear', raise_exception=True)
def delete_academic_year(request, pk):
    year = get_object_or_404(AcademicYear, pk=pk)
    if request.method == 'POST':
        year.delete()
        return redirect('academic_year_list')
    return render(request, 'admin_panel/academic_year_confirm_delete.html', {'year': year})


# -------------------- Section CRUD --------------------
from .models import Section, AcademicYear, Class, Admission
from .forms import SectionForm


@permission_required('admin_panel.add_section', raise_exception=True)
def add_section(request):
    if request.method == 'POST':
        form = SectionForm(request.POST)
        form.fields['academic_year'].queryset = AcademicYear.objects.filter(is_active=True)
        if form.is_valid():
            form.save()
            return redirect('section_list')
    else:
        form = SectionForm()
        form.fields['academic_year'].queryset = AcademicYear.objects.filter(is_active=True)
    return render(request, 'admin_panel/add_section.html', {'form': form})


from django.db.models import F, IntegerField, ExpressionWrapper


@permission_required('admin_panel.view_section', raise_exception=True)
def section_list(request):
    sections = Section.objects.select_related('academic_year', 'class_fk').annotate(
        approved_admissions_count=Count(
            'admission',
            filter=Q(admission__admission_status='approved')
        ),
        available_seats=ExpressionWrapper(
            F('capacity') - Count(
                'admission',
                filter=Q(admission__admission_status='approved')
            ),
            output_field=IntegerField()
        )
    )
    return render(request, 'admin_panel/section_list.html', {'sections': sections})


@permission_required('admin_panel.change_section', raise_exception=True)
def edit_section(request, pk):
    section = get_object_or_404(Section, pk=pk)
    if request.method == 'POST':
        form = SectionForm(request.POST, instance=section)
        if form.is_valid():
            form.save()
            return redirect('section_list')
    else:
        form = SectionForm(instance=section)
    return render(request, 'admin_panel/edit_section.html', {'form': form})


@permission_required('admin_panel.delete_section', raise_exception=True)
def delete_section(request, pk):
    section = get_object_or_404(Section, pk=pk)
    if request.method == 'POST':
        section.delete()
        return redirect('section_list')
    return render(request, 'admin_panel/delete_section.html', {'section': section})


# -------------------- Subject CRUD --------------------
from .models import Subject
from .forms import SubjectForm


@permission_required('admin_panel.view_subject', raise_exception=True)
def subject_list(request):
    subjects = Subject.objects.all()
    return render(request, 'admin_panel/subject_list.html', {'subjects': subjects})


@permission_required('admin_panel.add_subject', raise_exception=True)
def add_subject(request):
    if request.method == 'POST':
        form = SubjectForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('subject_list')
        else:
            print("Form errors:", form.errors)
    else:
        form = SubjectForm()
    return render(request, 'admin_panel/subject_form.html', {'form': form, 'subject': None})


@permission_required('admin_panel.change_subject', raise_exception=True)
def edit_subject(request, pk):
    subject = get_object_or_404(Subject, pk=pk)
    if request.method == 'POST':
        form = SubjectForm(request.POST, instance=subject)
        if form.is_valid():
            form.save()
            return redirect('subject_list')
    else:
        form = SubjectForm(instance=subject)
    return render(request, 'admin_panel/subject_form.html', {'form': form, 'subject': subject})


@permission_required('admin_panel.delete_subject', raise_exception=True)
def delete_subject(request, pk):
    subject = get_object_or_404(Subject, pk=pk)
    if request.method == 'POST':
        subject.delete()
        return redirect('subject_list')
    return render(request, 'admin_panel/subject_confirm_delete.html', {'subject': subject})


# -------------------- Teacher CRUD --------------------
from teacher_dashboard.models import Teacher
from admin_panel.forms import TeacherForm
from django.core.paginator import Paginator
from django.utils.text import slugify
import uuid


@permission_required('teacher_dashboard.view_teacher', raise_exception=True)
def teacher_list(request):
    teachers = Teacher.objects.all()
    paginator = Paginator(teachers, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    return render(request, 'admin_panel/teacher_list.html', {
        'page_obj': page_obj,
        'teachers': page_obj.object_list
    })


DEFAULT_TEACHER_PASSWORD = "ex"


@permission_required("teacher_dashboard.add_teacher", raise_exception=True)
def teacher_create(request):
    teacher_group, _ = Group.objects.get_or_create(name="Teacher")

    if request.method == "POST":
        form = TeacherForm(request.POST, request.FILES)
        if form.is_valid():
            teacher = form.save(commit=False)

            if teacher.user:
                teacher.save()
                form.save_m2m()
                messages.success(request, "Teacher updated.")
                return redirect("teacher_list")

            if User.objects.filter(email__iexact=teacher.email).exists():
                messages.error(request, "A user with this email already exists.")
                return render(request, "admin_panel/teacher_form.html", {"form": form})

            base = slugify(teacher.name) or "teacher"
            username = f"{base}_{str(uuid.uuid4())[:5]}"

            with transaction.atomic():
                user = User.objects.create_user(
                    username=username,
                    email=teacher.email,
                    password=DEFAULT_TEACHER_PASSWORD,
                    first_name=teacher.name
                )
                user.groups.set([teacher_group])
                teacher.user = user
                teacher.save()
                form.save_m2m()

            try:
                send_mail(
                    subject="Teacher account created",
                    message=f"Username: {user.username}\nPassword: {DEFAULT_TEACHER_PASSWORD}",
                    from_email=getattr(settings, "DEFAULT_FROM_EMAIL", None),
                    recipient_list=[teacher.email],
                    fail_silently=True
                )
            except Exception:
                pass

            messages.success(request, "Teacher added and user created.")
            return redirect("teacher_list")

        messages.error(request, "Please fix the errors below.")
    else:
        form = TeacherForm()

    return render(request, "admin_panel/teacher_form.html", {"form": form})


@permission_required('teacher_dashboard.change_teacher', raise_exception=True)
def teacher_update(request, pk):
    teacher = get_object_or_404(Teacher, pk=pk)

    if request.method == 'POST':
        form = TeacherForm(request.POST, request.FILES, instance=teacher)
        selected_faculties = request.POST.getlist('faculty_group')
        if form.is_valid():
            form.save()
            messages.success(request, 'Teacher updated successfully.')
            return redirect('teacher_list')
    else:
        form = TeacherForm(instance=teacher)
        selected_faculties = teacher.faculty_group

    return render(request, 'admin_panel/teacher_form.html', {
        'form': form, 'title': 'Edit Teacher', 'selected_faculties': selected_faculties
    })


@permission_required('teacher_dashboard.delete_teacher', raise_exception=True)
def teacher_delete(request, pk):
    teacher = get_object_or_404(Teacher, pk=pk)
    if request.method == 'POST':
        teacher.delete()
        messages.success(request, 'Teacher deleted successfully.')
        return redirect('teacher_list')
    return render(request, 'admin_panel/teacher_confirm_delete.html', {'teacher': teacher})


# ==================== PERIOD PLANNING ====================
from .models import CreatePeriod, Subject, SubjectPeriod, Section
from .forms import CreatePeriodForm, AssignedPeriodForm
from django.http import JsonResponse, HttpResponseBadRequest
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt


@permission_required('admin_panel.add_createperiod', raise_exception=True)
def create_period_view(request):
    if request.method == 'POST':
        form = CreatePeriodForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('period_list')
    else:
        form = CreatePeriodForm()
    return render(request, 'admin_panel/create_period.html', {'form': form})


@permission_required('admin_panel.view_createperiod', raise_exception=True)
def period_list_view(request):
    periods = CreatePeriod.objects.all().order_by('day', 'start_time')
    return render(request, 'admin_panel/period_list.html', {'periods': periods})


@permission_required('admin_panel.change_createperiod', raise_exception=True)
def update_period_view(request, pk):
    period = get_object_or_404(CreatePeriod, pk=pk)
    if request.method == 'POST':
        form = CreatePeriodForm(request.POST, instance=period)
        if form.is_valid():
            form.save()
            return redirect('period_list')
    else:
        form = CreatePeriodForm(instance=period)
    return render(request, 'admin_panel/update_period.html', {'form': form})


@permission_required('admin_panel.delete_createperiod', raise_exception=True)
def delete_period_view(request, pk):
    period = get_object_or_404(CreatePeriod, pk=pk)
    if request.method == 'POST':
        period.delete()
        return redirect('period_list')
    return render(request, 'admin_panel/delete_period.html', {'period': period})


# -------------------- Timetable View --------------------
from .models import (
    Subject, SubjectPeriod, Section, Class, ClassGroup, AssignedPeriod,
    TeacherFixture, ClassTeacher, TeacherAbsence, TeacherFixtureCandidateLog,
    TeacherFixtureNotificationLog
)


@permission_required('admin_panel.view_subjectperiod', raise_exception=True)
def timetable_automation(request):
    groups = ClassGroup.objects.all().order_by('group_name')
    selected_group_id = request.GET.get('group')
    selected_group = None
    automation_result = None

    if request.method == 'POST':
        action = request.POST.get('action', 'run')

        if action in ['cancel_fixture', 'mark_uncovered', 'rerun_fixture', 'replace_substitute']:
            fixture = get_object_or_404(TeacherFixture.objects.select_related('assigned_period', 'substitute_teacher'), id=request.POST.get('fixture_id'))
            override_reason = request.POST.get('override_reason', '').strip() or f'Admin action: {action}'

            if action == 'cancel_fixture':
                fixture.fixture_status = 'cancelled'
                fixture.override_reason = override_reason
                fixture.overridden_by = request.user
                fixture.overridden_at = timezone.now()
                fixture.assignment_mode = 'overridden'
                fixture.save(update_fields=['fixture_status', 'override_reason', 'overridden_by', 'overridden_at', 'assignment_mode'])
                messages.success(request, 'Fixture cancelled and override logged.')
                return redirect('timetable_automation')

            if action == 'mark_uncovered':
                fixture.fixture_status = 'uncovered'
                fixture.override_reason = override_reason
                fixture.overridden_by = request.user
                fixture.overridden_at = timezone.now()
                fixture.assignment_mode = 'overridden'
                fixture.save(update_fields=['fixture_status', 'override_reason', 'overridden_by', 'overridden_at', 'assignment_mode'])
                messages.success(request, 'Fixture marked as uncovered.')
                return redirect('timetable_automation')

            if action == 'replace_substitute':
                substitute_id = request.POST.get('substitute_teacher_id')
                replacement = get_object_or_404(Teacher, id=substitute_id, status='active')
                if not fixture.original_substitute_teacher_id:
                    fixture.original_substitute_teacher = fixture.substitute_teacher
                fixture.substitute_teacher = replacement
                fixture.fixture_status = 'reassigned'
                fixture.assignment_mode = 'overridden'
                fixture.override_reason = override_reason
                fixture.overridden_by = request.user
                fixture.overridden_at = timezone.now()
                fixture.save()
                messages.success(request, f'Fixture reassigned to {replacement.name}.')
                return redirect('timetable_automation')

            if action == 'rerun_fixture' and fixture.assigned_period:
                fixture.fixture_status = 'cancelled'
                fixture.override_reason = override_reason
                fixture.overridden_by = request.user
                fixture.overridden_at = timezone.now()
                fixture.assignment_mode = 'overridden'
                fixture.save(update_fields=['fixture_status', 'override_reason', 'overridden_by', 'overridden_at', 'assignment_mode'])
                automation_result = FixtureAutomationService.run_for_absence(
                    teacher=fixture.absent_teacher,
                    target_date=fixture.fixture_date,
                    source='manual',
                    triggered_by=request.user,
                )
                messages.success(request, 'Fixture cancelled and automation re-run.')
            elif action == 'rerun_fixture':
                messages.error(request, 'This fixture cannot be re-run because it is not linked to an assigned period.')
                return redirect('timetable_automation')

        teacher_id = request.POST.get('teacher_id')
        absence_date = request.POST.get('absence_date')

        if automation_result is None and (not teacher_id or not absence_date):
            messages.error(request, 'Please select absent teacher and date.')
            return redirect('timetable_automation')

        if automation_result is None:
            absent_teacher = get_object_or_404(Teacher, id=teacher_id)
            automation_result = FixtureAutomationService.run_for_absence(
                teacher=absent_teacher,
                target_date=absence_date,
                source='manual',
                triggered_by=request.user,
            )

        assigned_count = len(automation_result.get('assigned', []))
        unassigned_count = len(automation_result.get('unassigned', []))
        skipped_count = len(automation_result.get('skipped', []))
        if assigned_count:
            messages.success(
                request,
                f'Auto fixture completed: {assigned_count} assigned, {unassigned_count} unassigned, {skipped_count} skipped.'
            )
        else:
            messages.warning(
                request,
                f'Auto fixture completed with no new assignments: {unassigned_count} unassigned, {skipped_count} skipped.'
            )

    if selected_group_id:
        selected_group = get_object_or_404(ClassGroup, id=selected_group_id)
    elif groups.exists():
        selected_group = groups.first()

    group_subject_count = 0
    configured_subject_count = 0
    missing_allocation_count = 0
    planned_periods = 0
    assigned_group_periods = 0

    if selected_group:
        group_class_ids = Class.objects.filter(group=selected_group).values_list('id', flat=True)
        group_subjects = Subject.objects.filter(class_fk_id__in=group_class_ids).order_by('name')
        subject_names = set(group_subjects.values_list('name', flat=True))
        group_subject_count = len(subject_names)

        allocation_map = {}
        for sp in SubjectPeriod.objects.filter(group=selected_group, subject__class_fk_id__in=group_class_ids).select_related('subject'):
            key = (sp.subject.name, sp.day)
            allocation_map[key] = max(allocation_map.get(key, 0), sp.periods)

        planned_by_subject = {}
        for (subject_name, _day), periods in allocation_map.items():
            planned_by_subject[subject_name] = planned_by_subject.get(subject_name, 0) + periods

        configured_subject_count = len([name for name, total in planned_by_subject.items() if total > 0])
        missing_allocation_count = max(group_subject_count - configured_subject_count, 0)
        planned_periods = sum(planned_by_subject.values())
        assigned_group_periods = AssignedPeriod.objects.filter(class_fk_id__in=group_class_ids).count()

    duplicate_teacher_slots = AssignedPeriod.objects.values(
        'teacher_id', 'day', 'period_id'
    ).annotate(total=Count('id')).filter(total__gt=1).count()

    recent_fixtures = TeacherFixture.objects.select_related(
        'class_fk', 'section', 'period', 'subject', 'absent_teacher', 'substitute_teacher', 'assigned_period'
    ).order_by('-id')[:5]

    today = date.today()
    fixture_stats = {
        'total': TeacherFixture.objects.count(),
        'today': TeacherFixture.objects.filter(fixture_date=today).count(),
        'absent_teachers': TeacherFixture.objects.values('absent_teacher_id').distinct().count(),
        'substitute_teachers': TeacherFixture.objects.values('substitute_teacher_id').distinct().count(),
    }

    classes = Class.objects.all().order_by('class_name')
    sections = Section.objects.select_related('class_fk').order_by('class_fk__class_name', 'section_name')
    class_teacher_count = ClassTeacher.objects.count()
    teachers = Teacher.objects.filter(status='active').order_by('name')
    today_absences = TeacherAbsence.objects.filter(absence_date=today).select_related('teacher').order_by('-created_at')
    latest_absence = None
    if automation_result:
        latest_absence = automation_result.get('absence')
    elif today_absences.exists():
        latest_absence = today_absences.first()
    latest_absence_results = []
    if latest_absence:
        latest_absence_results = latest_absence.results.select_related(
            'assigned_period__class_fk', 'assigned_period__section', 'assigned_period__subject',
            'assigned_period__period', 'fixture__substitute_teacher'
        )
    visible_fixtures = TeacherFixture.objects.select_related(
        'class_fk', 'section', 'period', 'subject', 'absent_teacher', 'substitute_teacher', 'assigned_period'
    ).order_by('-fixture_date', '-id')[:10]
    uncovered_results = TeacherAbsence.objects.filter(
        results__status='unassigned'
    ).select_related('teacher').distinct().order_by('-absence_date')[:10]
    candidate_logs = TeacherFixtureCandidateLog.objects.select_related(
        'teacher', 'assigned_period__subject', 'assigned_period__period'
    ).order_by('-created_at')[:20]
    notification_logs = TeacherFixtureNotificationLog.objects.select_related(
        'recipient_teacher', 'fixture'
    ).order_by('-created_at')[:10]
    workflow_steps = FixtureAutomationService.workflow_steps()

    return render(request, 'admin_panel/timetable_automation.html', {
        'groups': groups,
        'selected_group': selected_group,
        'group_subject_count': group_subject_count,
        'configured_subject_count': configured_subject_count,
        'missing_allocation_count': missing_allocation_count,
        'planned_periods': planned_periods,
        'assigned_group_periods': assigned_group_periods,
        'unassigned_periods': max(planned_periods - assigned_group_periods, 0),
        'assignment_count': AssignedPeriod.objects.count(),
        'duplicate_teacher_slots': duplicate_teacher_slots,
        'fixture_stats': fixture_stats,
        'recent_fixtures': recent_fixtures,
        'classes': classes,
        'sections': sections,
        'class_teacher_count': class_teacher_count,
        'teachers': teachers,
        'today_absences': today_absences,
        'latest_absence': latest_absence,
        'latest_absence_results': latest_absence_results,
        'today': today,
        'visible_fixtures': visible_fixtures,
        'uncovered_results': uncovered_results,
        'candidate_logs': candidate_logs,
        'notification_logs': notification_logs,
        'workflow_steps': workflow_steps,
    })


@permission_required('admin_panel.view_subjectperiod', raise_exception=True)
def timetable_view(request):
    days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
    groups = ClassGroup.objects.all()
    selected_group_id = request.GET.get('group') or request.POST.get('group')
    subjects = []
    saved_periods = {}

    if selected_group_id:
        selected_group = ClassGroup.objects.get(id=selected_group_id)
        classes = Class.objects.filter(group=selected_group)
        class_ids = classes.values_list('id', flat=True)
        all_subjects = Subject.objects.filter(class_fk_id__in=class_ids).order_by('name')

        seen = set()
        for subj in all_subjects:
            if subj.name not in seen:
                seen.add(subj.name)
                subjects.append(subj)

        all_sp = SubjectPeriod.objects.filter(group=selected_group)
        for sp in all_sp:
            saved_periods.setdefault(sp.subject_id, {})[sp.day] = sp.periods

    timetable_summary = {
        'selected_group_name': '',
        'total_subjects': len(subjects),
        'weekly_allocated_periods': 0,
        'remaining_periods': 36,
        'missing_subjects': 0,
        'is_over_limit': False,
    }

    if selected_group_id:
        selected_group = ClassGroup.objects.get(id=selected_group_id)
        timetable_summary['selected_group_name'] = selected_group.group_name
        for subject in subjects:
            subject_total = sum((saved_periods.get(subject.id, {}) or {}).values())
            timetable_summary['weekly_allocated_periods'] += subject_total
            if subject_total == 0:
                timetable_summary['missing_subjects'] += 1
        timetable_summary['remaining_periods'] = 36 - timetable_summary['weekly_allocated_periods']
        timetable_summary['is_over_limit'] = timetable_summary['remaining_periods'] < 0

    if request.method == 'POST' and selected_group_id:
        selected_group = ClassGroup.objects.get(id=selected_group_id)

        for subject in subjects:
            subject_name = subject.name
            for day in days:
                key = f'periods_{subject.id}_{day}'
                value = int(request.POST.get(key) or 0)

                matching_subjects = Subject.objects.filter(
                    name=subject_name,
                    class_fk__group=selected_group
                )
                for subj in matching_subjects:
                    SubjectPeriod.objects.update_or_create(
                        subject=subj,
                        group=selected_group,
                        day=day,
                        defaults={'periods': value}
                    )

        return redirect(f'{request.path}?group={selected_group_id}')

    return render(request, 'admin_panel/timetable.html', {
        'groups': groups,
        'subjects': subjects,
        'days': days,
        'selected_group_id': int(selected_group_id) if selected_group_id else None,
        'saved_periods': saved_periods,
        'timetable_summary': timetable_summary
    })


# -------------------- Assign Period --------------------
@permission_required('admin_panel.add_assignedperiod', raise_exception=True)
def assign_period_view(request):
    form = AssignedPeriodForm()
    classes = Class.objects.all()

    if request.method == 'POST':
        form = AssignedPeriodForm(request.POST)
        if form.is_valid():
            form.save()
            return JsonResponse({'success': True})
        else:
            print("Form errors:", form.errors)
            return JsonResponse({
                'success': False,
                'error': form.errors.get_json_data()
            }, status=400)

    return render(request, 'admin_panel/assign_period.html', {
        'form': form,
        'classes': classes
    })


# -------------------- AJAX Endpoints --------------------
from .models import (
    Subject, SubjectPeriod, Section, Class, ClassGroup,
    AssignedPeriod, CreatePeriod
)


def get_teachers_for_subject(request):
    subject_id = request.GET.get('subject_id')
    teachers = Teacher.objects.filter(subjects__id=subject_id).values('id', 'name')
    return JsonResponse(list(teachers), safe=False)


def filter_subject_periods(request):
    subject_id = request.GET.get('subject_id')
    if not subject_id:
        return JsonResponse({'error': 'No subject provided'}, status=400)

    assigned_days = AssignedPeriod.objects.filter(subject_id=subject_id).values_list('day', flat=True).distinct()
    teacher_ids = AssignedPeriod.objects.filter(subject_id=subject_id).values_list('teacher_id', flat=True).distinct()
    teachers = list(Teacher.objects.filter(id__in=teacher_ids).values('id', 'name'))

    return JsonResponse({'days': list(assigned_days), 'teachers': teachers})


def get_time_slots_for_subject_day(request):
    subject_id = request.GET.get('subject_id')
    day = request.GET.get('day')

    if not subject_id or not day:
        return JsonResponse({'error': 'Missing subject or day'}, status=400)

    assigned_periods = AssignedPeriod.objects.filter(subject_id=subject_id, day=day)
    period_ids = assigned_periods.values_list('period_id', flat=True)
    periods = CreatePeriod.objects.filter(id__in=period_ids).order_by('start_time')

    period_data = [
        {
            'id': p.id,
            'label': f"{p.period_name} ({p.start_time.strftime('%I:%M %p')} - {p.end_time.strftime('%I:%M %p')})"
        }
        for p in periods
    ]
    return JsonResponse({'periods': period_data})


def get_days_for_subject(request):
    subject_id = request.GET.get('subject_id')
    section_id = request.GET.get('section_id')

    if subject_id and section_id:
        try:
            section = Section.objects.get(id=section_id)
            group = section.class_fk.group
            subject = Subject.objects.get(id=subject_id)
            class_ids = Class.objects.filter(group=group).values_list('id', flat=True)
            subject_ids = Subject.objects.filter(class_fk_id__in=class_ids, name=subject.name).values_list('id', flat=True)

            subject_periods = SubjectPeriod.objects.filter(
                subject_id__in=subject_ids,
                group=group,
                periods__gt=0
            )
            days = subject_periods.values_list('day', 'periods').distinct()
            result = [{'day': day, 'label': f"{day} ({periods})"} for day, periods in days]
            return JsonResponse(result, safe=False)
        except Section.DoesNotExist:
            return JsonResponse([], safe=False)
    return JsonResponse([], safe=False)


def ajax_subject_periods(request):
    subject_id = request.GET.get('subject_id')
    try:
        subject = Subject.objects.get(id=subject_id)
        teachers = subject.teachers.all()
        data = {"teachers": [{"id": t.id, "name": t.name} for t in teachers]}
    except Subject.DoesNotExist:
        data = {"teachers": []}
    return JsonResponse(data)


def ajax_time_slots(request):
    subject_id = request.GET.get('subject_id')
    day = request.GET.get('day')
    section_id = request.GET.get('section_id')
    print("Incoming Data: ", subject_id, day, section_id)

    if not subject_id or not day or not section_id:
        return JsonResponse({'error': 'Missing data'}, status=400)

    try:
        section = Section.objects.get(id=section_id)
        group = section.class_fk.group
        subject = Subject.objects.get(id=subject_id)
        class_ids = Class.objects.filter(group=group).values_list('id', flat=True)
        subject_ids = Subject.objects.filter(
            class_fk_id__in=class_ids,
            name=subject.name
        ).values_list('id', flat=True)

        subject_period = SubjectPeriod.objects.filter(
            subject_id__in=subject_ids,
            group=group,
            day=day,
            periods__gt=0
        ).first()

        all_periods = CreatePeriod.objects.filter(day=day).order_by('start_time')

        data = {
            "assignable": subject_period.periods if subject_period else 0,
            "periods": [
                {
                    "id": p.id,
                    "label": f"{p.period_name} ({p.start_time.strftime('%I:%M %p')} - {p.end_time.strftime('%I:%M %p')})"
                } for p in all_periods
            ]
        }
        return JsonResponse(data)

    except (Section.DoesNotExist, Subject.DoesNotExist):
        return JsonResponse({'error': 'Invalid subject or section'}, status=400)


def get_subjects_for_section(request):
    section_id = request.GET.get('section_id')
    if not section_id:
        return JsonResponse({'error': 'Missing section id'}, status=400)
    section = get_object_or_404(Section, id=section_id)
    subjects = Subject.objects.filter(class_fk=section.class_fk).values('id', 'name')
    return JsonResponse(list(subjects), safe=False)


def get_sections_for_class(request):
    class_id = request.GET.get('class_id')
    if not class_id:
        return JsonResponse({'error': 'Missing class_id'}, status=400)
    sections = Section.objects.filter(class_fk_id=class_id).values('id', 'section_name')
    data = [{'id': s['id'], 'name': s['section_name']} for s in sections]
    return JsonResponse(data, safe=False)


def get_periods_for_day(request):
    subject_id = request.GET.get('subject_id')
    day = request.GET.get('day')
    section_id = request.GET.get('section_id')

    if subject_id and day and section_id:
        periods = SubjectPeriod.objects.filter(
            subject_id=subject_id, section_id=section_id, day=day
        ).values('period_id', 'period__label')
        period_list = [{'id': p['period_id'], 'label': p['period__label']} for p in periods]
        return JsonResponse({'periods': period_list})

    return JsonResponse({'periods': []})


# -------------------- Class Group --------------------
@permission_required('admin_panel.view_classgroup', raise_exception=True)
def add_class_group(request):
    if request.method == 'POST':
        name = request.POST.get('group_name')
        ClassGroup.objects.create(group_name=name)
        return redirect('class_group_list')
    return render(request, 'admin_panel/add_group.html')


@permission_required('admin_panel.view_classgroup', raise_exception=True)
def class_group_list(request):
    groups = ClassGroup.objects.all()
    return render(request, 'admin_panel/class_group_list.html', {'groups': groups})


@require_http_methods(["DELETE"])
@csrf_exempt
def delete_assignment(request, assignment_id):
    try:
        assignment = AssignedPeriod.objects.get(id=assignment_id)
        assignment.delete()
        return JsonResponse({'success': True})
    except AssignedPeriod.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Assignment not found'}, status=404)


def get_assigned_classes(request):
    assignments = AssignedPeriod.objects.select_related('class_fk', 'section', 'period', 'subject', 'teacher').all()
    data = []
    for a in assignments:
        data.append({
            'id': a.id,
            'class_name': a.class_fk.class_name if a.class_fk else 'N/A',
            'section_name': a.section.section_name if a.section else 'N/A',
            'subject_name': a.subject.name if a.subject else 'N/A',
            'day_label': a.get_day_display() if hasattr(a, 'get_day_display') else a.day,
            'period_label': f"{a.period.period_name} ({a.period.start_time.strftime('%I:%M %p')} - {a.period.end_time.strftime('%I:%M %p')})" if a.period else 'N/A',
            'teacher_name': a.teacher.name if a.teacher else 'N/A',
        })
    return JsonResponse(data, safe=False)


def edit_class_group(request, group_id):
    group = get_object_or_404(ClassGroup, id=group_id)
    if request.method == 'POST':
        name = request.POST.get('group_name')
        group.group_name = name
        group.save()
        return redirect('class_group_list')
    return render(request, 'admin_panel/edit_group.html', {'group': group})


def delete_class_group(request, group_id):
    group = get_object_or_404(ClassGroup, id=group_id)
    group.delete()
    return redirect('class_group_list')


# -------------------- Class Teacher --------------------
from admin_panel.models import ClassTeacher, AcademicYear, Class, Section
from teacher_dashboard.models import Teacher


@permission_required('admin_panel.view_classteacher', raise_exception=True)
def class_teacher_list(request):
    assignments = ClassTeacher.objects.all()
    return render(request, 'admin_panel/class_teacher_list.html', {'assignments': assignments})


def class_teacher_create(request):
    classes = Class.objects.all()
    academic_years = AcademicYear.objects.all()

    if request.method == 'POST':
        academic_year = request.POST.get('academic_year')
        class_id = request.POST.get('class_fk')
        section_id = request.POST.get('section')
        teacher_id = request.POST.get('teacher')

        if academic_year and class_id and section_id and teacher_id:
            existing = ClassTeacher.objects.filter(
                academic_year_id=academic_year,
                class_fk_id=class_id,
                section_id=section_id,
                teacher_id=teacher_id
            ).first()

            if existing:
                teacher = Teacher.objects.get(id=teacher_id)
                return render(request, 'admin_panel/class_teacher_form.html', {
                    'classes': classes,
                    'academic_years': academic_years,
                    'error': f"❌ Teacher '{teacher.name}' is already assigned to this class and section."
                })

            ClassTeacher.objects.create(
                academic_year_id=academic_year,
                class_fk_id=class_id,
                section_id=section_id,
                teacher_id=teacher_id
            )
            return redirect('class_teacher_list')
        else:
            return render(request, 'admin_panel/class_teacher_form.html', {
                'classes': classes,
                'academic_years': academic_years,
                'error': 'Please fill all required fields.'
            })

    return render(request, 'admin_panel/class_teacher_form.html', {
        'classes': classes,
        'academic_years': academic_years
    })


def class_teacher_update(request, pk):
    assignment = get_object_or_404(ClassTeacher, pk=pk)
    academic_years = AcademicYear.objects.all()
    classes = Class.objects.all()
    sections = Section.objects.all()
    teachers = Teacher.objects.all()

    if request.method == 'POST':
        assignment.academic_year_id = request.POST.get('academic_year')
        assignment.class_fk_id = request.POST.get('class_fk')
        assignment.section_id = request.POST.get('section')
        assignment.teacher_id = request.POST.get('teacher')
        assignment.save()
        return redirect('class_teacher_list')

    context = {
        'assignment': assignment,
        'academic_years': academic_years,
        'classes': classes,
        'sections': sections,
        'teachers': teachers,
    }
    return render(request, 'admin_panel/class_teacher_form.html', context)


def class_teacher_delete(request, pk):
    assignment = get_object_or_404(ClassTeacher, pk=pk)
    if request.method == 'POST':
        assignment.delete()
        return redirect('class_teacher_list')
    return render(request, 'admin_panel/class_teacher_confirm_delete.html', {'assignment': assignment})


def ajax_load_sections(request):
    class_id = request.GET.get('class_id')
    if class_id:
        sections = Section.objects.filter(class_fk_id=class_id).values('id', 'section_name')
        return JsonResponse({'sections': list(sections)})
    return JsonResponse({'sections': []})


def ajax_load_teachers_by_class(request):
    class_id = request.GET.get('class_id')
    section_id = request.GET.get('section_id')

    assigned = AssignedPeriod.objects.filter(
        class_fk_id=class_id,
        section_id=section_id
    ).select_related('teacher')

    unique_teachers = {a.teacher for a in assigned}
    data = [{'id': t.id, 'name': t.name} for t in unique_teachers]
    return JsonResponse({'teachers': data})


# ==================== PORTFOLIO / TIMETABLE PDF ====================
from django.template.loader import render_to_string
from django.http import HttpResponse, JsonResponse


def _get_portfolio_timetable_data(class_obj, section_obj):
    from admin_panel.models import ClassTeacher

    all_periods = CreatePeriod.objects.all().order_by('day', 'start_time')
    monday_periods = all_periods.filter(day='Monday')
    period_order = [p.period_name for p in monday_periods]
    for p in all_periods:
        if p.period_name not in period_order:
            period_order.append(p.period_name)

    days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']

    teacher_obj = ClassTeacher.objects.filter(class_fk=class_obj, section=section_obj).first()
    teacher_name = teacher_obj.teacher.name if teacher_obj else None

    slots = {}
    for day in days:
        assigned_periods = AssignedPeriod.objects.filter(
            class_fk=class_obj, section=section_obj, day=day
        ).select_related('period', 'subject', 'teacher')
        assigned_map = {ap.period.period_name: ap for ap in assigned_periods}
        day_slots = {}
        for pname in period_order:
            ap = assigned_map.get(pname)
            if ap:
                day_slots[pname] = f"{ap.subject.name} ({ap.teacher.name})<br><small>{ap.period.start_time.strftime('%I:%M %p')} - {ap.period.end_time.strftime('%I:%M %p')}</small>"
            else:
                day_slots[pname] = "---"
        slots[day] = day_slots

    return period_order, slots, days, teacher_name


def get_sections(request):
    class_id = request.GET.get('class_id')
    if class_id:
        sections = Section.objects.filter(class_fk_id=class_id).values('id', 'section_name')
        return JsonResponse({'sections': list(sections)})
    return JsonResponse({'sections': []})


def extract_period_number(period_name):
    try:
        left = period_name.split(':')[0]
        parts = left.strip().split()
        for part in parts:
            digits = ''.join(filter(str.isdigit, part))
            if digits:
                return int(digits)
    except Exception:
        pass
    return 9999


@permission_required('admin_panel.view_assignedperiod', raise_exception=True)
def portfolio_timetable(request):
    class_id = request.GET.get('class_id')
    section_id = request.GET.get('section_id')

    classes = Class.objects.all()
    timetable_data = None
    class_info = section_info = teacher_name = None
    timetable_summary = {
        'class_name': '-',
        'section_name': '-',
        'class_teacher': 'Not Assigned',
        'assigned_periods': 0,
        'empty_periods': 0,
    }

    if class_id and section_id:
        class_obj = get_object_or_404(Class, id=class_id)
        section_obj = get_object_or_404(Section, id=section_id)

        period_order, slots, days, teacher_name = _get_portfolio_timetable_data(class_obj, section_obj)

        timetable_data = {
            'period_order': period_order,
            'slots': slots,
            'days': days
        }
        class_info = class_obj
        section_info = section_obj
        assigned_periods = AssignedPeriod.objects.filter(class_fk=class_obj, section=section_obj).count()
        total_slots = len(period_order) * len(days)
        timetable_summary = {
            'class_name': class_obj.class_name,
            'section_name': section_obj.section_name,
            'class_teacher': teacher_name or 'Not Assigned',
            'assigned_periods': assigned_periods,
            'empty_periods': max(total_slots - assigned_periods, 0),
        }

    return render(request, 'admin_panel/portfolio_timetable.html', {
        'classes': classes,
        'timetable_data': timetable_data,
        'class_info': class_info,
        'section_info': section_info,
        'teacher_name': teacher_name,
        'timetable_summary': timetable_summary
    })


@permission_required('admin_panel.view_assignedperiod', raise_exception=True)
def timetable_pdf(request):
    class_id = request.GET.get('class_id')
    section_id = request.GET.get('section_id')

    if not class_id or not section_id:
        return HttpResponse("Class or Section not provided", status=400)

    class_obj = get_object_or_404(Class, id=class_id)
    section_obj = get_object_or_404(Section, id=section_id)

    period_order, slots, days, teacher_name = _get_portfolio_timetable_data(class_obj, section_obj)

    html_string = render_to_string('admin_panel/timetable_pdf.html', {
        'class_info': class_obj,
        'section_info': section_obj,
        'period_order': period_order,
        'slots': slots,
        'days': days,
        'teacher_name': teacher_name
    })

    try:
        from weasyprint import HTML as WeasyHTML
        pdf = WeasyHTML(string=html_string).write_pdf()
    except OSError as e:
        return HttpResponse(
            f"PDF generation failed: WeasyPrint libraries not installed. {e}",
            status=500
        )

    response = HttpResponse(pdf, content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="timetable_{class_obj.class_name}_{section_obj.section_name}.pdf"'
    return response


# ==================== ID CARD ====================
from student_profile.models import Student


@permission_required('student_profile.view_studentidcard', raise_exception=True)
def generate_student_id_card(request, student_id):
    student = get_object_or_404(Student, id=student_id)
    return render(request, 'admin_panel/id_card.html', {'student': student})


@permission_required('admin_panel.view_admission', raise_exception=True)
def student_id_card_list(request):
    students = Student.objects.all()
    return render(request, 'admin_panel/student_id_card_list.html', {'students': students})


def upload_student_photo(request, student_id):
    if request.method == "POST" and request.FILES.get("photo"):
        student = get_object_or_404(Student, id=student_id)
        student.photo = request.FILES["photo"]
        student.save()
    return redirect('student_id_card_list')


# ==================== STREAM ====================
from .models import Stream


@permission_required('admin_panel.view_stream', raise_exception=True)
def stream_list(request):
    streams = Stream.objects.all()
    return render(request, "admin_panel/stream_list.html", {"streams": streams})


@permission_required('admin_panel.add_stream', raise_exception=True)
def add_stream(request):
    if request.method == "POST":
        name = request.POST.get("stream_name")
        if name:
            Stream.objects.create(stream_name=name)
            return redirect("stream_list")
    return render(request, "admin_panel/stream_form.html")


@permission_required('admin_panel.change_stream', raise_exception=True)
def edit_stream(request, pk):
    stream = get_object_or_404(Stream, pk=pk)
    if request.method == "POST":
        stream.stream_name = request.POST.get("stream_name")
        stream.save()
        return redirect("stream_list")
    return render(request, "admin_panel/stream_form.html", {"stream": stream})


@permission_required('admin_panel.delete_stream', raise_exception=True)
def delete_stream(request, pk):
    stream = get_object_or_404(Stream, pk=pk)
    stream.delete()
    return redirect("stream_list")


def my_view(request):
    return HttpResponse("Hello, this is my_view!")


# ==================== EXAMINATION ====================
from .models import ExamFormat, Question


@login_required
@permission_required('admin_panel.view_examformat', raise_exception=True)
def format_list(request):
    classes = Class.objects.all()
    subjects = Subject.objects.all()
    class_id = request.GET.get("class_id")
    subject_id = request.GET.get("subject_id")
    formats = ExamFormat.objects.select_related("class_obj", "subject").all()
    if class_id:
        formats = formats.filter(class_obj_id=class_id)
    if subject_id:
        formats = formats.filter(subject_id=subject_id)
    return render(request, "admin_panel/format_list.html", {
        "formats": formats, "classes": classes, "subjects": subjects,
    })


@login_required
@permission_required('admin_panel.change_examformat', raise_exception=True)
def edit_format(request, format_id):
    exam_format = get_object_or_404(ExamFormat, id=format_id)
    if request.method == "POST":
        exam_format.format_name = request.POST.get("format_name")
        exam_format.num_mcqs = request.POST.get("num_mcqs")
        exam_format.num_short = request.POST.get("num_short")
        exam_format.num_long = request.POST.get("num_long")
        exam_format.class_obj_id = request.POST.get("class")
        exam_format.subject_id = request.POST.get("subject")
        exam_format.save()
        messages.success(request, "Exam format updated successfully!")
        return redirect("format_list")
    classes = Class.objects.all()
    subjects = Subject.objects.all()
    return render(request, "admin_panel/edit_format.html", {
        "exam_format": exam_format, "classes": classes, "subjects": subjects,
    })


@login_required
@permission_required('admin_panel.delete_examformat', raise_exception=True)
def delete_format(request, format_id):
    exam_format = get_object_or_404(ExamFormat, id=format_id)
    exam_format.delete()
    messages.success(request, "Exam format deleted successfully!")
    return redirect("format_list")


@permission_required('admin_panel.add_examformat', raise_exception=True)
def create_format(request):
    if request.method == "POST":
        ExamFormat.objects.create(
            class_obj_id=request.POST.get("class"),
            subject_id=request.POST.get("subject"),
            format_name=request.POST.get("format_name"),
            num_mcqs=request.POST.get("num_mcqs"),
            num_short=request.POST.get("num_short"),
            num_long=request.POST.get("num_long"),
        )
        return redirect("format_list")
    classes = Class.objects.all()
    subjects = Subject.objects.all()
    return render(request, "admin_panel/create_format.html", {"classes": classes, "subjects": subjects})


@login_required
@permission_required('admin_panel.view_examformat', raise_exception=True)
def format_questions(request, format_id):
    exam_format = get_object_or_404(
        ExamFormat.objects.select_related("class_obj", "subject"), id=format_id
    )
    questions = Question.objects.select_related("teacher", "section").filter(exam_format=exam_format)
    return render(request, "admin_panel/format_questions.html", {
        "exam_format": exam_format, "questions": questions,
    })


@permission_required('admin_panel.view_question', raise_exception=True)
def all_questions(request):
    questions = Question.objects.select_related("exam_format", "teacher", "section")
    return render(request, "admin_panel/all_questions.html", {"questions": questions})


# ==================== PAPER GENERATION ====================
import random
from math import ceil
from django.db.models import Count
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas


@login_required
@permission_required('admin_panel.view_examformat', raise_exception=True)
def generate_paper_confirm(request, format_id):
    exam_format = get_object_or_404(
        ExamFormat.objects.select_related("class_obj", "subject"), id=format_id
    )
    if request.method == "POST":
        return generate_question_paper_pdf(request, format_id)
    return render(request, "admin_panel/generate_paper_confirm.html", {"exam_format": exam_format})


def _pick_most_common_questions(queryset, needed):
    if needed <= 0:
        return []
    grouped = (
        queryset.values("text")
        .annotate(cnt=Count("id"))
        .order_by("-cnt")
    )
    selected = []
    used_texts = set()
    for g in grouped:
        if len(selected) >= needed:
            break
        txt = g["text"]
        if txt in used_texts:
            continue
        q = queryset.filter(text=txt).first()
        if q:
            selected.append(q)
            used_texts.add(txt)
    return selected


def _pick_random_questions(queryset, needed, exclude_ids=None):
    if needed <= 0:
        return []
    qs = queryset
    if exclude_ids:
        qs = qs.exclude(id__in=exclude_ids)
    total = qs.count()
    if total == 0:
        return []
    if total <= needed:
        return list(qs)
    ids = list(qs.values_list("id", flat=True))
    sampled_ids = random.sample(ids, needed)
    return list(qs.filter(id__in=sampled_ids))


def generate_question_paper_pdf(request, format_id):
    exam_format = get_object_or_404(
        ExamFormat.objects.select_related("class_obj", "subject"), id=format_id
    )
    all_questions = Question.objects.filter(exam_format=exam_format)
    mcq_needed = getattr(exam_format, "num_mcqs", 0) or 0
    short_needed = getattr(exam_format, "num_short", 0) or 0
    long_needed = getattr(exam_format, "num_long", 0) or 0

    selected_questions = []

    mcq_qs = all_questions.filter(question_type__iexact="MCQ")
    mcq_most_common = _pick_most_common_questions(mcq_qs, ceil(mcq_needed * 0.5))
    selected_ids = [q.id for q in mcq_most_common]
    mcq_random = _pick_random_questions(mcq_qs, mcq_needed - len(mcq_most_common), exclude_ids=selected_ids)
    selected_questions.extend(mcq_most_common)
    selected_questions.extend(mcq_random)

    short_qs = all_questions.filter(question_type__iexact="SHORT")
    short_most_common = _pick_most_common_questions(short_qs, ceil(short_needed * 0.5))
    selected_ids = selected_ids + [q.id for q in short_most_common]
    short_random = _pick_random_questions(short_qs, short_needed - len(short_most_common), exclude_ids=selected_ids)
    selected_questions.extend(short_most_common)
    selected_questions.extend(short_random)

    long_qs = all_questions.filter(question_type__iexact="LONG")
    long_most_common = _pick_most_common_questions(long_qs, ceil(long_needed * 0.5))
    selected_ids = selected_ids + [q.id for q in long_most_common]
    long_random = _pick_random_questions(long_qs, long_needed - len(long_most_common), exclude_ids=selected_ids)
    selected_questions.extend(long_most_common)
    selected_questions.extend(long_random)

    response = HttpResponse(content_type="application/pdf")
    filename = f"Exam_Paper_{exam_format.format_name.replace(' ', '_')}.pdf"
    response["Content-Disposition"] = f'attachment; filename="{filename}"'

    p = canvas.Canvas(response, pagesize=A4)
    width, height = A4
    y = height - 60

    p.setFont("Helvetica-Bold", 16)
    p.drawCentredString(width / 2, y, f"Exam Paper — {exam_format.format_name}")
    y -= 30
    p.setFont("Helvetica", 12)
    p.drawCentredString(width / 2, y, f"Class: {exam_format.class_obj.class_name}    Subject: {exam_format.subject.name}")
    y -= 40

    p.setFont("Helvetica-Bold", 13)
    p.drawString(50, y, "Section A: MCQs")
    y -= 20
    p.setFont("Helvetica", 11)
    idx = 1
    for q in [qq for qq in selected_questions if qq.question_type.upper() == "MCQ"]:
        if y < 100:
            p.showPage()
            y = height - 60
        p.drawString(50, y, f"{idx}. {q.text}")
        y -= 16
        for attr, letter in [("option_a", "A"), ("option_b", "B"), ("option_c", "C"), ("option_d", "D")]:
            if hasattr(q, attr):
                p.drawString(70, y, f"{letter}) {getattr(q, attr)}")
                y -= 14
        y -= 8
        idx += 1

    p.setFont("Helvetica-Bold", 13)
    p.drawString(50, y, "Section B: Short Questions")
    y -= 20
    p.setFont("Helvetica", 11)
    idx = 1
    for q in [qq for qq in selected_questions if qq.question_type.upper() == "SHORT"]:
        if y < 100:
            p.showPage()
            y = height - 60
        p.drawString(50, y, f"{idx}. {q.text}")
        y -= 30
        idx += 1

    p.setFont("Helvetica-Bold", 13)
    p.drawString(50, y, "Section C: Long Questions")
    y -= 20
    p.setFont("Helvetica", 11)
    idx = 1
    for q in [qq for qq in selected_questions if qq.question_type.upper() == "LONG"]:
        if y < 100:
            p.showPage()
            y = height - 60
        p.drawString(50, y, f"{idx}. {q.text}")
        y -= 50
        idx += 1

    p.save()
    return response


def generate_question_paper(request, format_id=None):
    if format_id:
        exam_format = get_object_or_404(ExamFormat, id=format_id)
        context = {"format": exam_format}
    else:
        context = {"format": None}
    return render(request, "admin_panel/generate_question_paper.html", context)


# ==================== BOOK UPLOAD ====================
from .models import Book
from .forms import BookUploadForm
from .ml_toc_parser import parse_book_toc_ml


@permission_required('admin_panel.add_book', raise_exception=True)
def upload_book(request):
    if request.method == "POST":
        form = BookUploadForm(request.POST, request.FILES)
        if form.is_valid():
            book = form.save(commit=False)
            book.uploaded_by = request.user
            book.save()
            try:
                parse_book_toc_ml(book)
                messages.success(request, f"Book '{book.title}' uploaded and TOC parsed successfully!")
            except Exception as e:
                messages.warning(request, f"Book uploaded but TOC parsing failed: {e}")
            return redirect('upload_book')
        else:
            messages.error(request, "Form invalid. Please check the uploaded file.")
    else:
        form = BookUploadForm()

    books = Book.objects.all().order_by('-uploaded_at')
    return render(request, 'admin_panel/upload_book.html', {'form': form, 'books': books})


def book_detail(request, pk):
    book = get_object_or_404(Book.objects.prefetch_related('chapters__topics__subtopics'), pk=pk)
    return render(request, 'admin_panel/book_detail.html', {'book': book})


def book_list(request):
    books = Book.objects.all().order_by('-id')
    return render(request, "admin_panel/book_list.html", {"books": books})


# ==================== TEACHER DATA ====================
from teacher_dashboard.models import AssignedPeriod as TeacherAssignedPeriod


@login_required
def get_teacher_data(request, teacher_id):
    teacher = get_object_or_404(Teacher, id=teacher_id)
    periods = TeacherAssignedPeriod.objects.filter(teacher=teacher).select_related(
        'class_fk', 'section', 'subject'
    )
    data = []
    for p in periods:
        data.append({
            'class_id': p.class_fk.id,
            'class_name': p.class_fk.class_name,
            'section_id': p.section.id,
            'section_name': p.section.section_name,
            'subject_id': p.subject.id,
            'subject_name': p.subject.name
        })
    return JsonResponse({'assigned': data})


# ==================== FIXTURE MANAGEMENT ====================
from .models import TeacherFixture


@permission_required('admin_panel.add_teacherfixture', raise_exception=True)
def manage_fixture(request):
    classes = Class.objects.all()
    sections = Section.objects.all()
    periods = CreatePeriod.objects.all()
    subjects = Subject.objects.all()
    teachers = Teacher.objects.filter(status='active')
    fixtures = TeacherFixture.objects.select_related(
        "class_fk", "section", "period",
        "absent_teacher", "substitute_teacher", "subject"
    ).order_by("-id")
    today = date.today()
    fixture_summary = {
        'total': fixtures.count(),
        'today': TeacherFixture.objects.filter(fixture_date=today).count(),
        'workload_limit': 3,
        'active_teachers': teachers.count(),
    }

    if request.method == 'POST':
        class_id = request.POST.get("class_fk")
        section_id = request.POST.get("section")
        subject_id = request.POST.get("subject")
        period_id = request.POST.get("period")
        day = request.POST.get("day")
        fixture_date = request.POST.get("fixture_date") or today
        absent_teacher_id = request.POST.get("absent_teacher")
        substitute_teacher_id = request.POST.get("substitute_teacher")

        if TeacherFixture.objects.filter(
            class_fk_id=class_id, section_id=section_id,
            period_id=period_id, day=day, fixture_date=fixture_date
        ).exists():
            messages.error(request, "❌ Fixture already assigned for this class/period.")
            return redirect("manage_fixture")

        if subject_id:
            subject_ok = Teacher.objects.filter(id=substitute_teacher_id, subjects__id=subject_id).exists()
            if not subject_ok:
                messages.error(request, "❌ Substitute teacher cannot teach this subject.")
                return redirect("manage_fixture")

        if TeacherFixture.objects.filter(substitute_teacher_id=substitute_teacher_id, fixture_date=fixture_date).count() >= 3:
            messages.error(request, "❌ Teacher workload limit reached for today.")
            return redirect("manage_fixture")

        TeacherFixture.objects.create(
            absent_teacher_id=absent_teacher_id,
            substitute_teacher_id=substitute_teacher_id,
            class_fk_id=class_id,
            section_id=section_id,
            subject_id=subject_id or None,
            period_id=period_id,
            day=day,
            fixture_date=fixture_date,
            source='manual',
            automation_status='assigned'
        )
        messages.success(request, "✅ Fixture Assigned Successfully!")
        return redirect("manage_fixture")

    return render(request, "admin_panel/manage_fixture.html", {
        'classes': classes, 'sections': sections, 'periods': periods,
        'subjects': subjects, 'teachers': teachers, 'fixtures': fixtures,
        'fixture_summary': fixture_summary,
    })


def get_free_teachers(request):
    try:
        day = request.GET.get('day')
        period_id = request.GET.get('period_id')
        subject_id = request.GET.get('subject_id')
        fixture_date = request.GET.get('fixture_date') or date.today()

        if not period_id:
            return JsonResponse({'error': 'Missing period'}, status=400)

        busy_from_timetable = AssignedPeriod.objects.filter(
            day=day, period_id=period_id
        ).values_list('teacher_id', flat=True)

        busy_from_fixtures = TeacherFixture.objects.filter(
            day=day, period_id=period_id, fixture_date=fixture_date
        ).values_list('substitute_teacher_id', flat=True)

        all_busy_ids = set(busy_from_timetable) | set(busy_from_fixtures)
        free_teachers = Teacher.objects.filter(status='active').exclude(id__in=all_busy_ids)

        if subject_id:
            free_teachers = free_teachers.filter(subjects__id=subject_id)

        free_teachers = [
            t for t in free_teachers
            if TeacherFixture.objects.filter(substitute_teacher=t, fixture_date=fixture_date).count() < 3
        ]

        free_teachers_sorted = sorted(
            free_teachers,
            key=lambda t: (
                TeacherFixture.objects.filter(substitute_teacher=t).count(),
                AssignedPeriod.objects.filter(teacher=t).count()
            )
        )

        data = [{'id': t.id, 'name': t.name} for t in free_teachers_sorted]
        return JsonResponse(data, safe=False)

    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


# ==================== HR / EMPLOYEE ====================
from .models import (Department, Designation, Employee, StaffCategory, JobType, LeaveType, LeaveApplication)


@permission_required('admin_panel.view_department', raise_exception=True)
def department_list(request):
    departments = Department.objects.all()
    return render(request, 'admin_panel/department_list.html', {'departments': departments})


@permission_required('admin_panel.add_department', raise_exception=True)
def department_create(request):
    if request.method == 'POST':
        Department.objects.create(
            name=request.POST.get('name'),
            description=request.POST.get('description', '')
        )
        return redirect('department_list')
    return render(request, 'admin_panel/department_form.html')


@permission_required('admin_panel.view_designation', raise_exception=True)
def designation_list(request):
    designations = Designation.objects.select_related('department')
    return render(request, 'admin_panel/designation_list.html', {'designations': designations})


@permission_required('admin_panel.add_designation', raise_exception=True)
def designation_create(request):
    departments = Department.objects.all()
    if request.method == 'POST':
        Designation.objects.create(
            department_id=request.POST.get('department'),
            title=request.POST.get('title')
        )
        return redirect('designation_list')
    return render(request, 'admin_panel/designation_form.html', {'departments': departments})


@permission_required('admin_panel.view_employee', raise_exception=True)
def employee_list(request):
    employees = Employee.objects.all()
    return render(request, 'admin_panel/employee_list.html', {'employees': employees})


from .forms import EmployeeForm, TeacherFromEmployeeForm


def employee_create(request):
    if request.method == "POST":
        form = EmployeeForm(request.POST, request.FILES)
        if form.is_valid():
            with transaction.atomic():
                employee = form.save()
                is_teacher = form.cleaned_data.get("is_teacher")

                if is_teacher:
                    teacher_group, _ = Group.objects.get_or_create(name="Teacher")
                    user = None
                    if employee.user:
                        user = employee.user
                    else:
                        username = slugify(employee.name) + "_" + str(uuid.uuid4())[:5]
                        user = User.objects.create_user(
                            username=username,
                            email=employee.email,
                            password="default123",
                            first_name=employee.name
                        )
                        user.groups.set([teacher_group])
                        employee.user = user
                        employee.save(update_fields=["user"])

                    teacher, _created = Teacher.objects.get_or_create(
                        email=employee.email,
                        defaults={
                            "user": user,
                            "name": employee.name,
                            "phone": employee.phone,
                            "gender": form.cleaned_data.get("teacher_gender") or "Male",
                            "qualification": form.cleaned_data.get("teacher_qualification") or "Matric",
                            "experience": form.cleaned_data.get("teacher_experience") or 0,
                            "Address": form.cleaned_data.get("teacher_address") or "",
                            "department": form.cleaned_data.get("teacher_department") or "",
                            "faculty_group": form.cleaned_data.get("teacher_faculty_group") or [],
                        }
                    )

                    teacher.user = user
                    teacher.name = employee.name
                    teacher.phone = employee.phone
                    teacher.gender = form.cleaned_data.get("teacher_gender") or teacher.gender
                    teacher.qualification = form.cleaned_data.get("teacher_qualification") or teacher.qualification
                    exp = form.cleaned_data.get("teacher_experience")
                    teacher.experience = exp if exp is not None else teacher.experience
                    teacher.Address = form.cleaned_data.get("teacher_address") or teacher.Address
                    teacher.department = form.cleaned_data.get("teacher_department") or teacher.department
                    teacher.faculty_group = form.cleaned_data.get("teacher_faculty_group") or teacher.faculty_group

                    if request.FILES.get("teacher_image"):
                        teacher.image = request.FILES.get("teacher_image")

                    teacher.save()

                    teacher_subjects = form.cleaned_data.get("teacher_subjects")
                    if teacher_subjects is not None:
                        teacher.subjects.set(teacher_subjects)

            messages.success(request, "Employee created successfully.")
            return redirect("employee_list")
        else:
            messages.error(request, "Please correct the errors below.")
    else:
        form = EmployeeForm()

    return render(request, "admin_panel/employee_form.html", {"form": form})


@permission_required('admin_panel.change_employee', raise_exception=True)
def employee_edit(request, pk):
    employee = get_object_or_404(Employee, pk=pk)
    if request.method == 'POST':
        form = EmployeeForm(request.POST, instance=employee)
        if form.is_valid():
            form.save()
            return redirect('employee_list')
    else:
        form = EmployeeForm(instance=employee)
    return render(request, 'admin_panel/employee_form.html', {'form': form, 'title': 'Edit Employee'})


# ==================== LEAVE ====================
from django.utils import timezone
from datetime import date


def calculate_leave_days(start_date, end_date):
    return (end_date - start_date).days + 1


@permission_required('admin_panel.add_leaveapplication', raise_exception=True)
def leave_create(request):
    employees = Employee.objects.all()
    leave_types = LeaveType.objects.all()

    if request.method == 'POST':
        employee = get_object_or_404(Employee, id=request.POST.get('employee'))
        leave_type = get_object_or_404(LeaveType, id=request.POST.get('leave_type'))
        start_date = date.fromisoformat(request.POST.get('start_date'))
        end_date = date.fromisoformat(request.POST.get('end_date'))
        reason = request.POST.get('reason')

        if not employee.can_apply_leave():
            messages.error(request, "Employee is not eligible for leave (probation not completed).")
            return redirect('leave_create')

        if leave_type not in employee.job_type.allowed_leave_types.all():
            messages.error(request, "This leave type is not allowed for this job type.")
            return redirect('leave_create')

        overlap = LeaveApplication.objects.filter(
            employee=employee,
            start_date__lte=end_date,
            end_date__gte=start_date,
            status__in=['pending', 'approved']
        )
        if overlap.exists():
            messages.error(request, "Employee already has leave during these dates.")
            return redirect('leave_create')

        requested_days = calculate_leave_days(start_date, end_date)

        approved_leaves = LeaveApplication.objects.filter(
            employee=employee,
            leave_type=leave_type,
            status='approved',
            start_date__year=date.today().year
        )
        used_days = sum(calculate_leave_days(l.start_date, l.end_date) for l in approved_leaves)
        remaining_days = leave_type.yearly_quota - used_days

        if requested_days > remaining_days:
            messages.error(request, f"Leave quota exceeded. Remaining days: {remaining_days}")
            return redirect('leave_create')

        LeaveApplication.objects.create(
            employee=employee,
            leave_type=leave_type,
            start_date=start_date,
            end_date=end_date,
            reason=reason
        )
        messages.success(request, "Leave applied successfully.")
        return redirect('leave_list')

    return render(request, 'admin_panel/leave_form.html', {
        'employees': employees, 'leave_types': leave_types
    })


@permission_required('admin_panel.view_leaveapplication', raise_exception=True)
def leave_list(request):
    leaves = LeaveApplication.objects.select_related('employee', 'leave_type').order_by('-applied_at')
    return render(request, 'admin_panel/leave_list.html', {'leaves': leaves})


@permission_required('admin_panel.change_leaveapplication', raise_exception=True)
def leave_action(request, pk, action):
    leave = get_object_or_404(LeaveApplication, pk=pk)
    if action in ['approved', 'rejected']:
        leave.status = action
        leave.action_date = timezone.now()
        leave.save()
        if action == 'approved':
            automation_results = FixtureAutomationService.run_for_leave(leave, triggered_by=request.user)
            assigned_count = sum(len(result.get('assigned', [])) for result in automation_results)
            unassigned_count = sum(len(result.get('unassigned', [])) for result in automation_results)
            skipped_count = sum(len(result.get('skipped', [])) for result in automation_results)
            if automation_results:
                messages.success(
                    request,
                    f'Leave approved. Auto fixture result: {assigned_count} assigned, {unassigned_count} unassigned, {skipped_count} skipped.'
                )
            else:
                messages.warning(
                    request,
                    'Leave approved, but no linked teacher profile was found for fixture automation.'
                )
    return redirect('leave_list')


# ==================== STAFF CATEGORY & JOB TYPE ====================
from .forms import StaffCategoryForm, JobTypeForm


@permission_required('admin_panel.view_staffcategory', raise_exception=True)
def staff_category_list(request):
    categories = StaffCategory.objects.all()
    return render(request, 'admin_panel/staff_category_list.html', {'categories': categories})


@permission_required('admin_panel.add_staffcategory', raise_exception=True)
def staff_category_create(request):
    if request.method == 'POST':
        form = StaffCategoryForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('staff_category_list')
    else:
        form = StaffCategoryForm()
    return render(request, 'admin_panel/staff_category_form.html', {'form': form})


@permission_required('admin_panel.view_jobtype', raise_exception=True)
def job_type_list(request):
    job_types = JobType.objects.all()
    return render(request, 'admin_panel/job_type_list.html', {'job_types': job_types})


@permission_required('admin_panel.add_jobtype', raise_exception=True)
def job_type_create(request):
    if request.method == 'POST':
        form = JobTypeForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('job_type_list')
    else:
        form = JobTypeForm()
    return render(request, 'admin_panel/job_type_form.html', {'form': form})


# ==================== LEAVE TYPE ====================
from .forms import LeaveTypeForm


@permission_required('admin_panel.view_leavetype', raise_exception=True)
def leave_type_list(request):
    leave_types = LeaveType.objects.all()
    return render(request, 'admin_panel/leave_type_list.html', {'leave_types': leave_types})


@permission_required('admin_panel.add_leavetype', raise_exception=True)
def leave_type_create(request):
    if request.method == 'POST':
        form = LeaveTypeForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('leave_type_list')
    else:
        form = LeaveTypeForm()
    return render(request, 'admin_panel/leave_type_form.html', {'form': form})


# ==================== APPRAISAL ====================
from django.contrib.auth.decorators import user_passes_test, login_required
from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render
from admin_panel.models import AppraisalCycle, TeacherAppraisalSubmission, KpiTemplate, KpiRule
from .appraisal_services import generate_score, predict_band, train_random_forest


def is_admin(user):
    return user.is_superuser or user.is_staff or user.groups.filter(name__iexact="Admin").exists()


@login_required
@user_passes_test(is_admin)
def admin_kpi_builder(request):
    cycle = AppraisalCycle.objects.filter(is_open=True).order_by("-start_date").first()
    if not cycle:
        messages.error(request, "No open appraisal cycle found.")
        return redirect("admin_dashboard")

    template = KpiTemplate.objects.filter(cycle=cycle).order_by("-id").first()
    if not template:
        template = KpiTemplate.objects.create(name=f"KPI Template - {cycle.name}", cycle=cycle)

    auto_keys = [k for k, _ in KpiRule.AUTO_KPI_KEYS]
    for k, label in KpiRule.AUTO_KPI_KEYS:
        KpiRule.objects.get_or_create(
            template=template,
            kpi_key=k,
            defaults={
                "title": label,
                "weight": 0,
                "target_value": 0,
                "scoring_method": "linear",
                "is_active": True,
                "is_manual": False,
            },
        )

    if request.method == "POST" and request.POST.get("save_kpis") == "1":
        for k in auto_keys:
            rule = template.rules.filter(kpi_key=k, is_manual=False).first()
            if not rule:
                continue
            active = request.POST.get(f"auto_active_{k}") == "on"
            w = request.POST.get(f"auto_weight_{k}") or "0"
            try:
                rule.weight = float(w)
            except Exception:
                rule.weight = 0.0
            rule.is_active = active
            rule.save(update_fields=["weight", "is_active"])

        manual_rules = list(template.rules.filter(is_manual=True).order_by("id"))
        for r in manual_rules:
            if request.POST.get(f"manual_delete_{r.id}") == "on":
                r.delete()
                continue
            r.is_active = request.POST.get(f"manual_active_{r.id}") == "on"
            r.title = (request.POST.get(f"manual_title_{r.id}") or r.title).strip()
            w = request.POST.get(f"manual_weight_{r.id}") or str(r.weight or 0)
            try:
                r.weight = float(w)
            except Exception:
                pass
            r.save()

        new_titles = request.POST.getlist("manual_title[]")
        new_weights = request.POST.getlist("manual_weight[]")
        for idx, t in enumerate(new_titles):
            t = (t or "").strip()
            if not t:
                continue
            w = 0.0
            if idx < len(new_weights):
                try:
                    w = float(new_weights[idx] or 0)
                except Exception:
                    w = 0.0
            KpiRule.objects.create(
                template=template,
                title=t,
                weight=w,
                is_active=True,
                is_manual=True,
                scoring_method="linear",
                target_value=10,
            )

        messages.success(request, "KPI rules saved successfully.")
        return redirect("admin_kpi_builder")

    auto_kpis = template.rules.filter(is_manual=False, kpi_key__in=auto_keys).order_by("id")
    manual_rules = template.rules.filter(is_manual=True).order_by("id")

    return render(request, "admin_panel/appraisal_admin_kpis.html", {
        "cycle": cycle,
        "template": template,
        "auto_kpis": auto_kpis,
        "manual_rules": manual_rules,
    })


@login_required
@user_passes_test(is_admin)
def admin_appraisal_list(request):
    cycle = AppraisalCycle.objects.filter(is_open=True).order_by("-start_date").first()
    qs = TeacherAppraisalSubmission.objects.select_related("teacher", "cycle").order_by("-updated_at")
    if cycle:
        qs = qs.filter(cycle=cycle)
    return render(request, "admin_panel/appraisal_admin_list.html", {
        "cycle": cycle, "submissions": qs
    })


@login_required
@user_passes_test(is_admin)
def admin_appraisal_detail(request, pk):
    submission = get_object_or_404(TeacherAppraisalSubmission, pk=pk)
    generate_score(submission)
    pred = predict_band(submission)

    if request.method == "POST":

        if request.POST.get("save_final_band"):
            submission.final_band = request.POST.get("final_band", "")
            submission.save(update_fields=["final_band"])
            messages.success(request, "Final band saved.")
            return redirect("admin_appraisal_detail", pk=pk)

        if request.POST.get("train_ml"):
            labeled = TeacherAppraisalSubmission.objects.exclude(
                final_band=""
            ).exclude(auto_metrics={})

            template = submission.kpi_template

            if not template and submission.cycle:
                template = KpiTemplate.objects.filter(
                    cycle=submission.cycle
                ).order_by("-id").first()

            if not template:
                messages.error(
                    request,
                    "❌ KPI Template nahi mila. Pehle KPI Builder mein template banao."
                )
                return redirect("admin_appraisal_detail", pk=pk)

            try:
                train_random_forest(labeled, template)
                messages.success(request, "✅ RandomForest trained successfully.")
            except RuntimeError as e:
                messages.error(request, f"❌ Training failed: {str(e)}")
            except Exception as e:
                messages.error(request, f"❌ Unexpected error: {str(e)}")

            return redirect("admin_appraisal_detail", pk=pk)

        if request.POST.get("regenerate"):
            generate_score(submission)
            messages.success(request, "Score regenerated.")
            return redirect("admin_appraisal_detail", pk=pk)

    return render(request, "admin_panel/appraisal_admin_detail.html", {
        "submission": submission,
        "pred": pred,
    })


# ==================== ACADEMIC CALENDAR ====================
import json
from datetime import datetime
from django.utils.dateparse import parse_datetime
from django.utils.timezone import localtime
from .models import AcademicCalendarEvent


def _type_to_color(event_type: str) -> str:
    return {
        "gazetted": "#34a853",
        "college_assess": "#1a73e8",
        "college_event": "#7c6f31",
        "mat_camb_assess": "#8ab4f8",
        "pre_primary": "#d56a1f",
        "speaker_train": "#7b1fa2",
        "eca_cca": "#fbbc05",
        "ptm": "#ea4335",
        "other": "#5f6368",
    }.get(event_type or "other", "#1a73e8")


@login_required
@permission_required("admin_panel.view_academiccalendarevent", raise_exception=True)
def academic_calendar_page(request):
    return render(request, "admin_panel/academic_calendar.html")


@login_required
@permission_required("admin_panel.view_academiccalendarevent", raise_exception=True)
def academic_calendar_events(request):
    events = AcademicCalendarEvent.objects.all().order_by("start")
    data = []
    for e in events:
        color = e.color or _type_to_color(e.event_type)
        data.append({
            "id": e.id,
            "title": e.title,
            "start": e.start.isoformat(),
            "end": e.end.isoformat() if e.end else None,
            "allDay": e.all_day,
            "extendedProps": {
                "event_type": e.event_type,
                "description": e.description,
                "streams": e.streams,
                "responsibility": e.responsibility,
                "color": color,
            },
            "backgroundColor": color,
            "borderColor": color,
        })
    return JsonResponse(data, safe=False)


@login_required
@permission_required("admin_panel.add_academiccalendarevent", raise_exception=True)
@require_http_methods(["POST"])
def academic_calendar_create(request):
    try:
        payload = json.loads(request.body.decode("utf-8"))
        title = (payload.get("title") or "").strip()
        start = parse_datetime(payload.get("start") or "")
        end = parse_datetime(payload.get("end") or "") if payload.get("end") else None

        if not title or not start:
            return HttpResponseBadRequest("title/start required")

        event_type = payload.get("event_type") or "other"
        e = AcademicCalendarEvent.objects.create(
            title=title,
            start=start,
            end=end,
            all_day=bool(payload.get("allDay", False)),
            event_type=event_type,
            description=payload.get("description") or "",
            streams=payload.get("streams") or "",
            responsibility=payload.get("responsibility") or "",
            color=payload.get("color") or _type_to_color(event_type),
        )
        return JsonResponse({"ok": True, "id": e.id})
    except Exception as ex:
        return HttpResponseBadRequest(str(ex))


@login_required
@permission_required("admin_panel.change_academiccalendarevent", raise_exception=True)
@require_http_methods(["POST", "PATCH"])
def academic_calendar_update(request, event_id):
    try:
        e = AcademicCalendarEvent.objects.get(id=event_id)
        payload = json.loads(request.body.decode("utf-8"))

        if "title" in payload:
            e.title = (payload.get("title") or "").strip()
        if "start" in payload:
            dt = parse_datetime(payload.get("start") or "")
            if dt:
                e.start = dt
        if "end" in payload:
            e.end = parse_datetime(payload.get("end") or "") if payload.get("end") else None
        if "allDay" in payload:
            e.all_day = bool(payload.get("allDay"))
        if "event_type" in payload:
            e.event_type = payload.get("event_type") or "other"
        if "description" in payload:
            e.description = payload.get("description") or ""
        if "streams" in payload:
            e.streams = payload.get("streams") or ""
        if "responsibility" in payload:
            e.responsibility = payload.get("responsibility") or ""
        if "color" in payload:
            e.color = payload.get("color") or ""
        else:
            if not e.color:
                e.color = _type_to_color(e.event_type)

        if not e.title or not e.start:
            return HttpResponseBadRequest("title/start required")

        e.save()
        return JsonResponse({"ok": True})
    except AcademicCalendarEvent.DoesNotExist:
        return HttpResponseBadRequest("event not found")
    except Exception as ex:
        return HttpResponseBadRequest(str(ex))


@login_required
@permission_required("admin_panel.delete_academiccalendarevent", raise_exception=True)
@require_http_methods(["POST", "DELETE"])
def academic_calendar_delete(request, event_id):
    AcademicCalendarEvent.objects.filter(id=event_id).delete()
    return JsonResponse({"ok": True})


@login_required
@permission_required("admin_panel.view_academiccalendarevent", raise_exception=True)
def academic_calendar_export_pdf(request):
    year_str = request.GET.get("year")
    try:
        year = int(year_str) if year_str else datetime.now().year
    except Exception:
        year = datetime.now().year

    qs = AcademicCalendarEvent.objects.filter(start__year=year).order_by("start")

    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.lib import colors

    response = HttpResponse(content_type="application/pdf")
    response["Content-Disposition"] = f'inline; filename="ACADEMIC_CALENDAR_{year}.pdf"'

    doc = SimpleDocTemplate(
        response,
        pagesize=landscape(A4),
        leftMargin=24, rightMargin=24, topMargin=18, bottomMargin=18
    )

    styles = getSampleStyleSheet()
    title_style = styles["Title"]
    normal = styles["BodyText"]

    story = []
    story.append(Paragraph(f"ACADEMIC CALENDAR {year}", title_style))
    story.append(Spacer(1, 10))

    legend_items = [
        ("Gazetted Holidays", _type_to_color("gazetted")),
        ("College Assess/Admin", _type_to_color("college_assess")),
        ("College Events", _type_to_color("college_event")),
        ("Mat/Camb Assess", _type_to_color("mat_camb_assess")),
        ("Pre-Primary", _type_to_color("pre_primary")),
        ("Speaker/Ses/Train", _type_to_color("speaker_train")),
        ("ECA/CCA", _type_to_color("eca_cca")),
        ("PTM", _type_to_color("ptm")),
    ]

    legend_data = []
    row = []
    for label, hexcol in legend_items:
        swatch = Table([[" "]], colWidths=10, rowHeights=10)
        swatch.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor(hexcol)),
            ("BOX", (0, 0), (-1, -1), 0.5, colors.black),
        ]))
        cell = Table([[swatch, Paragraph(label, normal)]], colWidths=[14, 120])
        cell.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "MIDDLE")]))
        row.append(cell)
        if len(row) == 3:
            legend_data.append(row)
            row = []
    if row:
        while len(row) < 3:
            row.append("")
        legend_data.append(row)

    legend_table = Table(legend_data, colWidths=[180, 180, 180])
    legend_table.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
    ]))
    story.append(legend_table)
    story.append(Spacer(1, 10))

    header = ["S.No", "Date", "Day", "Event", "Streams", "Responsibility"]
    table_data = [header]

    for idx, e in enumerate(qs, start=1):
        dt = localtime(e.start)
        table_data.append([
            str(idx),
            dt.strftime("%d-%m-%y"),
            dt.strftime("%A"),
            Paragraph(e.title or "", normal),
            Paragraph(e.streams or "", normal),
            Paragraph(e.responsibility or "", normal),
        ])

    if len(table_data) == 1:
        table_data.append(["", "", "", Paragraph("No events found for this year.", normal), "", ""])

    col_widths = [40, 70, 90, 280, 220, 220]
    t = Table(table_data, colWidths=col_widths, repeatRows=1)

    style_cmds = [
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#eeeeee")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.black),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, 0), 10),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#cfcfcf")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("FONTSIZE", (0, 1), (-1, -1), 9),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]

    for row_i, e in enumerate(qs, start=1):
        col = colors.HexColor(e.color or _type_to_color(e.event_type))
        style_cmds.append(("BACKGROUND", (0, row_i), (-1, row_i), col))
        style_cmds.append(("TEXTCOLOR", (0, row_i), (-1, row_i), colors.white))

    t.setStyle(TableStyle(style_cmds))
    story.append(t)

    doc.build(story)
    return response


# ==================== BULK UPLOAD ====================
import openpyxl
import uuid
from datetime import datetime
from django.contrib.auth.decorators import permission_required
from django.contrib.auth.models import Group, User
from django.contrib import messages
from django.shortcuts import redirect, render
from django.db import transaction
from django.utils.text import slugify


DEFAULT_TEACHER_PASSWORD = "Teacher@123"


def _parse_date(val):
    if val is None:
        return None
    if hasattr(val, 'date') and callable(val.date):
        return val.date()
    if hasattr(val, 'year'):
        return val
    val = str(val).strip()
    if not val or val.lower() in ('none', 'nan', ''):
        return None
    for fmt in ('%d-%b-%Y', '%d/%m/%Y', '%Y-%m-%d', '%d-%m-%Y', '%d %b %Y'):
        try:
            return datetime.strptime(val, fmt).date()
        except ValueError:
            continue
    return None


def _parse_experience(val):
    if val is None:
        return 0
    val = str(val).strip().lower()
    val = val.replace('years', '').replace('year', '').strip()
    try:
        return int(float(val))
    except (ValueError, TypeError):
        return 0


def _str(val):
    if val is None:
        return ''
    s = str(val).strip()
    return '' if s.lower() in ('none', 'nan') else s


@permission_required('admin_panel.add_admission', raise_exception=True)
def bulk_upload_students(request):
    if request.method == 'POST' and request.FILES.get('excel_file'):
        excel_file = request.FILES['excel_file']

        try:
            wb = openpyxl.load_workbook(excel_file, read_only=True, data_only=True)
        except Exception as e:
            messages.error(request, f"❌ Excel file padhne mein masla: {e}")
            return redirect('bulk_upload_students')

        ws = wb.active
        active_year = AcademicYear.objects.filter(is_active=True).first()

        if not active_year:
            messages.error(request, "❌ Koi active academic year nahi mila. Pehle academic year set karein.")
            return redirect('bulk_upload_students')

        success_count = 0
        skip_count    = 0
        error_rows    = []

        for row_num, row in enumerate(ws.iter_rows(min_row=2, values_only=True), start=2):

            if not any(row):
                continue

            try:
                student_id     = _str(row[1])
                campus         = _str(row[2])
                branch         = _str(row[3])
                name           = _str(row[4])
                dob            = _parse_date(row[5])
                gender         = _str(row[6]) or 'Male'
                email          = _str(row[7])
                contact        = _str(row[8])
                address        = _str(row[9])
                admission_date = _parse_date(row[10])
                father_name    = _str(row[11])
                father_email   = _str(row[12])
                class_name     = _str(row[14])
                father_occ     = _str(row[15])
                mother_name    = _str(row[16])
                father_contact = _str(row[17])
                father_cnic    = _str(row[18])
                nationality    = _str(row[19])
                raw_status     = _str(row[20]).lower() or 'pending'

                if not name:
                    skip_count += 1
                    continue

                status_map = {
                    'active':   'approved',
                    'inactive': 'rejected',
                    'pending':  'pending',
                    'approved': 'approved',
                    'rejected': 'rejected',
                }
                admission_status = status_map.get(raw_status, 'pending')

                if student_id and Admission.objects.filter(student_id=student_id).exists():
                    skip_count += 1
                    error_rows.append(
                        f"Row {row_num}: Student ID '{student_id}' pehle se exist karta hai — skip kiya."
                    )
                    continue

                Admission.objects.create(
                    student_id       = student_id or None,
                    campus           = campus,
                    branch           = branch,
                    name             = name,
                    dob              = dob,
                    gender           = gender,
                    email            = email,
                    contact          = contact,
                    address          = address,
                    admission_date   = admission_date,
                    father_name      = father_name,
                    father_email     = father_email,
                    mother_name      = mother_name,
                    father_contact   = father_contact,
                    father_cnic      = father_cnic,
                    academic_year    = active_year,
                    admission_status = admission_status,
                )
                success_count += 1

            except Exception as e:
                error_rows.append(f"Row {row_num}: {str(e)}")

        if success_count:
            messages.success(request, f"✅ {success_count} students successfully upload ho gaye.")
        if skip_count:
            messages.warning(request, f"⚠️ {skip_count} rows skip ki gayi (duplicate ya empty).")
        for err in error_rows:
            messages.error(request, err)

        return redirect('admission_list')

    return render(request, 'admin_panel/bulk_upload_students.html')


@permission_required('teacher_dashboard.add_teacher', raise_exception=True)
def bulk_upload_teachers(request):
    if request.method == 'POST' and request.FILES.get('excel_file'):
        excel_file = request.FILES['excel_file']

        try:
            wb = openpyxl.load_workbook(excel_file, read_only=True, data_only=True)
        except Exception as e:
            messages.error(request, f"❌ Excel file padhne mein masla: {e}")
            return redirect('bulk_upload_teachers')

        ws = wb.active
        teacher_group, _ = Group.objects.get_or_create(name="Teacher")

        success_count = 0
        skip_count    = 0
        error_rows    = []

        for row_num, row in enumerate(ws.iter_rows(min_row=2, values_only=True), start=2):

            if not any(row):
                continue

            try:
                teacher_id    = _str(row[0])
                name          = _str(row[1])
                email         = _str(row[2])
                phone         = _str(row[3])
                gender        = _str(row[4]) or 'Male'
                dob           = _parse_date(row[5])
                qualification = _str(row[6]) or 'BS'
                experience    = _parse_experience(row[7])
                address       = _str(row[8])
                faculty_group = _str(row[9])
                department    = _str(row[10])
                subject_name  = _str(row[11])
                joining_date  = _parse_date(row[13])
                raw_status    = _str(row[14]).lower() or 'active'

                if not name or not email:
                    skip_count += 1
                    continue

                if User.objects.filter(email__iexact=email).exists():
                    skip_count += 1
                    error_rows.append(
                        f"Row {row_num}: Email '{email}' pehle se exist karta hai — skip kiya."
                    )
                    continue

                status_map = {
                    'active':   'active',
                    'inactive': 'inactive',
                    'on leave': 'inactive',
                }
                teacher_status = status_map.get(raw_status, 'active')

                with transaction.atomic():
                    base     = slugify(name) or "teacher"
                    username = f"{base}_{str(uuid.uuid4())[:5]}"

                    user = User.objects.create_user(
                        username   = username,
                        email      = email,
                        password   = DEFAULT_TEACHER_PASSWORD,
                        first_name = name,
                    )
                    user.groups.set([teacher_group])

                    teacher = Teacher.objects.create(
                        user          = user,
                        name          = name,
                        email         = email,
                        phone         = phone,
                        gender        = gender,
                        qualification = qualification,
                        experience    = experience,
                        Address       = address,
                        department    = department,
                        faculty_group = [faculty_group] if faculty_group else [],
                        status        = teacher_status,
                    )

                    if subject_name:
                        subject_obj = Subject.objects.filter(name__iexact=subject_name).first()
                        if subject_obj:
                            teacher.subjects.add(subject_obj)

                success_count += 1

            except Exception as e:
                error_rows.append(f"Row {row_num}: {str(e)}")

        if success_count:
            messages.success(request, f"✅ {success_count} teachers successfully upload ho gaye.")
        if skip_count:
            messages.warning(request, f"⚠️ {skip_count} rows skip ki gayi (duplicate ya empty).")
        for err in error_rows:
            messages.error(request, err)

        return redirect('teacher_list')

    return render(request, 'admin_panel/bulk_upload_teachers.html')


# ==================== BULK DELETE ====================
from django.views.decorators.http import require_POST


@permission_required('admin_panel.delete_admission', raise_exception=True)
@require_POST
def bulk_delete_students(request):
    delete_all = request.POST.get('delete_all') == 'on'
    if delete_all:
        deleted_count, _ = Admission.objects.all().delete()
        messages.success(request, f"✅ Saare {deleted_count} students delete ho gaye.")
    else:
        student_ids = request.POST.getlist('student_ids')
        if not student_ids:
            messages.warning(request, "⚠️ Koi student select nahi kiya gaya.")
            return redirect('admission_list')
        deleted_count, _ = Admission.objects.filter(id__in=student_ids).delete()
        messages.success(request, f"✅ {deleted_count} students successfully delete ho gaye.")
    return redirect('admission_list')


@permission_required('teacher_dashboard.delete_teacher', raise_exception=True)
@require_POST
def bulk_delete_teachers(request):
    delete_all = request.POST.get('delete_all') == 'on'
    if delete_all:
        user_ids = Teacher.objects.values_list('user_id', flat=True)
        deleted_count, _ = Teacher.objects.all().delete()
        User.objects.filter(id__in=user_ids).delete()
        messages.success(request, f"✅ Saare {deleted_count} teachers delete ho gaye.")
    else:
        teacher_ids = request.POST.getlist('teacher_ids')
        if not teacher_ids:
            messages.warning(request, "⚠️ Koi teacher select nahi kiya gaya.")
            return redirect('teacher_list')
        user_ids = Teacher.objects.filter(id__in=teacher_ids).values_list('user_id', flat=True)
        deleted_count, _ = Teacher.objects.filter(id__in=teacher_ids).delete()
        User.objects.filter(id__in=user_ids).delete()
        messages.success(request, f"✅ {deleted_count} teachers successfully delete ho gaye.")
    return redirect('teacher_list')





# --- LOGIN/LOGOUT ---
@csrf_protect
def login_view(request):
    if request.user.is_authenticated:
        # User pehle se authenticated hai toh role ke mutabiq redirect karein
        if request.user.role == 'admin': return redirect('admin_dashboard')
        elif request.user.role == 'student': return redirect('student-dashboard')
        elif request.user.role == 'teacher': return redirect('teacher-dashboard')
        elif request.user.role == 'parent': return redirect('parent-dashboard')
    
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        role = request.POST.get('role') # UI dropdown se milne wala role
        
        user = authenticate(request, username=username, password=password)
        
        if user is not None:
            # Simple validation: user ka role check karein
            if user.role.lower() == role:
                login(request, user)
                if role == 'admin': return redirect('admin_dashboard')
                elif role == 'student': return redirect('student-dashboard')
                elif role == 'teacher': return redirect('teacher-dashboard')
                elif role == 'parent': return redirect('parent-dashboard')
                else: return redirect('admin_dashboard') # Default fallback
            else:
                messages.error(request, f"Invalid login for {role.upper()} portal.")
        else:
            messages.error(request, "Invalid username ya password.")
    return render(request, 'login.html')

def logout_view(request):
    logout(request)
    return redirect('login')

# --- ADMIN DASHBOARD ---
@login_required(login_url='login')
def admin_dashboard_view(request):
    fee_settings = FeeGenerationSettings.objects.first() or FeeGenerationSettings.objects.create()
    salary_settings = SalaryAutomationSettings.objects.first() or SalaryAutomationSettings.objects.create()

    if request.method == 'POST':
        action = request.POST.get('action')

        try:
            if action == 'save_fee_settings':
                fee_settings.auto_enabled = request.POST.get('fee_auto_enabled') == 'on'
                fee_settings.generation_day = int(request.POST.get('fee_generation_day') or 1)
                fee_settings.generation_time = datetime.strptime(
                    request.POST.get('fee_generation_time') or '09:00', '%H:%M'
                ).time()
                fee_settings.send_notifications = request.POST.get('fee_send_notifications') == 'on'
                fee_settings.save()
                messages.success(request, 'Fee automation settings saved successfully.')

            elif action == 'save_salary_settings':
                salary_settings.auto_enabled = request.POST.get('salary_auto_enabled') == 'on'
                salary_settings.generation_day = int(request.POST.get('salary_generation_day') or 30)
                salary_settings.generation_time = datetime.strptime(
                    request.POST.get('salary_generation_time') or '18:00', '%H:%M'
                ).time()
                salary_settings.send_notifications = request.POST.get('salary_send_notifications') == 'on'
                salary_settings.save()
                messages.success(request, 'Salary automation settings saved successfully.')

            elif action == 'generate_fees':
                today = date.today()
                month_name = request.POST.get('fee_month') or today.strftime('%B')
                year = int(request.POST.get('fee_year') or today.year)
                job = AutomationJob.objects.create(job_type='MANUAL_GENERATION', status='PENDING')
                count = FeeGenerationService.generate_monthly_fees(month_name, year, job_id=job.id)
                messages.success(request, f'Fee generation completed. {count} voucher(s) generated. Job ID: {job.id}.')

            elif action == 'generate_salaries':
                today = date.today()
                month_name = request.POST.get('salary_month') or today.strftime('%B')
                year = int(request.POST.get('salary_year') or today.year)
                SalaryAutomationService.generate_salaries(month_name, year)
                messages.success(request, 'Salary generation process completed.')

            elif action == 'send_notifications':
                pending_count = NotificationQueue.objects.filter(status='PENDING').count()
                NotificationDispatcherService.send_pending_notifications()
                messages.success(request, f'Notification dispatcher processed {pending_count} pending notification(s).')

            elif action == 'retry_failed_fees':
                today = date.today()
                month_name = request.POST.get('retry_fee_month') or today.strftime('%B')
                year = int(request.POST.get('retry_fee_year') or today.year)
                failed_jobs = AutomationJob.objects.filter(details__status='FAILED').distinct()
                retry_count = 0
                for job in failed_jobs:
                    FeeGenerationService.retry_failed_records(job.id, month_name, year)
                    retry_count += 1
                messages.success(request, f'Retry initiated for {retry_count} fee automation job(s).')

            elif action == 'retry_failed_salaries':
                SalaryAutomationService.generate_salaries()
                messages.success(request, 'Salary retry process completed.')

        except Exception as e:
            messages.error(request, f'Action failed: {str(e)}')

        return redirect('admin_dashboard')

    # Ab hum models.py mein banaye gaye helper function se stats utha rahe hain
    context = get_dashboard_stats()
    context.update({
        'fee_settings': fee_settings,
        'salary_settings': salary_settings,
        'fee_logs': FeeGenerationLog.objects.all().order_by('-started_at')[:5],
        'automation_jobs': AutomationJob.objects.all().order_by('-started_at')[:8],
        'automation_details': AutomationJobDetail.objects.filter(status='FAILED').order_by('-id')[:8],
        'salary_jobs': SalaryAutomationJob.objects.all().order_by('-started_at')[:8],
        'salary_details': SalaryAutomationJobDetail.objects.filter(status='FAILED').order_by('-id')[:8],
        'notifications': NotificationQueue.objects.all().order_by('-created_at')[:8],
        'pending_notifications': NotificationQueue.objects.filter(status='PENDING').count(),
        'failed_notifications': NotificationQueue.objects.filter(status='FAILED').count(),
        'fee_vouchers_count': FeeVoucher.objects.count(),
        'salary_vouchers_count': SalaryVoucher.objects.count(),
        'months': [
            'January', 'February', 'March', 'April', 'May', 'June',
            'July', 'August', 'September', 'October', 'November', 'December'
        ],
        'current_month': date.today().strftime('%B'),
        'current_year': date.today().year,
    })
    return render(request, 'dashboard.html', context)

# API for Admin Dashboard (Dynamic Front-end ke liye)
class AdminDashboardAPI(APIView):
    def get(self, request):
        data = get_dashboard_stats()
        # API response format
        return Response({
            "stats": {
                "total_students": data['total_students'],
                "monthly_revenue": data['monthly_revenue'],
                "total_expenses": data['total_expenses'],
                "high_risk_students": data['high_risk_students'],
                "total_teachers": data['total_teachers'],
                "total_staff": data['total_staff']
            },
            "recent_transactions": list(data['recent_transactions'].values('title', 'amount', 'type', 'date'))
        })

# --- STUDENT & PARENT VIEWS ---
def student_registration_view(request):
    if request.method == 'POST':
        form = StudentRegistrationForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('admin_dashboard')
    else:
        form = StudentRegistrationForm()
    return render(request, 'register.html', {'form': form})

def generate_fees_view(request):
    # Current month aur year nikal kar service call karna
    today = date.today()
    month_name = today.strftime("%B")
    year = today.year
    
    count = FeeGenerationService.generate_monthly_fees(month_name, year)
    messages.success(request, f"{count} vouchers generated successfully for {month_name}-{year}!")
    return redirect('/admin/edupilot_core/feevoucher/')

@login_required
def student_dashboard(request):
    try:
        student = Student.objects.get(admission_number=request.user.username)
        vouchers = FeeVoucher.objects.filter(student=student).order_by('-id')
        balance = StudentBalance.objects.get(student=student)
        
        # ✅ GET NOTIFICATIONS
        notifications = NotificationQueue.objects.filter(student=student).order_by('-created_at')[:10]
        
        context = {
            'student': student,
            'vouchers': vouchers,
            'balance': balance,
            'notifications': notifications  # ← ADD YE
        }
    except:
        context = {
            'student': None,
            'vouchers': [],
            'balance': None,
            'notifications': [],
            'error': 'Student data not found'
        }
    return render(request, 'student_profile/dashboard.html', context)

@login_required
def teacher_dashboard(request):
    try:
        # Teacher model mein 'user' field nahi hai
        # Username ko teacher_id se match karo
        teacher = Teacher.objects.get(teacher_id=request.user.username)
        
        # Get salary vouchers
        salary_vouchers = SalaryVoucher.objects.filter(teacher=teacher).order_by('-id')
        
        # Get notifications (empty - teacher notifications not in system)
        notifications = []
        
        context = {
            'teacher': teacher,
            'salary_vouchers': salary_vouchers,
            'notifications': notifications
        }
    except Teacher.DoesNotExist:
        context = {
            'teacher': None,
            'salary_vouchers': [],
            'notifications': [],
            'error': 'Teacher record not found'
        }
    except Exception as e:
        context = {
            'teacher': None,
            'salary_vouchers': [],
            'notifications': [],
            'error': f'Error: {str(e)}'
        }
    
    return render(request, 'teacher_dashboard/teacher_dashboard.html', context)

@login_required
def parent_dashboard(request):
    context = {'children': [], 'vouchers': []}
    return render(request, 'parent/dashboard.html', context)

def automation_logs(request):
    logs = AutomationJobDetail.objects.all().order_by('-id')
    return render(request, 'automation/logs.html', {'logs': logs})

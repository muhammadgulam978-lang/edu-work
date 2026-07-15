from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login
from django.contrib import messages
from django.contrib.auth.models import User
from django.views.decorators.cache import never_cache


ROLE_LOGIN_CONFIG = {
    "admin": {
        "group": "Admin",
        "title": "Admin Login",
        "portal": "Admin Portal",
        "welcome": "Welcome Admin! Please log in to continue",
        "subtitle": "Manage EduPilot operations, people, and automation.",
        "icon": "fa-user-shield",
        "dashboard": "admin_panel_dashboard",
        "profile_check": None,
    },
    "teacher": {
        "group": "Teacher",
        "title": "Teacher Login",
        "portal": "Teacher Portal",
        "welcome": "Welcome Teacher! Please log in to continue",
        "subtitle": "Open your timetable, classes, LMS, and exam tools.",
        "icon": "fa-chalkboard-user",
        "dashboard": "teacher_dashboard",
        "profile_check": "teacher",
    },
    "student": {
        "group": "Student",
        "title": "Student Login",
        "portal": "Student Portal",
        "welcome": "Welcome Student! Please log in to continue",
        "subtitle": "Continue learning, practice, assignments, and AI Tutor.",
        "icon": "fa-user-graduate",
        "dashboard": "student_dashboard",
        "profile_check": "student",
    },
    "parent": {
        "group": "Parent",
        "title": "Parent Login",
        "portal": "Parent Portal",
        "welcome": "Welcome Parent! Please log in to continue",
        "subtitle": "Track attendance, results, assignments, and progress.",
        "icon": "fa-users",
        "dashboard": "parent_dashboard",
        "profile_check": "parent",
    },
}


def _user_has_role(user, role):
    config = ROLE_LOGIN_CONFIG[role]
    if role == "admin" and user.is_superuser:
        return True
    return user.groups.filter(name__iexact=config["group"]).exists()


def _linked_profile_exists(user, role):
    profile_check = ROLE_LOGIN_CONFIG[role]["profile_check"]
    if not profile_check:
        return True

    if profile_check == "teacher":
        from teacher_dashboard.models import Teacher
        return Teacher.objects.filter(user=user).exists()
    if profile_check == "student":
        from student_profile.models import Student
        return Student.objects.filter(user=user).exists()
    if profile_check == "parent":
        from parent_dashboard.models import Parent
        return Parent.objects.filter(user=user).exists()
    return True


@never_cache
def role_select_view(request):
    if request.user.is_authenticated:
        for role in ("admin", "teacher", "student", "parent"):
            if _user_has_role(request.user, role) and _linked_profile_exists(request.user, role):
                return redirect(ROLE_LOGIN_CONFIG[role]["dashboard"])
    return render(request, "registration/role_select.html", {
        "roles": ROLE_LOGIN_CONFIG,
    })


@never_cache
def role_login_view(request, role):
    if role not in ROLE_LOGIN_CONFIG:
        return redirect("login")

    config = ROLE_LOGIN_CONFIG[role]

    if request.method == "POST":
        username = request.POST.get("username", "").strip()
        password = request.POST.get("password", "")
        remember_me = request.POST.get("remember_me") == "on"

        user = authenticate(request, username=username, password=password)

        if user is None:
            messages.error(request, "Invalid login ID or password.")
        elif not user.is_active:
            messages.error(request, "Your account is inactive. Contact admin.")
        elif not _user_has_role(user, role):
            messages.error(request, "This account is not allowed on this login page.")
        elif not _linked_profile_exists(user, role):
            messages.error(request, "This account is missing its linked portal profile. Contact admin.")
        else:
            login(request, user)
            if not remember_me:
                request.session.set_expiry(0)
            return redirect(config["dashboard"])

    return render(request, "registration/role_login.html", {
        "role": role,
        "config": config,
    })


def admin_login(request):
    return role_login_view(request, "admin")


def teacher_login(request):
    return role_login_view(request, "teacher")


def student_login(request):
    return role_login_view(request, "student")


def parent_login(request):
    return role_login_view(request, "parent")


def login_view(request):
    return redirect("login")


def redirect_user_dashboard(request, user):
    if user.groups.filter(name__iexact='Admin').exists():
        return redirect('admin_panel_dashboard')  # apna correct url name
    elif user.groups.filter(name__iexact='Parent').exists():
        return redirect('parent_dashboard_home')
    elif user.groups.filter(name__iexact='Teacher').exists():
        return redirect('teacher_dashboard')
    elif user.groups.filter(name__iexact='Student').exists():
        return redirect('student_dashboard')
        # return redirect('student_profile_home')
    else:
        messages.error(request, "No role assigned.")
        return redirect('login')


# ******************************** Working on chnage passowrd ************************************************
from django.contrib.auth.decorators import login_required
from django.contrib.auth import update_session_auth_hash

@login_required
def change_password(request):
    if request.method == 'POST':
        current_password = request.POST.get('current_password')
        new_password = request.POST.get('new_password')
        confirm_password = request.POST.get('confirm_password')

        user = request.user

        if not user.check_password(current_password):
            messages.error(request, 'Current password is incorrect.')
            return redirect('change_password')

        if new_password != confirm_password:
            messages.error(request, 'New passwords do not match.')
            return redirect('change_password')

        user.set_password(new_password)
        user.save()
        update_session_auth_hash(request, user)  # Login session maintained
        messages.success(request, 'Password updated successfully.')
        return redirect('login')  # Ya kisi aur page pe redirect karein

    return render(request, 'change_password.html')



from django.contrib.auth import logout
from django.shortcuts import redirect

def custom_logout(request):
    logout(request)
    return redirect('login')

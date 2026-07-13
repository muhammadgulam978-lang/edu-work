from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login
from django.contrib import messages
from django.contrib.auth.models import User

def login_view(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')

        # Pehle check karo kya username/email kisi user ke sath match karta hai
        user_exists = User.objects.filter(username=username).exists() or User.objects.filter(email=username).exists()

        if not user_exists:
            messages.error(request, 'Username or email is incorrect')
            return render(request, 'registration/login.html')

        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            return redirect_user_dashboard(request, user)
        else:
            messages.error(request, 'Password is incorrect')

    return render(request, 'registration/login.html')


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

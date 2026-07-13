from teacher_dashboard.models import Teacher

def get_selected_or_logged_teacher(request):
    """
    Returns selected teacher if admin chose one,
    otherwise the logged-in teacher.
    """
    teacher_id = request.GET.get('teacher_id') or request.POST.get('teacher_id')

    # ✅ agar admin hai aur kisi teacher ko select kiya hai
    if request.user.is_staff and teacher_id:
        try:
            return Teacher.objects.get(id=teacher_id)
        except Teacher.DoesNotExist:
            return None

    # ✅ agar normal teacher login hai
    try:
        return Teacher.objects.get(user=request.user)
    except Teacher.DoesNotExist:
        return None

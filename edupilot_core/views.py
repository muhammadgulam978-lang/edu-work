from django.db.models import Sum
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
from .services import FeeGenerationService, SalaryAutomationService, NotificationDispatcherService

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

# @login_required
# def teacher_dashboard(request):
#     try:
#         # Teacher model mein 'user' field nahi hai
#         # Username ko teacher_id se match karo
#         teacher = Teacher.objects.get(teacher_id=request.user.username)
        
#         # Get salary vouchers
#         salary_vouchers = SalaryVoucher.objects.filter(teacher=teacher).order_by('-id')
        
#         # Get notifications (empty - teacher notifications not in system)
#         notifications = []
        
#         context = {
#             'teacher': teacher,
#             'salary_vouchers': salary_vouchers,
#             'notifications': notifications
#         }
#     except Teacher.DoesNotExist:
#         context = {
#             'teacher': None,
#             'salary_vouchers': [],
#             'notifications': [],
#             'error': 'Teacher record not found'
#         }
#     except Exception as e:
#         context = {
#             'teacher': None,
#             'salary_vouchers': [],
#             'notifications': [],
#             'error': f'Error: {str(e)}'
#         }
    
#     return render(request, 'teacher_dashboard/teacher_dashboard.html', context)

@login_required
def teacher_dashboard(request):
    # Nursery se 5th tak k class keywords — flexible matching
    PRIMARY_CLASSES = [
        'nursery', 'kg', 'kindergarten', 'prep',
        'class 1', 'class-1', 'grade 1', 'grade-1', '1',
        'class 2', 'class-2', 'grade 2', 'grade-2', '2',
        'class 3', 'class-3', 'grade 3', 'grade-3', '3',
        'class 4', 'class-4', 'grade 4', 'grade-4', '4',
        'class 5', 'class-5', 'grade 5', 'grade-5', '5',
    ]

    try:
        # Teacher model mein 'user' field nahi hai
        # Username ko teacher_id se match karo
        teacher = Teacher.objects.get(teacher_id=request.user.username)

        # Get salary vouchers
        salary_vouchers = SalaryVoucher.objects.filter(teacher=teacher).order_by('-id')

        # Teacher ki apni notifications
        notifications = NotificationQueue.objects.filter(
            teacher=teacher
        ).order_by('-created_at')[:10]

        # Nursery se 5th tak ke active students — flexible filter
        all_students = Student.objects.filter(is_active=True)
        primary_students = [
            s for s in all_students
            if s.current_class and s.current_class.strip().lower() in PRIMARY_CLASSES
        ]

        # Primary students ke fee vouchers
        student_vouchers = []
        if primary_students:
            student_ids = [s.id for s in primary_students]
            student_vouchers = FeeVoucher.objects.filter(
                student__id__in=student_ids
            ).select_related('student').order_by('-id')

        # Primary students ki notifications
        student_notifications = []
        if primary_students:
            student_ids = [s.id for s in primary_students]
            student_notifications = NotificationQueue.objects.filter(
                student__id__in=student_ids
            ).select_related('student').order_by('-created_at')[:20]

        context = {
            'teacher': teacher,
            'salary_vouchers': salary_vouchers,
            'notifications': notifications,
            'primary_students': primary_students,
            'student_vouchers': student_vouchers,
            'student_notifications': student_notifications,
        }

    except Teacher.DoesNotExist:
        context = {
            'teacher': None,
            'salary_vouchers': [],
            'notifications': [],
            'primary_students': [],
            'student_vouchers': [],
            'student_notifications': [],
            'error': 'Teacher record not found'
        }
    except Exception as e:
        context = {
            'teacher': None,
            'salary_vouchers': [],
            'notifications': [],
            'primary_students': [],
            'student_vouchers': [],
            'student_notifications': [],
            'error': f'Error: {str(e)}'
        }

    return render(request, 'teacher_dashboard/teacher_dashboard.html', context)

@login_required
def parent_dashboard(request):
    context = {'children': [], 'vouchers': []}
    return render(request, 'parent/dashboard.html', context)

def automation_logs(request):
    fee_jobs = AutomationJob.objects.all().order_by('-started_at')
    salary_jobs = SalaryAutomationJob.objects.all().order_by('-started_at')

    combined_logs = []
    for job in fee_jobs:
        combined_logs.append({
            'job_type': job.job_type or 'FEE_GENERATION',
            'started_at': job.started_at,
            'completed_at': job.completed_at,
            'processed': job.processed_count,
            'success': job.success_count,
            'failed': job.failed_count,
            'status': job.status,
        })
    for job in salary_jobs:
        combined_logs.append({
            'job_type': 'SALARY_GENERATION',
            'started_at': job.started_at,
            'completed_at': job.completed_at,
            'processed': job.success_count + job.failed_count,
            'success': job.success_count,
            'failed': job.failed_count,
            'status': job.status,
        })

    combined_logs.sort(key=lambda x: x['started_at'] or timezone.now(), reverse=True)

    total_jobs = len(combined_logs)
    completed = len([j for j in combined_logs if j['status'] == 'COMPLETED'])
    failed = len([j for j in combined_logs if j['status'] == 'FAILED'])
    in_progress = len([j for j in combined_logs if j['status'] == 'RUNNING'])
    success_rate = round((completed / total_jobs * 100), 1) if total_jobs else 0

    context = {
        'logs': combined_logs,
        'total_jobs': total_jobs,
        'completed': completed,
        'failed': failed,
        'in_progress': in_progress,
        'success_rate': success_rate,
    }
    return render(request, 'automation/logs.html', context)
def automation_dashboard(request):
    total_students = Student.objects.filter(is_active=True).count()
    total_teachers = Teacher.objects.filter(is_active=True).count()

    last_fee_job = AutomationJob.objects.order_by('-started_at').first()
    last_salary_job = SalaryAutomationJob.objects.order_by('-started_at').first()
    last_notif = NotificationQueue.objects.order_by('-created_at').first()

    total_collected = FeeVoucher.objects.filter(status='PAID').aggregate(Sum('net_amount'))['net_amount__sum'] or 0
    total_pending = FeeVoucher.objects.exclude(status='PAID').aggregate(Sum('net_amount'))['net_amount__sum'] or 0
    total_all = total_collected + total_pending
    collection_rate = round((total_collected / total_all * 100), 1) if total_all else 0

    recent_jobs = []
    for job in AutomationJob.objects.order_by('-started_at')[:4]:
        recent_jobs.append({'type': job.job_type, 'started': job.started_at, 'status': job.status,
                             'processed': job.processed_count, 'success': job.success_count, 'failed': job.failed_count})
    for job in SalaryAutomationJob.objects.order_by('-started_at')[:2]:
        recent_jobs.append({'type': 'SALARY_GENERATION', 'started': job.started_at, 'status': job.status,
                             'processed': job.success_count + job.failed_count, 'success': job.success_count, 'failed': job.failed_count})
    recent_jobs.sort(key=lambda x: x['started'] or timezone.now(), reverse=True)
    recent_jobs = recent_jobs[:5]

    recent_notifications = [
        {'title': n.content, 'type': n.get_notification_type_display(), 'time': n.created_at}
        for n in NotificationQueue.objects.order_by('-created_at')[:5]
    ]

    context = {
        'total_students': total_students,
        'total_teachers': total_teachers,
        'total_parents': 0,
        'notifications_today': NotificationQueue.objects.filter(created_at__date=date.today()).count(),
        'fee_last_run': last_fee_job.started_at if last_fee_job else None,
        'fee_status': last_fee_job.status if last_fee_job else 'N/A',
        'salary_last_run': last_salary_job.started_at if last_salary_job else None,
        'salary_status': last_salary_job.status if last_salary_job else 'N/A',
        'notif_last_run': last_notif.created_at if last_notif else None,
        'notif_status': last_notif.status if last_notif else 'N/A',
        'total_collected': f"{total_collected:,.0f}",
        'total_pending': f"{total_pending:,.0f}",
        'collection_rate': collection_rate,
        'recent_jobs': recent_jobs,
        'recent_notifications': recent_notifications,
    }
    return render(request, 'automation/dashboard.html', context)


def fee_automation_view(request):
    fee_settings = FeeGenerationSettings.objects.first() or FeeGenerationSettings.objects.create()

    if request.method == 'POST':
        action = request.POST.get('action')
        try:
            if action == 'save_fee_settings':
                fee_settings.auto_enabled = request.POST.get('fee_auto_enabled') == 'on'
                fee_settings.generation_day = int(request.POST.get('fee_generation_day') or 1)
                fee_settings.generation_time = datetime.strptime(
                    request.POST.get('fee_generation_time') or '09:00', '%H:%M').time()
                fee_settings.send_notifications = request.POST.get('fee_send_notifications') == 'on'
                fee_settings.save()
                messages.success(request, 'Fee automation settings saved.')
            elif action == 'generate_fees':
                today = date.today()
                month_name = request.POST.get('fee_month') or today.strftime('%B')
                year = int(request.POST.get('fee_year') or today.year)
                job = AutomationJob.objects.create(job_type='MANUAL_GENERATION', status='PENDING')
                count = FeeGenerationService.generate_monthly_fees(month_name, year, job_id=job.id)
                messages.success(request, f'{count} fee voucher(s) generated.')
        except Exception as e:
            messages.error(request, f'Action failed: {str(e)}')
        return redirect('fee-automation')

    last_job = AutomationJob.objects.order_by('-started_at').first()
    total_fees = FeeVoucher.objects.aggregate(Sum('net_amount'))['net_amount__sum'] or 0
    collected = FeeVoucher.objects.filter(status='PAID').aggregate(Sum('net_amount'))['net_amount__sum'] or 0
    pending = total_fees - collected
    collection_rate = round((collected / total_fees * 100), 1) if total_fees else 0

    recent_runs = [
        {'date': log.started_at, 'processed': log.students_processed,
         'success': log.success_count, 'failed': log.failed_count, 'status': log.status}
        for log in FeeGenerationLog.objects.order_by('-started_at')[:8]
    ]

    context = {
        'fee_settings': fee_settings,
        'last_run': last_job.started_at if last_job else None,
        'processed': last_job.processed_count if last_job else 0,
        'success': last_job.success_count if last_job else 0,
        'failed': last_job.failed_count if last_job else 0,
        'total_fees': f"{total_fees:,.0f}", 'collected': f"{collected:,.0f}", 'pending': f"{pending:,.0f}",
        'collection_rate': collection_rate,
        'recent_runs': recent_runs,
        'months': ['January','February','March','April','May','June','July','August','September','October','November','December'],
        'current_month': date.today().strftime('%B'),
        'current_year': date.today().year,
    }
    return render(request, 'automation/fee.html', context)


def voucher_management_view(request):
    if request.method == 'POST' and request.POST.get('action') == 'generate_fees':
        today = date.today()
        job = AutomationJob.objects.create(job_type='MANUAL_GENERATION', status='PENDING')
        count = FeeGenerationService.generate_monthly_fees(today.strftime('%B'), today.year, job_id=job.id)
        messages.success(request, f'{count} voucher(s) generated.')
        return redirect('voucher-management')

    total_vouchers = FeeVoucher.objects.count()
    paid = FeeVoucher.objects.filter(status='PAID').count()
    pending = total_vouchers - paid
    download_rate = round((paid / total_vouchers * 100), 1) if total_vouchers else 0

    context = {
        'total_vouchers': total_vouchers, 'downloaded': paid, 'pending': pending, 'download_rate': download_rate,
        'recent_vouchers': FeeVoucher.objects.select_related('student').order_by('-id')[:15],
    }
    return render(request, 'automation/vouchers.html', context)


def notification_queue_view(request):
    if request.method == 'POST' and request.POST.get('action') == 'send_notifications':
        pending_count = NotificationQueue.objects.filter(status='PENDING').count()
        NotificationDispatcherService.send_pending_notifications()
        messages.success(request, f'{pending_count} pending notification(s) processed.')
        return redirect('notification-queue')

    context = {
        'total_queued': NotificationQueue.objects.count(),
        'sms_queued': NotificationQueue.objects.filter(notification_type='SMS').count(),
        'email_queued': NotificationQueue.objects.filter(notification_type='EMAIL').count(),
        'push_queued': 0,
        'failed': NotificationQueue.objects.filter(status='FAILED').count(),
        'recent_queue': NotificationQueue.objects.order_by('-created_at')[:15],
    }
    return render(request, 'automation/notifications.html', context)


def salary_automation_view(request):
    salary_settings = SalaryAutomationSettings.objects.first() or SalaryAutomationSettings.objects.create()

    if request.method == 'POST':
        action = request.POST.get('action')
        try:
            if action == 'save_salary_settings':
                salary_settings.auto_enabled = request.POST.get('salary_auto_enabled') == 'on'
                salary_settings.generation_day = int(request.POST.get('salary_generation_day') or 30)
                salary_settings.generation_time = datetime.strptime(
                    request.POST.get('salary_generation_time') or '18:00', '%H:%M').time()
                salary_settings.send_notifications = request.POST.get('salary_send_notifications') == 'on'
                salary_settings.save()
                messages.success(request, 'Salary automation settings saved.')
            elif action == 'generate_salaries':
                today = date.today()
                month_name = request.POST.get('salary_month') or today.strftime('%B')
                year = int(request.POST.get('salary_year') or today.year)
                SalaryAutomationService.generate_salaries(month_name, year)
                messages.success(request, 'Salary generation completed.')
        except Exception as e:
            messages.error(request, f'Action failed: {str(e)}')
        return redirect('salary-automation')

    this_month = date.today().strftime('%B')
    context = {
        'salary_settings': salary_settings,
        'total_payslips': SalaryVoucher.objects.count(),
        'generated_this_month': SalaryVoucher.objects.filter(month=this_month, year=date.today().year).count(),
        'downloaded': SalaryVoucher.objects.filter(status='PAID').count(),
        'pending': SalaryVoucher.objects.exclude(status='PAID').count(),
        'recent_generation': SalaryVoucher.objects.select_related('teacher').order_by('-id')[:15],
        'months': ['January','February','March','April','May','June','July','August','September','October','November','December'],
        'current_month': this_month,
        'current_year': date.today().year,
    }
    return render(request, 'automation/salary.html', context)


def payslip_management_view(request):
    return salary_automation_view(request)


def automation_settings_view(request):
    fee_settings = FeeGenerationSettings.objects.first() or FeeGenerationSettings.objects.create()
    salary_settings = SalaryAutomationSettings.objects.first() or SalaryAutomationSettings.objects.create()

    if request.method == 'POST' and request.POST.get('action') == 'save_all_settings':
        try:
            fee_settings.auto_enabled = request.POST.get('fee_auto_enabled') == 'on'
            fee_settings.generation_day = int(request.POST.get('fee_generation_day') or 1)
            fee_settings.generation_time = datetime.strptime(
                request.POST.get('fee_generation_time') or '09:00', '%H:%M').time()
            fee_settings.send_notifications = request.POST.get('fee_send_notifications') == 'on'
            fee_settings.save()

            salary_settings.auto_enabled = request.POST.get('salary_auto_enabled') == 'on'
            salary_settings.generation_day = int(request.POST.get('salary_generation_day') or 30)
            salary_settings.generation_time = datetime.strptime(
                request.POST.get('salary_generation_time') or '18:00', '%H:%M').time()
            salary_settings.send_notifications = request.POST.get('salary_send_notifications') == 'on'
            salary_settings.save()

            messages.success(request, 'Automation settings saved successfully.')
        except Exception as e:
            messages.error(request, f'Failed to save settings: {str(e)}')
        return redirect('automation-settings')

    context = {'fee_settings': fee_settings, 'salary_settings': salary_settings}
    return render(request, 'automation/settings.html', context)

def timetable_list(request):
    periods = Period.objects.all()
    return render(request, 'timetable/timetable.html', {'periods': periods})

def create_period(request):
    if request.method == 'POST':
        Period.objects.create(
            class_name=request.POST['class_name'],
            section=request.POST['section'],
            subject=request.POST['subject'],
            teacher_id=request.POST['teacher_id'],
            day=request.POST['day'],
            period_number=request.POST['period_number'],
            start_time=request.POST['start_time'],
            end_time=request.POST['end_time']
        )
    return render(request, 'timetable/manage_periods.html')

def mark_absence(request):
    if request.method == 'POST':
        absence = Absence.objects.create(
            teacher_id=request.POST['teacher_id'],
            absence_date=request.POST['absence_date'],
            period_id=request.POST['period_id']
        )
        Fixture.objects.create(
            absent_teacher_id=request.POST['teacher_id'],
            replacement_teacher_id=request.POST['replacement_teacher_id'],
            period_id=request.POST['period_id'],
            fixture_date=request.POST['absence_date'],
            status='PENDING'
        )
    return render(request, 'timetable/fixtures.html')

def fixture_auto_assign(request):
    absences = Absence.objects.all()
    return render(request, 'timetable/fixtures.html', {'absences': absences})

from edupilot_core.models import Period, AssignedPeriods, Fixture, Absence

def timetable_list(request):
    periods = Period.objects.all()
    return render(request, 'automation/timetable.html', {'periods': periods})

def create_period(request):
    if request.method == 'POST':
        Period.objects.create(
            class_name=request.POST['class_name'],
            section=request.POST['section'],
            subject=request.POST['subject'],
            teacher_id=request.POST['teacher_id'],
            day=request.POST['day'],
            period_number=request.POST['period_number'],
            start_time=request.POST['start_time'],
            end_time=request.POST['end_time']
        )
    return render(request, 'automation/manage_periods.html')

def mark_absence(request):
    if request.method == 'POST':
        Absence.objects.create(
            teacher_id=request.POST['teacher_id'],
            absence_date=request.POST['absence_date'],
            period_id=request.POST['period_id']
        )
        Fixture.objects.create(
            absent_teacher_id=request.POST['teacher_id'],
            replacement_teacher_id=request.POST['replacement_teacher_id'],
            period_id=request.POST['period_id'],
            fixture_date=request.POST['absence_date'],
            status='PENDING'
        )
    return render(request, 'automation/fixtures.html')

def fixture_auto_assign(request):
    fixtures = Fixture.objects.all()
    return render(request, 'automation/fixtures.html', {'fixtures': fixtures})

def mark_absence(request):
    if request.method == 'POST':
        absence = Absence.objects.create(
            teacher_id=request.POST['teacher_id'],
            absence_date=request.POST['absence_date'],
            period_id=request.POST['period_id']
        )
        
        # Auto-assign fixture
        from edupilot_core.services import FixtureAutomationService
        FixtureAutomationService.auto_assign_fixture(absence.id)
        
        return render(request, 'automation/fixtures.html')
    
    return render(request, 'automation/mark_absence.html')

def teacher_schedule(request):
    teacher = Teacher.objects.get(user=request.user)
    periods = Period.objects.filter(teacher=teacher)
    fixtures = Fixture.objects.filter(replacement_teacher=teacher)
    return render(request, 'timetable/my_schedule.html', 
                 {'periods': periods, 'fixtures': fixtures})

def timetable_logs(request):
    fixtures = Fixture.objects.all().order_by('-fixture_date')
    return render(request, 'timetable/logs.html', {'fixtures': fixtures})